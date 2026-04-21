#!/bin/bash
# toggle_gui.sh - Switch between Headless and GUI modes for benchmarking
# Usage: toggle_gui.sh [--headless | --gui]

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

if [[ "$1" == "--headless" ]]; then
    echo -e "${BLUE}>>> Switching to Headless Mode (Server)...${NC}"
    sudo systemctl set-default multi-user.target
    sudo systemctl stop sddm || true
    echo -e "${GREEN}✓ Done. System will now boot to TTY (Console) by default.${NC}"
    echo "Reboot or run 'sudo systemctl isolate multi-user.target' to apply now."

elif [[ "$1" == "--gui" ]]; then
    echo -e "${BLUE}>>> Switching to GUI Mode (KDE Plasma)...${NC}"
    sudo systemctl set-default graphical.target
    sudo systemctl start sddm || true
    echo -e "${GREEN}✓ Done. System will now boot to Desktop (KDE) by default.${NC}"
    echo "Reboot or run 'sudo systemctl isolate graphical.target' to apply now."

else
    echo "Benchmarking Mode Toggle"
    echo "------------------------"
    echo "Current Target: $(systemctl get-default)"
    echo ""
    echo "Usage: toggle_gui.sh [OPTION]"
    echo "  --headless    Disable GUI and boot to console (Server mode)"
    echo "  --gui         Enable GUI and boot to KDE Plasma (Desktop mode)"
fi
