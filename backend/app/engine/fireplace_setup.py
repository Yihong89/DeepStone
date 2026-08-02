"""Fireplace engine bootstrap: ensure card data is present and the DB is ready.

Fireplace's bundled CardDefs.xml is stored in git LFS; `pip install` leaves a
~133-byte pointer stub that makes the engine's card DB empty. ensure_carddefs()
downloads the real file (verified by SHA-256) and init_engine() initializes the
lazily-built card database. Run once at app startup.
"""
import hashlib
import pathlib
import shutil
import ssl
import urllib.request

import fireplace.cards as fireplace_cards

from app.engine.card_data_sync import sync_current_stats

# oid/size from the LFS pointer in fireplace/cards/CardDefs.xml (master).
LFS_OID = "7fccd87b7e20f9864fe0664aa9d9304213981dc6c883fe71010cceda1b9af7ac"
LFS_URL = "https://media.githubusercontent.com/media/jleclanche/fireplace/master/fireplace/cards/CardDefs.xml"


def carddefs_path() -> pathlib.Path:
    return pathlib.Path(fireplace_cards.__file__).parent / "CardDefs.xml"


def _ssl_context() -> ssl.SSLContext:
    # macOS Python often can't find the system root certs; certifi is the
    # reliable CA bundle.
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


def ensure_carddefs() -> pathlib.Path:
    path = carddefs_path()
    if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest() == LFS_OID:
        return path
    with urllib.request.urlopen(LFS_URL, context=_ssl_context()) as resp, open(path, "wb") as out:
        shutil.copyfileobj(resp, out)
    if hashlib.sha256(path.read_bytes()).hexdigest() != LFS_OID:
        raise SystemExit("SHA-256 mismatch after CardDefs.xml download")
    return path


def init_engine() -> None:
    ensure_carddefs()
    if not fireplace_cards.db.initialized:
        fireplace_cards.db.initialize()
    # Fireplace's frozen CardDefs overrides the current hearthstone_data with
    # stale balance-patch stats; restore the current values for the board.
    sync_current_stats(fireplace_cards.db)
