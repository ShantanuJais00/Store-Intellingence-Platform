import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_session_creation(async_client: AsyncClient, sample_events):
    await async_client.post("/api/v1/events/batch", json={"events": sample_events})
    await async_client.post("/api/v1/stores/store_1/sessions/build?date=2023-10-27")
    
    response = await async_client.get("/api/v1/stores/store_1/sessions?date=2023-10-27")
    assert response.status_code == 200
    data = response.json()
    sessions = data["sessions"]
    assert len(sessions) > 0
    assert sessions[0]["visitor_id"] == "p_001"

@pytest.mark.asyncio
async def test_reentry_detection(async_client: AsyncClient):
    events = [
        {
            "event_id": "r_evt_1",
            "timestamp": "2023-10-27T10:00:00Z",
            "event_type": "ENTRY",
            "store_id": "store_1",
            "camera_id": "cam_1",
            "visitor_id": "p_002",
        },
        {
            "event_id": "r_evt_2",
            "timestamp": "2023-10-27T10:30:00Z",
            "event_type": "EXIT",
            "store_id": "store_1",
            "camera_id": "cam_1",
            "visitor_id": "p_002",
        },
        {
            "event_id": "r_evt_3",
            "timestamp": "2023-10-27T10:45:00Z",
            "event_type": "REENTRY",
            "store_id": "store_1",
            "camera_id": "cam_1",
            "visitor_id": "p_002",
        }
    ]
    await async_client.post("/api/v1/events/batch", json={"events": events})
    await async_client.post("/api/v1/stores/store_1/sessions/build?date=2023-10-27")
    
    response = await async_client.get("/api/v1/stores/store_1/sessions?date=2023-10-27")
    assert response.status_code == 200
    data = response.json()
    sessions = data["sessions"]
    assert len(sessions) >= 1
    # The session should be marked as re-entry since REENTRY event exists
    assert any(s.get("is_reentry") is True for s in sessions)

@pytest.mark.asyncio
async def test_no_purchases(async_client: AsyncClient, sample_events):
    await async_client.post("/api/v1/events/batch", json={"events": sample_events})
    await async_client.post("/api/v1/stores/store_1/sessions/build?date=2023-10-27")
    
    response = await async_client.get("/api/v1/stores/store_1/sessions?date=2023-10-27")
    assert response.status_code == 200
    data = response.json()
    sessions = data["sessions"]
    assert all(s.get("converted", False) == False for s in sessions)

@pytest.mark.asyncio
async def test_pos_correlation(async_client: AsyncClient, sample_events, sample_transactions):
    # Make sure we add a BILLING_QUEUE_JOIN event so correlation works!
    billing_event = {
        "event_id": "evt_004",
        "timestamp": "2023-10-27T10:12:00Z",
        "event_type": "BILLING_QUEUE_JOIN",
        "store_id": "store_1",
        "camera_id": "cam_pos",
        "visitor_id": "p_001",
        "zone_id": "checkout"
    }
    await async_client.post("/api/v1/events/batch", json={"events": sample_events + [billing_event]})
    await async_client.post("/api/v1/transactions/ingest", json=sample_transactions)
    await async_client.post("/api/v1/stores/store_1/sessions/build?date=2023-10-27")
    
    response = await async_client.get("/api/v1/stores/store_1/sessions?date=2023-10-27")
    assert response.status_code == 200
    data = response.json()
    sessions = data["sessions"]
    assert len(sessions) > 0
    # The session for p_001 should be correlated since billing event + transaction align within 5 min
    assert any(s.get("converted") is True for s in sessions)
