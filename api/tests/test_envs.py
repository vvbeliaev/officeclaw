import pytest


@pytest.fixture
async def user_id(client):
    resp = await client.post("/users", json={"email": "env-owner@example.com"})
    return resp.json()["id"]


async def test_create_env(client, user_id):
    resp = await client.post("/envs", json={
        "user_id": user_id, "name": "anthropic", "values": {"ANTHROPIC_API_KEY": "sk-ant-test"}
    })
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "anthropic"
    assert "values" not in body
    assert "values_encrypted" not in body


async def test_create_env_duplicate_name(client, user_id):
    await client.post("/envs", json={"user_id": user_id, "name": "dupe", "values": {}})
    resp = await client.post("/envs", json={"user_id": user_id, "name": "dupe", "values": {}})
    assert resp.status_code == 409


async def test_list_envs(client, user_id):
    await client.post("/envs", json={"user_id": user_id, "name": "env1", "values": {}})
    await client.post("/envs", json={"user_id": user_id, "name": "env2", "values": {}})
    resp = await client.get(f"/envs?user_id={user_id}")
    # user registration creates 1 'officeclaw' env; 2 more added above = 3 total
    assert len(resp.json()) == 3
    for env in resp.json():
        assert "values" not in env


async def test_delete_env(client, user_id):
    create = await client.post("/envs", json={"user_id": user_id, "name": "todel", "values": {}})
    env_id = create.json()["id"]
    assert (await client.delete(f"/envs/{env_id}")).status_code == 204
