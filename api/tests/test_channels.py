import pytest


@pytest.fixture
async def user_id(client):
    resp = await client.post("/users", json={"email": "chan-owner@example.com"})
    return resp.json()["id"]


async def test_create_channel(client, user_id):
    resp = await client.post("/channels", json={
        "user_id": user_id, "type": "telegram",
        "config": {"token": "bot:12345", "allow_from": ["111222333"]}
    })
    assert resp.status_code == 201
    body = resp.json()
    assert body["type"] == "telegram"
    assert "config" not in body
    assert "config_encrypted" not in body


async def test_list_channels(client, user_id):
    await client.post("/channels", json={"user_id": user_id, "type": "telegram", "config": {}})
    await client.post("/channels", json={"user_id": user_id, "type": "discord", "config": {}})
    resp = await client.get(f"/channels?user_id={user_id}")
    assert len(resp.json()) == 2


async def test_delete_channel(client, user_id):
    create = await client.post("/channels", json={"user_id": user_id, "type": "telegram", "config": {}})
    channel_id = create.json()["id"]
    assert (await client.delete(f"/channels/{channel_id}")).status_code == 204
