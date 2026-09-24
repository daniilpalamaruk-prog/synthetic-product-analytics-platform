#!/usr/bin/env python3
"""Run data-quality checks against an existing generated dataset."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from saasgen.quality import main

if __name__ == "__main__":
    main()
