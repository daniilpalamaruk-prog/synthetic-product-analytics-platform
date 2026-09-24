#!/usr/bin/env python3
"""CLI entry point for the synthetic SaaS dataset generator."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from saasgen.cli import main

if __name__ == "__main__":
    main()
