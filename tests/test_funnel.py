import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_funnel_empty_store(async_client: AsyncClient):
    response = await async_client.get("/api/v1/stores/empty_store/funnel")
    assert response.status_code == 200
    data = response.json()
    assert "stages" in data
    assert all(st["count"] == 0 for st in data["stages"])

@pytest.mark.asyncio
async def test_funnel_full_journey(async_client: AsyncClient, sample_events, sample_transactions):
    await async_client.post("/api/v1/events/batch", json=sample_events)
    await async_client.post("/api/v1/transactions/ingest", json=sample_transactions)
    
    response = await async_client.get("/api/v1/stores/store_1/funnel")
    assert response.status_code == 200
    data = response.json()
    stages = {st["name"]: st["count"] for st in data["stages"]}
    assert stages.get("ENTRY", 0) > 0

@pytest.mark.asyncio
async def test_funnel_dropoff_percentages(async_client: AsyncClient, sample_events):
    await async_client.post("/api/v1/events/batch", json=sample_events)
    
    response = await async_client.get("/api/v1/stores/store_1/funnel")
    assert response.status_code == 200
    data = response.json()
    stages = data["stages"]
    assert len(stages) > 0
    assert "dropoff_pct" in stages[0]

@pytest.mark.asyncio
async def test_funnel_no_purchases(async_client: AsyncClient, sample_events):
    await async_client.post("/api/v1/events/batch", json=sample_events)
    
    response = await async_client.get("/api/v1/stores/store_1/funnel")
    assert response.status_code == 200
    data = response.json()
    stages = {st["name"]: st["count"] for st in data["stages"]}
    assert stages.get("PURCHASE", 0) == 0
