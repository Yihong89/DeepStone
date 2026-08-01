def test_register_success(client):
    resp = client.post("/api/auth/register", json={
        "username": "alice",
        "email": "alice@example.com",
        "password": "hunter22",
    })
    assert resp.status_code == 201
    body = resp.json()
    assert body["username"] == "alice"
    assert body["role"] == "user"
    assert "password" not in body


def test_register_duplicate_username(client):
    payload = {"username": "bob", "email": "bob@example.com", "password": "pw123456"}
    assert client.post("/api/auth/register", json=payload).status_code == 201
    resp = client.post("/api/auth/register", json=payload)
    assert resp.status_code == 409


def test_login_success(client):
    client.post("/api/auth/register", json={
        "username": "carol", "email": "carol@example.com", "password": "pw123456",
    })
    resp = client.post("/api/auth/login", json={
        "username": "carol", "password": "pw123456",
    })
    assert resp.status_code == 200
    assert resp.json()["token_type"] == "bearer"
    assert resp.json()["access_token"]


def test_login_wrong_password(client):
    client.post("/api/auth/register", json={
        "username": "dave", "email": "dave@example.com", "password": "pw123456",
    })
    resp = client.post("/api/auth/login", json={
        "username": "dave", "password": "wrongpass",
    })
    assert resp.status_code == 401


def test_me_requires_token(client):
    assert client.get("/api/auth/me").status_code == 401


def test_me_returns_user(client):
    client.post("/api/auth/register", json={
        "username": "erin", "email": "erin@example.com", "password": "pw123456",
    })
    token = client.post("/api/auth/login", json={
        "username": "erin", "password": "pw123456",
    }).json()["access_token"]
    resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["username"] == "erin"
