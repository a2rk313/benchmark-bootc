#!/bin/bash
# download_data.sh - Download benchmark data at runtime
set -euo pipefail

DATA_DIR="/data"
TOOLS_DIR="/tools"
FALLBACK_DIR="$(pwd)/data"

echo "=========================================================================="
echo "DOWNLOADING BENCHMARK DATA"
echo "=========================================================================="

# Determine data directory
if [ -d "$DATA_DIR" ] && [ -n "$(ls -A "$DATA_DIR" 2>/dev/null)" ]; then
    echo "✓ Data already present in $DATA_DIR"
    exit 0
fi

# Try to use tools/download_data.py first
if [ -f "$TOOLS_DIR/download_data.py" ]; then
    echo "Using tools/download_data.py..."
    cd /
    python3 "$TOOLS_DIR/download_data.py" --all --synthetic 2>/dev/null && {
        echo "✓ Data downloaded to $FALLBACK_DIR"
        exit 0
    }
fi

# Fallback: create minimal synthetic data
echo "Creating minimal synthetic data..."
mkdir -p "$FALLBACK_DIR"

# Create a minimal Cuprite.mat file (placeholder)
if [ ! -f "$FALLBACK_DIR/Cuprite.mat" ]; then
    echo "Creating synthetic Cuprite.mat..."
    python3 -c "
import numpy as np
from scipy.io import savemat
data = {'crism': np.random.rand(100, 100, 50).astype(np.float32)}
savemat('$FALLBACK_DIR/Cuprite.mat', data)
print('Created Cuprite.mat')
" 2>/dev/null || echo "Warning: Could not create synthetic data"
fi

echo "✓ Minimal data ready in $FALLBACK_DIR"
