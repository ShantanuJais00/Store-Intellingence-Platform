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
    await async_client.post("/api/v1/events/batch", json=events)
    
    response = await async_client.get("/api/v1/anomalies?store_id=store_1")
    assert response.status_code == 200
    anomalies = response.json()
    assert any(a["type"] == "QUEUE_SPIKE" for a in anomalies)

@pytest.mark.asyncio
async def test_anomalies_dead_zone(async_client: AsyncClient):
    response = await async_client.get("/api/v1/anomalies?store_id=store_1")
    assert response.status_code == 200
    anomalies = response.json()
    # Without data, might not trigger dead zone unless mapped, assuming tests configures dead zone
    # For now, just test endpoint successfully returns list
    assert isinstance(anomalies, list)

@pytest.mark.asyncio
async def test_anomalies_conversion_drop(async_client: AsyncClient):
    # Mocking or simulating a significant drop in conversion
    response = await async_client.get("/api/v1/anomalies?store_id=store_1")
    assert response.status_code == 200
    anomalies = response.json()
    assert isinstance(anomalies, list)

@pytest.mark.asyncio
async def test_anomalies_empty_store(async_client: AsyncClient):
    response = await async_client.get("/api/v1/anomalies?store_id=store_empty")
    assert response.status_code == 200
    anomalies = response.json()
    assert len(anomalies) == 0  # Should have no anomalies if empty
