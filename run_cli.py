#!/usr/bin/env python3
"""
Entrypoint CLI for the Fifine AmpliGame D6 (StreamDock 293S) Controller & Web Studio.
Usage:
    python3 run_cli.py studio       # Launches the Pro Web Studio (http://localhost:5151)
    python3 run_cli.py list         # Inspect connected USB Stream Deck hardware
    python3 run_cli.py brightness 80 # Adjust display brightness (0 to 100%)
    python3 run_cli.py monitor      # Real-time event monitor for key presses
    python3 run_cli.py clear        # Blank all LCD keys
"""

import sys
from pathlib import Path

# Add src and embedded sdk to python path
ROOT_DIR = Path(__file__).resolve().parent
SRC_DIR = ROOT_DIR / "src"
SDK_DIR = ROOT_DIR / "sdk"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
if str(SDK_DIR) not in sys.path:
    sys.path.insert(0, str(SDK_DIR))

from ampligame_d6 import main

if __name__ == "__main__":
    main()
