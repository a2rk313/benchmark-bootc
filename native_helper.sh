#!/bin/bash
# =============================================================================
# Native Benchmark Helper Script
# =============================================================================
# Sets up PATH for locally installed tools and runs benchmarks.
# For immutable distros without package managers.
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

echo "=============================================="
echo "Native Benchmark Helper"
echo "=============================================="

# Add local Julia to PATH if installed
if [ -d "$HOME/.local/julia/bin" ]; then
    export PATH="$HOME/.local/julia/bin:$PATH"
    echo -e "${GREEN}✓${NC} Julia found: $(julia --version | head -1)"
else
    echo -e "${RED}✗${NC} Julia not found in ~/.local/julia"
fi

# Activate Python venv if exists
if [ -f "$SCRIPT_DIR/.venv/bin/activate" ]; then
    source "$SCRIPT_DIR/.venv/bin/activate"
    echo -e "${GREEN}✓${NC} Python venv activated: $(python --version)"
else
    echo -e "${RED}✗${NC} Python venv not found"
fi

# R must use container
echo ""
echo "Note: R is not installable on immutable distros."
echo "      Use container mode for R benchmarks:"
echo "      ./run_benchmarks.sh"
echo ""

# Run requested benchmark
if [ -n "${1:-}" ]; then
    echo "Running: $@"
    "$@"
fi
