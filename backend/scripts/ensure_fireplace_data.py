"""CLI wrapper: ensure Fireplace's CardDefs.xml is the real file (not an LFS stub)."""
from app.engine.fireplace_setup import ensure_carddefs


def main():
    path = ensure_carddefs()
    print(f"CardDefs.xml OK: {path} ({path.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
