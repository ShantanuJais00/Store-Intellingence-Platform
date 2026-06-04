from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from datetime import datetime, timezone
import structlog
from sqlalchemy.future import select

from ..schemas import HealthResponse
from ..database import get_db
from ..models import Event

router = APIRouter()
logger = structlog.get_logger()

@router.get("/health", response_model=HealthResponse)
async def health_check(db: AsyncSession = Depends(get_db)):
    db_status = "ok"
    try:
        await db.execute(text("SELECT 1"))
    except Exception as e:
        logger.error("db_health_check_failed", error=str(e))
        db_status = "unavailable"

    last_event_timestamp = None
    stale_feed_warning = False

    if db_status == "ok":
        result = await db.execute(
            select(Event.timestamp).order_by(Event.timestamp.desc()).limit(1)
        )
        last_event = result.scalar_one_or_none()
        if last_event:
            last_event_timestamp = last_event
            now = datetime.now(timezone.utc) if last_event.tzinfo else datetime.utcnow()
            time_diff = (now - last_event).total_seconds()
            if time_diff > 600:
                stale_feed_warning = True

    status = "ok" if db_status == "ok" else "error"

    return HealthResponse(
        status=status,
        db_status=db_status,
        last_event_timestamp=last_event_timestamp,
        stale_feed_warning=stale_feed_warning,
        version="1.0.0"
    )
