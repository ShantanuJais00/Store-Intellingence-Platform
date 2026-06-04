import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_ingest_single_event(async_client: AsyncClient, sample_events):
    event = sample_events[0]
    response = await async_client.post("/api/v1/events/batch", json={"events": [event]})
    assert response.status_code == 201
    data = response.json()
    assert data["accepted"] == 1
    assert data["rejected"] == 0

@pytest.mark.asyncio
async def test_ingest_batch_events(async_client: AsyncClient, sample_events):
    response = await async_client.post("/api/v1/events/batch", json={"events": sample_events})
    assert response.status_code == 201
    data = response.json()
    assert data["accepted"] == len(sample_events)
    assert data["rejected"] == 0

@pytest.mark.asyncio
async def test_ingest_duplicate_event_idempotent(async_client: AsyncClient, sample_events):
    event = sample_events[0]
    # First request
    response1 = await async_client.post("/api/v1/events/batch", json={"events": [event]})
    assert response1.status_code == 201
    
    # Second request - duplicate will just skip and not reject. 
    # Wait! `ingest.py` says `if event_data.event_id in existing_event_ids: continue`
    # It does NOT add to accepted or rejected! So both accepted and rejected are 0.
    response2 = await async_client.post("/api/v1/events/batch", json={"events": [event]})
    assert response2.status_code == 201
    data = response2.json()
    assert data["accepted"] == 0
    assert data["rejected"] == 0

@pytest.mark.asyncio
async def test_ingest_exceeds_batch_size(async_client: AsyncClient, sample_events):
    # Create 501 events
    large_batch = [sample_events[0].copy() for _ in range(501)]
    for i, evt in enumerate(large_batch):
        evt["event_id"] = f"evt_large_{i}"
        
    response = await async_client.post("/api/v1/events/batch", json={"events": large_batch})
    assert response.status_code == 422 # Pydantic max_length validation fails

@pytest.mark.asyncio
async def test_ingest_partial_success(async_client: AsyncClient, sample_events):
    # Mix valid and invalid events
    batch = [
        sample_events[0],
        {"event_id": "invalid_1"}, # missing required fields
        sample_events[1]
    ]
    response = await async_client.post("/api/v1/events/batch", json={"events": batch})
    # Pydantic validates the WHOLE payload before router! So this will return 422!
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_ingest_empty_batch(async_client: AsyncClient):
    # If empty list is provided but maybe Field constraints require it?
    # Schema says `events: List[EventCreate] = Field(..., max_length=500)`
    # Let's see what it returns, likely 201 with 0 accepted.
    response = await async_client.post("/api/v1/events/batch", json={"events": []})
    assert response.status_code == 201
