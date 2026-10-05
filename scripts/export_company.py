#!/usr/bin/env python3
"""Root convenience wrapper for backend/scripts/export_company.py."""
import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from scripts.export_company import main

if __name__ == "__main__":
    main()
