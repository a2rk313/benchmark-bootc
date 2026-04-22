#!/bin/bash
# native_benchmark.sh - Native OS benchmark runner
# Clones benchmark-thesis repo on first run if not present

set -e

BENCHMARK_DIR="/benchmarks"
DATA_DIR="/data"
REPO_URL="https://github.com/a2rk313/benchmark-thesis.git"

echo "=========================================================================="
echo "NATIVE BARE-METAL BENCHMARK RUNNER"
echo "=========================================================================="

# CHECK SYSTEM MODE (GUI vs HEADLESS)
SYSTEM_TARGET=$(systemctl get-default)
if [[ "$SYSTEM_TARGET" == "graphical.target" ]]; then
    SYSTEM_MODE="GUI (KDE Plasma)"
else
    SYSTEM_MODE="Headless (Server)"
fi
echo "System Mode: $SYSTEM_MODE"
echo "--------------------------------------------------------------------------"

# 0. ENSURE BENCHMARKS ARE AVAILABLE
ensure_benchmarks() {
    echo ""
    echo "[0/5] Checking benchmark repository..."
    
    if [ -d "$BENCHMARK_DIR/.git" ]; then
        echo "    ✓ Benchmark repo found at $BENCHMARK_DIR"
        cd "$BENCHMARK_DIR"
        return 0
    else
        echo "    ✗ ERROR: Benchmark repository not found in $BENCHMARK_DIR"
        echo "      Please run 'sudo setup-benchmarks.sh' first to initialize the environment."
        exit 1
    fi
}

# 1. CHECK DATA
check_data() {
    echo ""
    echo "[1/5] Checking benchmark data..."
    
    if [ -d "$BENCHMARK_DIR/data" ] && [ -n "$(ls -A "$BENCHMARK_DIR/data" 2>/dev/null)" ]; then
        echo "    ✓ Data found in $BENCHMARK_DIR/data"
        return 0
    else
        echo "    ✗ ERROR: Benchmark data not found."
        echo "      Please run 'sudo setup-benchmarks.sh' to download required datasets."
        exit 1
    fi
}

# 2. PYTHON NATIVE CHECK
check_python_native() {
    echo ""
    echo "[2/5] Verifying system Python environment..."
    
    if ! command -v python3 &> /dev/null; then
        echo "    ! python3 not found in PATH"
        return 1
    fi
    
    python3 -c "import numpy; print(f'    ✓ NumPy {numpy.__version__} detected'); numpy.show_config()" | grep -i blas || echo "    ! OpenBLAS not detected in NumPy config"
    python3 -c "import geopandas; print(f'    ✓ GeoPandas {geopandas.__version__} detected')"
    echo "    ✓ System Python ready"
}

# 3. JULIA NATIVE CHECK
check_julia_native() {
    echo ""
    echo "[3/5] Verifying system Julia environment..."
    
    if ! command -v julia &> /dev/null; then
        echo "    ! julia not found in PATH"
        return 1
    fi
    
    export JULIA_DEPOT_PATH="/usr/share/julia/depot"
    julia -e 'using Pkg; if !haskey(Pkg.dependencies(), UUID("ArchGDAL")); Pkg.add("ArchGDAL"); end'
    julia -e 'using ArchGDAL; println("    ✓ Julia packages verified")'
    echo "    ✓ System Julia ready"
}

# 4. R NATIVE CHECK  
check_r_native() {
    echo ""
    echo "[4/5] Verifying system R environment..."
    
    if ! command -v Rscript &> /dev/null; then
        echo "    ! Rscript not found in PATH"
        return 1
    fi
    
    Rscript -e "library(terra); library(data.table); cat('    ✓ R packages verified\n')"
    Rscript -e "cat('    ✓ BLAS: ', La_library(), '\n')" | grep -i blas || echo "    ! OpenBLAS not detected in R"
    echo "    ✓ System R ready"
}

# OPTIMIZE SYSTEM FOR BENCHMARKING
optimize_system() {
    echo ""
    echo "Optimizing system for benchmarking..."
    
    # Set CPU to performance mode if possible
    if command -v cpupower &> /dev/null; then
        sudo cpupower frequency-set --governor performance 2>/dev/null || true
        echo "✓ CPU governor set to performance"
    fi
    
    # Drop caches to ensure clean start
    sync
    echo 3 | sudo tee /proc/sys/vm/drop_caches > /dev/null 2>&1 || true
    echo "✓ Filesystem caches dropped"
}

