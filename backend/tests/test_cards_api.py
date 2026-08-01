def test_list_cards_all(client):
    resp = client.get("/api/cards")
    assert resp.status_code == 200
    assert len(resp.json()) == 16


def test_list_cards_filter_class(client):
    resp = client.get("/api/cards", params={"class": "MAGE"})
    assert {c["id"] for c in resp.json()} == {"CS2_029", "EX1_279"}


def test_list_cards_search(client):
    resp = client.get("/api/cards", params={"q": "boulder"})
    assert resp.json()[0]["id"] == "CS2_200"
