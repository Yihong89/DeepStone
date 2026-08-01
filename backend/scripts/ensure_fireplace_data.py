"""CLI wrapper: ensure Fireplace's CardDefs.xml is the real file (not an LFS stub)."""
import os
import sys

# Allow running as `python scripts/ensure_fireplace_data.py` from anywhere.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.engine.fireplace_setup import ensure_carddefs


def main():
    path = ensure_carddefs()
    print(f"CardDefs.xml OK: {path} ({path.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
