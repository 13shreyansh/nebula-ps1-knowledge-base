#!/usr/bin/env python3
"""Run the local PS1 validator from a source checkout without installing it."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from nebula_ps1.validator import main

if __name__ == "__main__":
    raise SystemExit(main())
