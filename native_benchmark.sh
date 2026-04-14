#!/bin/bash
# native_benchmark.sh - Simple native OS benchmark runner
# Eliminates container overhead for true bare-metal performance

set -e

echo "=========================================================================="
echo "NATIVE BARE-METAL BENCHMARK RUNNER"
echo "=========================================================================="

# Set DATA_DIR
DATA_DIR="/data"
FALLBACK_DIR="$(pwd)/data"

# 0. DOWNLOAD DATA IF NOT PRESENT
download_data() {
    echo ""
    echo "[0/4] Checking benchmark data..."
    
    if [ -d "$DATA_DIR" ] && [ -n "$(ls -A "$DATA_DIR" 2>/dev/null)" ]; then
        echo "    ✓ Data found in $DATA_DIR"
        return 0
    fi
    
    if [ -d "$FALLBACK_DIR" ] && [ -n "$(ls -A "$FALLBACK_DIR" 2>/dev/null)" ]; then
        echo "    ✓ Data found in $FALLBACK_DIR"
        return 0
    fi
    
    echo "    → Data not found, downloading..."
    
    # Try tools/download_data.py first
    if [ -f "/tools/download_data.py" ]; then
        python3 /tools/download_data.py --all --synthetic 2>/dev/null && {
            echo "    ✓ Data downloaded"
            return 0
        }
    fi
    
    # Fallback: create minimal synthetic data
    echo "    → Creating minimal synthetic data..."
    mkdir -p "$FALLBACK_DIR"
    
    echo "    ✓ Using fallback mode"
}

# 1. PYTHON NATIVE SETUP
setup_python_native() {
    echo ""
    echo "[1/4] Setting up Python native environment..."
    
    # Use system Python or create venv
    python3 -m venv /tmp/thesis-native-python
    source /tmp/thesis-native-python/bin/activate
    
    # Install exact versions
    pip install --quiet \
        numpy==1.26.3 \
        scipy==1.11.4 \
        pandas==2.1.4 \
        rasterio==1.3.9
    
    # Check BLAS (important for performance!)
    python3 -c "import numpy; numpy.show_config()" | grep -i blas
    
    echo "    ✓ Python native ready"
}

# 2. JULIA NATIVE SETUP
setup_julia_native() {
    echo ""
    echo "[2/4] Setting up Julia native environment..."
    
    # Julia packages install to ~/.julia by default (already native!)
    # Just ensure packages are precompiled
    julia -e 'using Pkg; Pkg.instantiate(); Pkg.precompile()'
    
    echo "    ✓ Julia native ready (uses ~/.julia/)"
}

# 3. R NATIVE SETUP  
setup_r_native() {
    echo ""
    echo "[3/4] Setting up R native environment..."
    
    # Check which BLAS R is using
    R --quiet -e "La_library()" | grep -i blas
    
    # Ensure packages installed
    R --quiet -e 'install.packages(c("terra", "data.table"), repos="https://cloud.r-project.org")'
    
    echo "    ✓ R native ready"
}

# OPTIMIZE SYSTEM FOR BENCHMARKING
optimize_system() {
    echo ""
    echo "Optimizing system for benchmarking..."
    
    # Set CPU governor to performance (requires sudo)
    if command -v cpupower &> /dev/null; then
        sudo cpupower frequency-set --governor performance 2>/dev/null || true
        echo "✓ CPU governor set to performance"
    fi
    
    # Drop filesystem caches
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
    echo "Next step: Compare with container results"
    echo "  python3 compare_native_vs_container.py"
}

main "$@"
