"""Download original Hearthstone card art for PRIVATE use.

The art is Blizzard's copyrighted property. It is stored under
backend/images/ (cards/ = 256px, cards_big/ = 512px) which is gitignored, so it
never enters the public repository. Use it only in a private, non-public
deployment.

Source: HearthstoneJSON art renderer (keyed by the standard card ID).
"""
import json
import os
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.engine.fireplace_setup import _ssl_context  # noqa: E402

ART_URL = "https://art.hearthstonejson.com/v1/render/latest/enUS/{size}/{card}.png"
ROOT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "images"
)
# size -> subdirectory
SIZES = {"256x": "cards", "512x": "cards_big"}


def download(item) -> str:
    card_id, size = item
    out = os.path.join(ROOT, SIZES[size], f"{card_id}.png")
    if os.path.exists(out) and os.path.getsize(out) > 1000:
        return "skip"
    try:
        # A browser-like User-Agent is required; the CDN blocks Python's default.
        req = urllib.request.Request(
            ART_URL.format(size=size, card=card_id),
            headers={"User-Agent": "Mozilla/5.0"},
        )
        with urllib.request.urlopen(req, context=_ssl_context(), timeout=30) as resp:
            if resp.status != 200:
                return "fail"
            data = resp.read()
        if len(data) < 1000:
            return "fail"
        with open(out, "wb") as f:
            f.write(data)
        return "ok"
    except Exception:
        return "fail"


def main() -> None:
    cards_path = sys.argv[1] if len(sys.argv) > 1 else "cards.json"
    cards = json.load(open(cards_path))
    ids = [c["id"] for c in cards]
    for subdir in SIZES.values():
        os.makedirs(os.path.join(ROOT, subdir), exist_ok=True)
    items = [(cid, size) for cid in ids for size in SIZES]
    stats = {"ok": 0, "skip": 0, "fail": 0}
    with ThreadPoolExecutor(max_workers=8) as ex:
        for result in ex.map(download, items):
            stats[result] += 1
    print(f"done: ok={stats['ok']} skip={stats['skip']} fail={stats['fail']} of {len(items)} items")


if __name__ == "__main__":
    main()
