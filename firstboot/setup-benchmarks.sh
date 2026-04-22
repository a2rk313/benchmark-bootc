#!/bin/bash
# setup-benchmarks.sh - Manual benchmark environment setup
set -euo pipefail

BENCHMARK_REPO="https://github.com/a2rk313/benchmark-thesis.git"
BENCHMARK_DIR="/benchmarks"
DATA_DIR="/data"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

log() {
    echo -e "${BLUE}[$(date +'%H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}✓ $1${NC}"
}

error() {
    echo -e "${RED}✗ ERROR: $1${NC}"
    exit 1
}

log "Initializing benchmark environment setup..."

# Check if already set up
if [ -d "$BENCHMARK_DIR/.git" ]; then
    success "Benchmark repository already exists at $BENCHMARK_DIR"
else
    log "Cloning benchmark-thesis repository..."
    # Ensure SSL verification is active
    export GIT_SSL_NO_VERIFY=false
    
    if git clone "$BENCHMARK_REPO" "$BENCHMARK_DIR" 2>&1; then
        if [ ! -d "$BENCHMARK_DIR/.git" ]; then
            error "Git clone seemed to succeed but .git directory is missing!"
        fi
        success "Benchmark repo cloned successfully!"
    else
        error "Failed to clone benchmark repo"
    fi
fi

# Download data
if [ -f "$BENCHMARK_DIR/tools/download_data.py" ]; then
    log "Downloading benchmark datasets (this may take a while)..."
    cd "$BENCHMARK_DIR"
    python3 tools/download_data.py --all || log "Warning: Data download encountered issues"
fi

# Ensure the global /data link points to the repo's data folder
log "Configuring data paths..."
sudo ln -sf "$BENCHMARK_DIR/data" "$DATA_DIR" 2>/dev/null || true

success "Setup complete! You can now run benchmarks using 'native_benchmark.sh'"
