# api/tests/test_skills.py
import pytest


@pytest.fixture
async def user_id(client):
    resp = await client.post("/users", json={"email": "skill-owner@example.com"})
    return resp.json()["id"]


async def test_create_skill(client, user_id):
    resp = await client.post("/skills", json={
        "user_id": user_id, "name": "research", "description": "Web research skill"
    })
    assert resp.status_code == 201
    assert resp.json()["name"] == "research"


async def test_upsert_skill_file(client, user_id):
    skill = await client.post("/skills", json={"user_id": user_id, "name": "s1"})
    skill_id = skill.json()["id"]
    resp = await client.put(f"/skills/{skill_id}/files", json={
        "path": "SKILL.md", "content": "# Research Skill\n..."
    })
    assert resp.status_code == 200
    assert resp.json()["path"] == "SKILL.md"


async def test_list_skill_files(client, user_id):
    skill = await client.post("/skills", json={"user_id": user_id, "name": "s2"})
    skill_id = skill.json()["id"]
    await client.put(f"/skills/{skill_id}/files", json={"path": "SKILL.md", "content": "x"})
    await client.put(f"/skills/{skill_id}/files", json={"path": "scripts/run.sh", "content": "y"})
    resp = await client.get(f"/skills/{skill_id}/files")
    assert len(resp.json()) == 2
