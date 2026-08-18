"""
Tests for FastAPI REST Endpoints
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_endpoint(async_client: AsyncClient):
    resp = await async_client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["service"] == "tanvelo-memory"
    assert data["version"] == "1.0.0"


@pytest.mark.asyncio
async def test_auth_and_protected_endpoints(async_client: AsyncClient, user_a: dict):
    raw_key = user_a["raw_key"]
    headers = {"Authorization": f"Bearer {raw_key}"}

    # 1. Test /v1/auth/me with valid token
    me_resp = await async_client.get("/v1/auth/me", headers=headers)
    assert me_resp.status_code == 200
    assert me_resp.json()["user_id"] == user_a["user"].id

    # 2. Test without auth token -> 401 Unauthorized
    unauth_resp = await async_client.get("/v1/auth/me")
    assert unauth_resp.status_code == 401

    # 3. Test Save Memory via REST API
    save_payload = {
        "content": "Remember that Tanvelo uses FastAPI and Supabase.",
        "type": "project_fact"
    }
    save_resp = await async_client.post("/v1/memories", json=save_payload, headers=headers)
    assert save_resp.status_code == 200
    save_data = save_resp.json()
    assert save_data["success"] is True
    mem_id = save_data["memory_id"]
    assert mem_id is not None

    # 4. Test List Memories
    list_resp = await async_client.get("/v1/memories", headers=headers)
    assert list_resp.status_code == 200
    assert list_resp.json()["total"] >= 1

    # 5. Test Search Memories
    search_resp = await async_client.post(
        "/v1/search",
        json={"query": "What database does Tanvelo use?"},
        headers=headers
    )
    assert search_resp.status_code == 200
    search_data = search_resp.json()
    assert len(search_data["memories"]) >= 1

    # 6. Test Context Retrieval
    ctx_resp = await async_client.post(
        "/v1/context",
        json={"query": "Tanvelo stack architecture"},
        headers=headers
    )
    assert ctx_resp.status_code == 200
    ctx_data = ctx_resp.json()
    assert "FastAPI" in ctx_data["context"]

    # 7. Test Delete Memory
    del_resp = await async_client.delete(f"/v1/memories/{mem_id}", headers=headers)
    assert del_resp.status_code == 200
    assert del_resp.json()["success"] is True
