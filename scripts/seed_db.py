#!/usr/bin/env python3
"""Seed the database with sample data.

Usage:
    python scripts/seed_db.py
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.db.seed_data import seed_database

if __name__ == "__main__":
    seed_database()
