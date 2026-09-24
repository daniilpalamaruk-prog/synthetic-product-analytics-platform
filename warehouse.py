#!/usr/bin/env python3
"""Build the portable raw/staging/core/marts warehouse."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from saasgen.warehouse import main

if __name__ == "__main__":
    main()
