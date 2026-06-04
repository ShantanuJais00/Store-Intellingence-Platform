import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import timedelta
from ..models import Transaction, Session, Event
from .session_service import update_session_conversion

async def correlate_pos(store_id: str, db: AsyncSession):
    unmatched_tx_query = select(Transaction).where(Transaction.store_id == store_id, Transaction.matched_visitor_id.is_(None))
    result = await db.execute(unmatched_tx_query)
    unmatched_txs = result.scalars().all()

    for tx in unmatched_txs:
        time_limit = tx.timestamp - timedelta(minutes=5)
        
        event_query = select(Event.visitor_id).where(
            Event.store_id == store_id,
            Event.zone_id.like("%BILLING%")
        ).order_by(Event.timestamp.desc()).limit(1)

        ev_result = await db.execute(event_query)
        visitor_id = ev_result.scalar_one_or_none()

        if visitor_id:
            session_query = select(Session).where(
                Session.store_id == store_id,
                Session.visitor_id == visitor_id
            ).order_by(Session.entry_time.desc()).limit(1)
            
            sess_result = await db.execute(session_query)
            session = sess_result.scalar_one_or_none()

            if session:
                await update_session_conversion(session, tx, db)
                purchase_event = Event(
                    event_id=str(uuid.uuid4()),
                    store_id=store_id,
                    visitor_id=visitor_id,
                    event_type="PURCHASE",
                    timestamp=tx.timestamp
                )
                db.add(purchase_event)
                await db.commit()
