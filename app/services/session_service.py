from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime
import uuid
from ..models import Session, Event, Transaction

async def build_sessions(events: list[Event], db: AsyncSession):
    visitor_events = {}
    for ev in events:
        visitor_events.setdefault(ev.visitor_id, []).append(ev)
    
    for visitor_id, evs in visitor_events.items():
        evs.sort(key=lambda x: x.timestamp)
        for ev in evs:
            if ev.event_type == "ENTRY":
                session = Session(
                    session_id=str(uuid.uuid4()),
                    store_id=ev.store_id,
                    visitor_id=visitor_id,
                    entry_time=ev.timestamp,
                    is_staff=ev.is_staff
                )
                db.add(session)
            elif ev.event_type == "EXIT":
                stmt = select(Session).where(
                    Session.visitor_id == visitor_id,
                    Session.store_id == ev.store_id,
                    Session.exit_time.is_(None)
                ).order_by(Session.entry_time.desc()).limit(1)
                result = await db.execute(stmt)
                session = result.scalar_one_or_none()
                if session:
                    session.exit_time = ev.timestamp
            elif ev.event_type == "ZONE_ENTER":
                stmt = select(Session).where(
                    Session.visitor_id == visitor_id,
                    Session.store_id == ev.store_id,
                    Session.exit_time.is_(None)
                ).order_by(Session.entry_time.desc()).limit(1)
                result = await db.execute(stmt)
                session = result.scalar_one_or_none()
                if session and ev.zone_id:
                    zones = list(session.zones_visited) if session.zones_visited else []
                    if ev.zone_id not in zones:
                        zones.append(ev.zone_id)
                        session.zones_visited = zones
            elif ev.event_type == "ZONE_DWELL":
                stmt = select(Session).where(
                    Session.visitor_id == visitor_id,
                    Session.store_id == ev.store_id,
                    Session.exit_time.is_(None)
                ).order_by(Session.entry_time.desc()).limit(1)
                result = await db.execute(stmt)
                session = result.scalar_one_or_none()
                if session and ev.dwell_ms:
                    session.total_dwell_ms = (session.total_dwell_ms or 0) + ev.dwell_ms

    await db.commit()

async def update_session_conversion(session: Session, transaction: Transaction, db: AsyncSession):
    session.converted = True
    session.transaction_id = transaction.transaction_id
    transaction.matched_visitor_id = session.visitor_id
    await db.commit()
