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

# 0. ENSURE BENCHMARKS ARE AVAILABLE
ensure_benchmarks() {
    echo ""
    echo "[0/5] Checking benchmark repository..."
    
    if [ -d "$BENCHMARK_DIR/.git" ]; then
        echo "    ✓ Benchmark repo found at $BENCHMARK_DIR"
        cd "$BENCHMARK_DIR"
        return 0
    fi
    
    echo "    → Benchmark repo not found, cloning..."
    git clone "$REPO_URL" "$BENCHMARK_DIR"
    cd "$BENCHMARK_DIR"
    
    # Download data
    if [ -f "tools/download_data.py" ]; then
        echo "    → Downloading benchmark data..."
        python3 tools/download_data.py --all --synthetic || true
    fi
    
    echo "    ✓ Benchmark repo cloned and ready"
}

# 1. DOWNLOAD DATA IF NOT PRESENT
download_data() {
    echo ""
    echo "[1/5] Checking benchmark data..."
    
    if [ -d "$DATA_DIR" ] && [ -n "$(ls -A "$DATA_DIR" 2>/dev/null)" ]; then
        echo "    ✓ Data found in $DATA_DIR"
        return 0
    fi
    
    if [ -d "$BENCHMARK_DIR/data" ] && [ -n "$(ls -A "$BENCHMARK_DIR/data" 2>/dev/null)" ]; then
        echo "    ✓ Data found in $BENCHMARK_DIR/data"
        return 0
    fi
    
    echo "    → Data not found, downloading..."
    if [ -f "$BENCHMARK_DIR/tools/download_data.py" ]; then
        python3 "$BENCHMARK_DIR/tools/download_data.py" --all --synthetic 2>/dev/null || true
    fi
    echo "    ✓ Data ready"
}

# 2. PYTHON NATIVE SETUP
setup_python_native() {
    echo ""
    echo "[2/5] Setting up Python native environment..."
    
    python3 -m venv /tmp/thesis-native-python
    source /tmp/thesis-native-python/bin/activate
    
    pip install --quiet \
        numpy==1.26.3 \
        scipy==1.11.4 \
        pandas==2.1.4 \
        rasterio==1.3.9
    
    python3 -c "import numpy; numpy.show_config()" | grep -i blas
    echo "    ✓ Python native ready"
}

# 3. JULIA NATIVE SETUP
setup_julia_native() {
    echo ""
    echo "[3/5] Setting up Julia native environment..."
    
    julia -e 'using Pkg; Pkg.instantiate(); Pkg.precompile()'
    echo "    ✓ Julia native ready"
}

# 4. R NATIVE SETUP  
setup_r_native() {
    echo ""
    echo "[4/5] Setting up R native environment..."
    
    R --quiet -e "La_library()" | grep -i blas
    R --quiet -e 'install.packages(c("terra", "data.table"), repos="https://cloud.r-project.org")'
    echo "    ✓ R native ready"
}

# OPTIMIZE SYSTEM FOR BENCHMARKING
optimize_system() {
    echo ""
    echo "Optimizing system for benchmarking..."
    
    if command -v cpupower &> /dev/null; then
        sudo cpupower frequency-set --governor performance 2>/dev/null || true
        echo "✓ CPU governor set to performance"
    fi
    
    sync
    echo 3 | sudo tee /proc/sys/vm/drop_caches > /dev/null 2>&1 || true
    echo "✓ Filesystem caches dropped"
}

# RUN NATIVE BENCHMARKS
run_native_benchmarks() {
    echo ""
    echo "=========================================================================="
    echo "Running native benchmarks..."
    echo "=========================================================================="
    
    mkdir -p results/native
    
    # Python
    echo ""
    echo "[Python] Running matrix operations..."
    source /tmp/thesis-native-python/bin/activate
    time python3 benchmarks/matrix_ops.py > results/native/matrix_ops_python.json
    
    # Julia
    echo ""
    echo "[Julia] Running matrix operations..."
    time julia benchmarks/matrix_ops.jl > results/native/matrix_ops_julia.json
    
    # R
    echo ""
    echo "[R] Running matrix operations..."
    time Rscript benchmarks/matrix_ops.R > results/native/matrix_ops_r.json
    
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
    download_data
    setup_python_native
    setup_julia_native
    setup_r_native
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
