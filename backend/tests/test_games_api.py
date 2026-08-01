_NEUTRALS = [
    "CS2_200", "CS2_182", "CS2_131", "CS2_121", "CS2_201", "CS2_118",
    "CS2_124", "CS2_127", "CS2_142", "CS2_147", "CS2_150", "CS2_152",
    "CS2_172", "CS2_173",
]


def _register(client, username, password="pw123456"):
    client.post("/api/auth/register", json={
        "username": username, "email": f"{username}@example.com", "password": password,
    })
    return client.post("/api/auth/login", json={
        "username": username, "password": password,
    }).json()["access_token"]


def _mkdeck(client, token, hero="MAGE"):
    card_ids = ["CS2_029", "CS2_029"]
    for cid in _NEUTRALS:
        card_ids += [cid, cid]
    resp = client.post("/api/decks", json={"name": "D", "hero_class": hero, "card_ids": card_ids},
                       headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def test_create_and_join_challenge(client):
    t1 = _register(client, "challenger")
    t2 = _register(client, "joiner")
    d1 = _mkdeck(client, t1)
    d2 = _mkdeck(client, t2)
    code = client.post("/api/games/challenges", json={"deck_id": d1},
                       headers={"Authorization": f"Bearer {t1}"}).json()["code"]
    resp = client.post(f"/api/games/challenges/{code}/join", json={"deck_id": d2},
                       headers={"Authorization": f"Bearer {t2}"})
    assert resp.status_code == 200
    assert resp.json()["game_id"]


def test_ai_game_created(client):
    token = _register(client, "aisolo")
    deck_id = _mkdeck(client, token)
    resp = client.post("/api/games/ai", json={"deck_id": deck_id},
                       headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["game_id"]


def test_matches_history(client):
    token = _register(client, "historian")
    deck_id = _mkdeck(client, token)
    client.post("/api/games/ai", json={"deck_id": deck_id},
                headers={"Authorization": f"Bearer {token}"})
    resp = client.get("/api/matches", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert len(resp.json()) == 1
