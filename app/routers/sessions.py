"""
Sessions router — CRUD for visitor sessions and POS correlation.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Event, Session, Transaction
from app.schemas import EventType

from pydantic import BaseModel, Field
from typing import Any

router = APIRouter()


class SessionResponse(BaseModel):
    id: int
    session_id: str
    store_id: str
    visitor_id: str
    entry_time: datetime
    exit_time: datetime | None = None
    is_reentry: bool = False
    is_staff: bool = False
    converted: bool = False
    total_dwell_ms: int = 0
    zones_visited: list | None = None

    model_config = {"from_attributes": True}


class SessionListResponse(BaseModel):
    sessions: list[SessionResponse]
    total: int


@router.get("/stores/{store_id}/sessions", response_model=SessionListResponse)
async def get_sessions(
    store_id: str,
    date: str | None = Query(None, description="Date in YYYY-MM-DD format"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> SessionListResponse:
    """
    Return paginated visitor sessions for a store.
    """
    query = select(Session).where(Session.store_id == store_id)

    if date:
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            next_day = target_date + timedelta(days=1)
            query = query.where(
                Session.entry_time >= target_date,
                Session.entry_time < next_day,
            )
        except ValueError:
            pass

    total_q = await db.execute(
        select(func.count()).select_from(query.subquery())
    )
    total = total_q.scalar() or 0

    result = await db.execute(
        query.order_by(Session.entry_time.desc()).limit(limit).offset(offset)
    )
    sessions = result.scalars().all()

    return SessionListResponse(
        sessions=[SessionResponse.model_validate(s) for s in sessions],
        total=total,
    )


@router.post("/stores/{store_id}/sessions/build", status_code=201)
async def build_sessions(
    store_id: str,
    date: str | None = Query(None, description="Date in YYYY-MM-DD"),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Build visitor sessions from raw events for a given store/date.

    Logic:
      1. Group ENTRY/EXIT events by visitor_id
      2. Mark REENTRY events
      3. Correlate with POS transactions within 5-minute billing window
    """
    if date:
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            target_date = datetime.now(timezone.utc).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
    else:
        target_date = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
    next_day = target_date + timedelta(days=1)

    # Get all events for this store/date
    events_q = await db.execute(
        select(Event)
        .where(
            Event.store_id == store_id,
            Event.timestamp >= target_date,
            Event.timestamp < next_day,
        )
        .order_by(Event.timestamp)
    )
    events = events_q.scalars().all()

    # Group by visitor_id
    visitor_events: dict[str, list[Event]] = {}
    for ev in events:
        if ev.visitor_id:
            visitor_events.setdefault(ev.visitor_id, []).append(ev)

    # Get transactions for POS correlation
    txn_q = await db.execute(
        select(Transaction).where(
            Transaction.store_id == store_id,
            Transaction.timestamp >= target_date,
            Transaction.timestamp < next_day,
        )
    )
    transactions = txn_q.scalars().all()

    created = 0
    for visitor_id, evts in visitor_events.items():
        entry_events = [
            e for e in evts if e.event_type in ("ENTRY", "REENTRY")
        ]
        exit_events = [e for e in evts if e.event_type == "EXIT"]
        zone_events = [
            e for e in evts if e.event_type in ("ZONE_ENTER", "ZONE_DWELL")
        ]
        purchase_events = [e for e in evts if e.event_type == "PURCHASE"]

        if not entry_events:
            continue

        entry_time = entry_events[0].timestamp
        exit_time = exit_events[-1].timestamp if exit_events else None

        is_reentry = any(e.event_type == "REENTRY" for e in evts)
        is_staff = any(e.is_staff for e in evts)

        zones_visited = list({e.zone_id for e in zone_events if e.zone_id})

        dwell = 0
        if exit_time and entry_time:
            if exit_time.tzinfo is None:
                exit_aware = exit_time.replace(tzinfo=timezone.utc)
            else:
                exit_aware = exit_time
            if entry_time.tzinfo is None:
                entry_aware = entry_time.replace(tzinfo=timezone.utc)
            else:
                entry_aware = entry_time
            dwell = int((exit_aware - entry_aware).total_seconds() * 1000)

        # POS correlation — check if a billing event is within 5 min of a transaction
        converted = len(purchase_events) > 0
        if not converted:
            billing_events = [
                e for e in evts if e.event_type == "BILLING_QUEUE_JOIN"
            ]
            for be in billing_events:
                be_ts = be.timestamp
                if be_ts.tzinfo is None:
                    be_ts = be_ts.replace(tzinfo=timezone.utc)
                for txn in transactions:
                    txn_ts = txn.timestamp
                    if txn_ts.tzinfo is None:
                        txn_ts = txn_ts.replace(tzinfo=timezone.utc)
                    if abs((txn_ts - be_ts).total_seconds()) <= 300:
                        converted = True
                        break
                if converted:
                    break

        session = Session(
            session_id=str(uuid.uuid4()),
            store_id=store_id,
            visitor_id=visitor_id,
            entry_time=entry_time,
            exit_time=exit_time,
            is_reentry=is_reentry,
            is_staff=is_staff,
            converted=converted,
            total_dwell_ms=dwell,
            zones_visited=zones_visited,
        )
        db.add(session)
        created += 1

    if created > 0:
        await db.commit()

    return {"sessions_created": created}