# RUN NATIVE BENCHMARKS
run_native_benchmarks() {
    echo ""
    echo "=========================================================================="
    echo "Running native benchmarks with CPU affinity (pinning)..."
    echo "=========================================================================="
    
    # Ensure we are in the benchmark directory
    cd "$BENCHMARK_DIR"

    # Persistence location
    RESULTS_BASE="$BENCHMARK_DIR/results/native"
    mkdir -p "$RESULTS_BASE"
    
    # ACADEMIC RIGOR: Environment Synchronization
    export JULIA_DEPOT_PATH="/usr/share/julia/depot"
    export JULIA_NUM_THREADS=8
    export OPENBLAS_NUM_THREADS=8
    export FLEXIBLAS_NUM_THREADS=8
    export GOTO_NUM_THREADS=8
    export OMP_NUM_THREADS=8
    
    # ACADEMIC RIGOR: CPU Affinity (Pinning)
    # Attempt to pin to physical cores 0-7 to avoid scheduler noise
    PIN_CMD=""
    if command -v numactl &> /dev/null; then
        CORES=$(nproc)
        if [ "$CORES" -ge 8 ]; then
            PIN_CMD="numactl --physcpubind=0-7 --localalloc"
            echo "    ✓ Affinity: Locked to physical cores 0-7"
        else
            PIN_CMD="numactl --physcpubind=0-$((CORES-1)) --localalloc"
            echo "    ⚠ Affinity: Limited cores ($CORES), locking to all available"
        fi
    fi

    SCENARIOS=(
        "matrix_ops"
        "raster_algebra"
        "zonal_stats"
        "vector_pip"
        "timeseries_ndvi"
        "reprojection"
        "interpolation_idw"
        "hsi_stream"
        "io_ops"
    )

    for scenario in "${SCENARIOS[@]}"; do
        echo ""
        echo ">>> RUNNING SCENARIO: $scenario"
        echo "--------------------------------------------------------------------------"

        # Python
        if [ -f "benchmarks/${scenario}.py" ]; then
            echo "[Python] Running $scenario..."
            /usr/bin/time -v $PIN_CMD python3 "benchmarks/${scenario}.py" > "$RESULTS_BASE/${scenario}_python.json" 2> "$RESULTS_BASE/${scenario}_python_stats.txt" || echo "    ! Python $scenario failed"
        fi
        
        # Julia
        if [ -f "benchmarks/${scenario}.jl" ]; then
            echo "[Julia] Running $scenario..."
            /usr/bin/time -v $PIN_CMD julia "benchmarks/${scenario}.jl" > "$RESULTS_BASE/${scenario}_julia.json" 2> "$RESULTS_BASE/${scenario}_julia_stats.txt" || echo "    ! Julia $scenario failed"
        fi
        
        # R
        if [ -f "benchmarks/${scenario}.R" ]; then
            echo "[R] Running $scenario..."
            /usr/bin/time -v $PIN_CMD Rscript "benchmarks/${scenario}.R" > "$RESULTS_BASE/${scenario}_r.json" 2> "$RESULTS_BASE/${scenario}_r_stats.txt" || echo "    ! R $scenario failed"
        fi
    done
    
    echo ""
    echo "✓ Native benchmarks complete"
}

# RESTORE SYSTEM
restore_system() {
    echo ""
    echo "Restoring system settings..."
    
    if command -v cpupower &> /dev/null; then
        sudo cpupower frequency-set --governor powersave 2>/dev/null || true
    fi
    
    echo "✓ System restored"
}

# MAIN EXECUTION
main() {
    ensure_benchmarks
    check_data
    check_python_native
    check_julia_native
    check_r_native
    optimize_system
    run_native_benchmarks
    restore_system
    
    echo ""
    echo "=========================================================================="
    echo "NATIVE BENCHMARKS COMPLETE"
    echo "=========================================================================="
    echo ""
    echo "Results saved to: results/native/"
    echo ""
    echo "Full benchmark suite: cd $BENCHMARK_DIR && ./run_benchmarks.sh --native-only"
}

main "$@"
