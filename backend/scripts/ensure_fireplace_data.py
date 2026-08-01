"""Ensure Fireplace's bundled CardDefs.xml is the real file, not a git-LFS stub.

Fireplace's CardDefs.xml is stored in git LFS. `pip install fireplace @ git+...`
does not resolve LFS, leaving a ~133-byte pointer stub that makes the engine's
card database empty. This script downloads the real file and verifies its
SHA-256 against the pointer's advertised oid.
"""
import hashlib
import pathlib
import urllib.request

# oid/size from the LFS pointer in fireplace/cards/CardDefs.xml (master).
LFS_OID = "7fccd87b7e20f9864fe0664aa9d9304213981dc6c883fe71010cceda1b9af7ac"
LFS_URL = "https://media.githubusercontent.com/media/jleclanche/fireplace/master/fireplace/cards/CardDefs.xml"


def carddefs_path() -> pathlib.Path:
    import fireplace.cards as fc

    return pathlib.Path(fc.__file__).parent / "CardDefs.xml"


def ensure_carddefs() -> pathlib.Path:
    path = carddefs_path()
    if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest() == LFS_OID:
        return path
    print(f"Downloading CardDefs.xml from {LFS_URL} ...")
    urllib.request.urlretrieve(LFS_URL, path)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != LFS_OID:
        raise SystemExit(f"SHA-256 mismatch after download: {digest}")
    return path


if __name__ == "__main__":
    path = ensure_carddefs()
    print(f"CardDefs.xml OK: {path} ({path.stat().st_size} bytes)")
