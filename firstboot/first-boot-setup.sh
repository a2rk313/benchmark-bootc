#!/bin/bash
# first-boot-setup.sh - Clone benchmarks on first boot
set -euo pipefail

BENCHMARK_REPO="https://github.com/a2rk313/benchmark-thesis.git"
BENCHMARK_DIR="/benchmarks"
DATA_DIR="/data"
LOG_FILE="/var/log/firstboot.log"

log() {
    echo "[$(date)] $1" | tee -a "$LOG_FILE"
}

log "Starting first-boot benchmark setup..."

# Check if already set up
if [ -d "$BENCHMARK_DIR/.git" ]; then
    log "Benchmark repo already cloned, skipping..."
    touch /var/lib/benchmark-firstboot-complete
    exit 0
fi

# Clone the benchmark repo
log "Cloning benchmark-thesis repository..."
if git clone "$BENCHMARK_REPO" "$BENCHMARK_DIR" 2>&1 | tee -a "$LOG_FILE"; then
    log "Benchmark repo cloned successfully!"
else
    log "ERROR: Failed to clone benchmark repo"
    exit 1
fi

# Download data
if [ -f "$BENCHMARK_DIR/tools/download_data.py" ]; then
    log "Downloading benchmark data..."
    cd "$BENCHMARK_DIR"
    python3 tools/download_data.py --all --synthetic 2>&1 | tee -a "$LOG_FILE" || true
fi

# Create data symlink
ln -sf "$BENCHMARK_DIR/data" "$DATA_DIR" 2>/dev/null || true

# Mark as complete
touch /var/lib/benchmark-firstboot-complete
log "First-boot setup complete!"
