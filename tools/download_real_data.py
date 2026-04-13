#!/usr/bin/env python3
"""
DEPRECATED: Use tools/download_data.py instead

This script is kept for backwards compatibility.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

if __name__ == "__main__":
    print("=" * 60)
    print("DEPRECATED: Use tools/download_data.py instead")
    print("=" * 60)
    print()
    print("New usage:")
    print("  python tools/download_data.py --all")
    print("  python tools/download_data.py --check")
    print()

    # Forward to unified script
    from tools.download_data import main

    sys.exit(main())
