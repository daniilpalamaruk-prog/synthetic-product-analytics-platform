#!/usr/bin/env python3
"""Stable validation entry point; delegates to the package quality layer."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from saasgen.quality import main

if __name__ == "__main__":
    main()

