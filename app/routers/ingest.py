from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import uuid
from datetime import datetime

from ..schemas import IngestRequest, IngestResponse, TransactionCreate, ErrorResponse
from ..database import get_db
from ..models import Event, Transaction
from ..services.conversion_service import correlate_pos

router = APIRouter()

@router.post("/events/batch", response_model=IngestResponse, status_code=201)
async def ingest_events(request: IngestRequest, db: AsyncSession = Depends(get_db)):
    accepted = 0
    rejected = 0
    errors = []

    event_ids = [e.event_id for e in request.events]
    result = await db.execute(select(Event.event_id).where(Event.event_id.in_(event_ids)))
    existing_event_ids = set(row[0] for row in result.all())

    new_events = []
    for event_data in request.events:
        if event_data.event_id in existing_event_ids:
            continue
        try:
            db_event = Event(
                event_id=event_data.event_id,
                store_id=event_data.store_id,
                camera_id=event_data.camera_id,
                visitor_id=event_data.visitor_id,
                event_type=event_data.event_type.value,
                timestamp=event_data.timestamp,
                zone_id=event_data.zone_id,
                dwell_ms=event_data.dwell_ms,
                is_staff=event_data.is_staff,
                confidence=event_data.confidence,
                metadata_json=event_data.metadata
            )
            db.add(db_event)
            new_events.append(db_event)
            accepted += 1
        except Exception as e:
            rejected += 1
            errors.append({"event_id": event_data.event_id, "error": str(e)})

    if new_events:
        from ..services.session_service import build_sessions
        await build_sessions(new_events, db)
        await db.commit()
        from ..main import ws_manager
        await ws_manager.broadcast_events(new_events)

    return IngestResponse(accepted=accepted, rejected=rejected, errors=errors)

@router.post("/transactions/ingest", response_model=dict)
async def ingest_transactions(transactions: list[TransactionCreate], db: AsyncSession = Depends(get_db)):
    store_ids = set()
    for tx_data in transactions:
        tx_id = str(uuid.uuid4())
        db_tx = Transaction(
            transaction_id=tx_id,
            store_id=tx_data.store_id,
            order_id=tx_data.order_id,
            timestamp=tx_data.timestamp,
            product_id=tx_data.product_id,
            brand_name=tx_data.brand_name,
            total_amount=tx_data.total_amount
        )
        db.add(db_tx)
        store_ids.add(tx_data.store_id)
    
    await db.commit()

    for store_id in store_ids:
        await correlate_pos(store_id, db)
        
    return {"message": "Transactions ingested successfully", "count": len(transactions)}
