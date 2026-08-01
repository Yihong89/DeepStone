"""Download original Hearthstone card art for PRIVATE use.

The art is Blizzard's copyrighted property. It is stored under backend/images/
(cards/ = 256px framed, cards_big/ = 512px framed, cards_board/ = raw square
art) which is gitignored, so it never enters the public repository. Use it only
in a private, non-public deployment.

Source: HearthstoneJSON art renderer (keyed by the standard card ID).
"""
import json
import os
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.engine.fireplace_setup import _ssl_context  # noqa: E402

ROOT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "images"
)
# (kind, url_template, subdirectory)
SOURCES = [
    ("256x", "https://art.hearthstonejson.com/v1/render/latest/enUS/256x/{}.png", "cards"),
    ("512x", "https://art.hearthstonejson.com/v1/render/latest/enUS/512x/{}.png", "cards_big"),
    ("orig", "https://art.hearthstonejson.com/v1/orig/{}.png", "cards_board"),
]


def download(item) -> str:
    card_id, url_template, subdir = item
    out = os.path.join(ROOT, subdir, f"{card_id}.png")
    if os.path.exists(out) and os.path.getsize(out) > 1000:
        return "skip"
    try:
        # A browser-like User-Agent is required; the CDN blocks Python's default.
        req = urllib.request.Request(
            url_template.format(card_id), headers={"User-Agent": "Mozilla/5.0"}
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
    for _, _, subdir in SOURCES:
        os.makedirs(os.path.join(ROOT, subdir), exist_ok=True)
    items = [(cid, url, subdir) for cid in ids for _, url, subdir in SOURCES]
    stats = {"ok": 0, "skip": 0, "fail": 0}
    with ThreadPoolExecutor(max_workers=8) as ex:
        for result in ex.map(download, items):
            stats[result] += 1
    print(f"done: ok={stats['ok']} skip={stats['skip']} fail={stats['fail']} of {len(items)} items")


if __name__ == "__main__":
    main()
