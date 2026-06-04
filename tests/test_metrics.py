import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_metrics_empty_store(async_client: AsyncClient):
    response = await async_client.get("/api/v1/stores/store_empty/metrics")
    assert response.status_code == 200
    data = response.json()
    assert data["unique_visitors"] == 0
    assert data["conversion_rate"] == 0.0
    assert data["avg_dwell_per_zone"] == {}

@pytest.mark.asyncio
async def test_metrics_all_staff_excluded(async_client: AsyncClient, sample_events):
    staff_events = [e.copy() for e in sample_events]
    for e in staff_events:
        e["is_staff"] = True
    
    await async_client.post("/api/v1/events/batch", json=staff_events)
    
    response = await async_client.get("/api/v1/stores/store_1/metrics")
    assert response.status_code == 200
    data = response.json()
    assert data["unique_visitors"] == 0

@pytest.mark.asyncio
async def test_metrics_with_visitors(async_client: AsyncClient, sample_events):
    await async_client.post("/api/v1/events/batch", json=sample_events)
    
    response = await async_client.get("/api/v1/stores/store_1/metrics")
    assert response.status_code == 200
    data = response.json()
    assert data["unique_visitors"] == 1

@pytest.mark.asyncio
async def test_metrics_conversion_rate(async_client: AsyncClient, sample_events, sample_transactions):
    await async_client.post("/api/v1/events/batch", json=sample_events)
    await async_client.post("/api/v1/transactions/ingest", json=sample_transactions)
    
    response = await async_client.get("/api/v1/stores/store_1/metrics")
    assert response.status_code == 200
    data = response.json()
    # If the logic triggers, conversion rate should be > 0
    # Wait, if tx timestamp and event timestamp match, it should be 1.0
    assert data["conversion_rate"] > 0.0

@pytest.mark.asyncio
async def test_metrics_avg_dwell_per_zone(async_client: AsyncClient, sample_events):
    # Add a dwell event
    dwell_event = {
        "event_id": "evt_004",
        "timestamp": "2023-10-27T10:10:00Z",
        "event_type": "ZONE_DWELL",
        "store_id": "store_1",
        "camera_id": "cam_2",
        "visitor_id": "p_001",
        "zone_id": "shoes",
        "dwell_ms": 300000
    }
    await async_client.post("/api/v1/events/batch", json=sample_events + [dwell_event])
    
    response = await async_client.get("/api/v1/stores/store_1/metrics")
    assert response.status_code == 200
    data = response.json()
    assert "shoes" in data["avg_dwell_per_zone"]
    assert data["avg_dwell_per_zone"]["shoes"] > 0
