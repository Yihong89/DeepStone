def _register(client, username, password="pw123456"):
    client.post("/api/auth/register", json={
        "username": username, "email": f"{username}@example.com", "password": password,
    })
    token = client.post("/api/auth/login", json={
        "username": username, "password": password,
    }).json()["access_token"]
    return token


def test_non_admin_forbidden(client):
    token = _register(client, "mallory")
    resp = client.get("/api/admin/users", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


def test_admin_lists_and_disables(client, admin_token):
    _register(client, "victim")
    headers = {"Authorization": f"Bearer {admin_token}"}
    users = client.get("/api/admin/users", headers=headers).json()
    victim = next(u for u in users if u["username"] == "victim")
    resp = client.patch(f"/api/admin/users/{victim['id']}", json={"is_active": False},
                        headers=headers)
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False


def test_admin_reset_password(client, admin_token):
    _register(client, "resetme")
    headers = {"Authorization": f"Bearer {admin_token}"}
    users = client.get("/api/admin/users", headers=headers).json()
    target = next(u for u in users if u["username"] == "resetme")
    resp = client.post(f"/api/admin/users/{target['id']}/reset-password",
                       json={"new_password": "freshpass"}, headers=headers)
    assert resp.status_code == 200
    # Old password no longer works
    old = client.post("/api/auth/login", json={"username": "resetme", "password": "pw123456"})
    new = client.post("/api/auth/login", json={"username": "resetme", "password": "freshpass"})
    assert old.status_code == 401
    assert new.status_code == 200
