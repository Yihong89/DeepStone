def _register(client, username="sam", password="pw123456"):
    client.post("/api/auth/register", json={
        "username": username, "email": f"{username}@example.com", "password": password,
    })
    return client.post("/api/auth/login", json={
        "username": username, "password": password,
    }).json()["access_token"]


_NEUTRALS = [
    "CS2_200", "CS2_182", "CS2_131", "CS2_121", "CS2_201", "CS2_118",
    "CS2_124", "CS2_127", "CS2_142", "CS2_147", "CS2_150", "CS2_152",
    "CS2_172", "CS2_173",
]


def _valid30():
    # 2x Fireball (MAGE) + 2x each of 14 distinct NEUTRAL cards => 30 cards, legal for MAGE
    cards = ["CS2_029", "CS2_029"]
    for cid in _NEUTRALS:
        cards += [cid, cid]
    return cards


def test_create_valid_deck(client):
    token = _register(client)
    resp = client.post("/api/decks", json={
        "name": "Fire Yetis",
        "hero_class": "MAGE",
        "card_ids": _valid30(),
    }, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 201
    assert len(resp.json()["card_ids"]) == 30


def test_deck_wrong_class_rejected(client):
    token = _register(client)
    resp = client.post("/api/decks", json={
        "name": "Bad",
        "hero_class": "WARRIOR",
        "card_ids": ["CS2_029"] * 30,
    }, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 422
    assert any("WARRIOR" in e for e in resp.json()["detail"])


def test_deck_too_many_copies_rejected(client):
    token = _register(client)
    # 3x Pyroblast (EPIC) + 27x Yeti => 3 copies of a non-legendary card is invalid
    resp = client.post("/api/decks", json={
        "name": "Triple",
        "hero_class": "MAGE",
        "card_ids": ["EX1_279"] * 3 + ["CS2_182"] * 27,
    }, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 422
