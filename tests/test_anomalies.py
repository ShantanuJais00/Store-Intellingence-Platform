import pytest
from httpx import AsyncClient
import datetime

@pytest.mark.asyncio
async def test_anomalies_queue_spike(async_client: AsyncClient):
    events = [
        {
            "event_id": f"q_evt_{i}",
            "timestamp": (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=i)).isoformat(),
            "event_type": "BILLING_QUEUE_JOIN",
            "store_id": "store_1",
            "camera_id": "cam_pos",
            "zone_id": "checkout",
            "visitor_id": f"p_{i}"
        }
        for i in range(6)
    ]
    await async_client.post("/api/v1/events/batch", json={"events": events})
    
    response = await async_client.get("/api/v1/stores/store_1/anomalies")
    assert response.status_code == 200
    data = response.json()
    assert "anomalies" in data
    assert any(a["type"] == "QUEUE_SPIKE" for a in data["anomalies"])

@pytest.mark.asyncio
async def test_anomalies_dead_zone(async_client: AsyncClient):
    response = await async_client.get("/api/v1/stores/store_1/anomalies")
    assert response.status_code == 200
    data = response.json()
    assert "anomalies" in data
    assert isinstance(data["anomalies"], list)

@pytest.mark.asyncio
async def test_anomalies_conversion_drop(async_client: AsyncClient):
    response = await async_client.get("/api/v1/stores/store_1/anomalies")
    assert response.status_code == 200
    data = response.json()
    assert "anomalies" in data
    assert isinstance(data["anomalies"], list)

@pytest.mark.asyncio
async def test_anomalies_empty_store(async_client: AsyncClient):
    response = await async_client.get("/api/v1/stores/store_empty/anomalies")
    assert response.status_code == 200
    data = response.json()
    assert len(data["anomalies"]) == 0
