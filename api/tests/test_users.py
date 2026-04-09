# api/tests/test_users.py
async def test_create_user(client):
    resp = await client.post("/users", json={"email": "alice@example.com"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == "alice@example.com"
    assert "id" in body
    assert "created_at" in body


async def test_create_user_duplicate_email(client):
    await client.post("/users", json={"email": "bob@example.com"})
    resp = await client.post("/users", json={"email": "bob@example.com"})
    assert resp.status_code == 409


async def test_get_user(client):
    create = await client.post("/users", json={"email": "carol@example.com"})
    user_id = create.json()["id"]
    resp = await client.get(f"/users/{user_id}")
    assert resp.status_code == 200
    assert resp.json()["email"] == "carol@example.com"


async def test_get_user_not_found(client):
    resp = await client.get("/users/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404
