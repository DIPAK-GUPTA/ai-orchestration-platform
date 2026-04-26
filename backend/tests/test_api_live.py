"""
Set RUN_API_TESTS=1 and a reachable postgres (same DATABASE_URL as the app) to run.

Example (host):
  export DATABASE_URL=postgresql+asyncpg://orchestrator:orchestrator_pass@127.0.0.1:15432/agentdb
  export RUN_API_TESTS=1
  cd backend && pytest tests/test_api_live.py -v
"""
import os

import pytest
from httpx import ASGITransport, AsyncClient

pytestmark = pytest.mark.asyncio


@pytest.mark.skipif(
    not os.environ.get("RUN_API_TESTS"),
    reason="Set RUN_API_TESTS=1 with DATABASE_URL to run live API tests",
)
async def test_agent_create_and_get():
    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.post(
            "/api/agents",
            json={
                "name": "API Test Agent",
                "role": "tester",
                "system_prompt": "You test.",
                "model": "gpt-4o-mini",
                "tools": [],
                "skills": [],
            },
        )
        assert r.status_code == 201, r.text
        aid = r.json()["id"]
        g = await ac.get(f"/api/agents/{aid}")
        assert g.status_code == 200
        assert g.json()["name"] == "API Test Agent"
