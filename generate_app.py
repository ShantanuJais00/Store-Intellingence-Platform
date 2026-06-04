import os

BASE_DIR = r"c:\Users\Shantanu Jaiswal\Downloads\New fol\store-intelligence"

files_to_create = {
    "app/__init__.py": "",
    
    "app/database.py": '''import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@postgres:5432/store_intelligence"
)

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(
    engine,
    expire_on_commit=False,
    class_=AsyncSession
)

Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
''',
    
    "app/models.py": '''from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime, JSON, text
from sqlalchemy.sql import func
from .database import Base

class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary key=True, autoincrement=True)
    event_id = Column(String(36), unique=True, nullable=False, index=True)
    store_id = Column(String(20), nullable=False, index=True)
    camera_id = Column(String(20))
    visitor_id = Column(String(50), index=True)
    event_type = Column(String(30), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    zone_id = Column(String(50), nullable=True)
    dwell_ms = Column(Integer, nullable=True)
    is_staff = Column(Boolean, default=False)
    confidence = Column(Float, nullable=True)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary key=True, autoincrement=True)
    session_id = Column(String(36), unique=True, nullable=False)
    store_id = Column(String(20), nullable=False, index=True)
    visitor_id = Column(String(50), nullable=False)
    entry_time = Column(DateTime, nullable=False)
    exit_time = Column(DateTime, nullable=True)
    is_reentry = Column(Boolean, default=False)
    is_staff = Column(Boolean, default=False)
    converted = Column(Boolean, default=False)
    total_dwell_ms = Column(Integer, default=0)
    zones_visited = Column(JSON, default=list)
    transaction_id = Column(String(36), nullable=True)
    created_at = Column(DateTime, server_default=func.now())

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary key=True, autoincrement=True)
    transaction_id = Column(String(36), unique=True, nullable=False)
    store_id = Column(String(20), nullable=False, index=True)
    order_id = Column(String(20))
    timestamp = Column(DateTime, nullable=False)
    product_id = Column(String(20))
    brand_name = Column(String(100))
    total_amount = Column(Float)
    matched_visitor_id = Column(String(50), nullable=True)
    created_at = Column(DateTime, server_default=func.now())

class Store(Base):
    __tablename__ = "stores"

    id = Column(Integer, primary key=True, autoincrement=True)
    store_id = Column(String(20), unique=True, nullable=False)
    name = Column(String(100))
    zones = Column(JSON, default=list)
    cameras = Column(JSON, default=list)
    created_at = Column(DateTime, server_default=func.now())

class Anomaly(Base):
    __tablename__ = "anomalies"

    id = Column(Integer, primary key=True, autoincrement=True)
    anomaly_id = Column(String(36), unique=True, nullable=False)
    store_id = Column(String(20), nullable=False, index=True)
    anomaly_type = Column(String(30), nullable=False)
    severity = Column(String(10), nullable=False)
    message = Column(String(500))
    suggested_action = Column(String(500))
    detected_at = Column(DateTime, nullable=False)
    resolved = Column(Boolean, default=False)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
''',

    "app/schemas.py": '''from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class EventType(str, Enum):
    ENTRY = "ENTRY"
    EXIT = "EXIT"
    REENTRY = "REENTRY"
    ZONE_ENTER = "ZONE_ENTER"
    ZONE_EXIT = "ZONE_EXIT"
    ZONE_DWELL = "ZONE_DWELL"
    BILLING_QUEUE_JOIN = "BILLING_QUEUE_JOIN"
    BILLING_QUEUE_ABANDON = "BILLING_QUEUE_ABANDON"
    PURCHASE = "PURCHASE"

class Severity(str, Enum):
    INFO = "INFO"
    WARN = "WARN"
    CRITICAL = "CRITICAL"

class AnomalyType(str, Enum):
    QUEUE_SPIKE = "QUEUE_SPIKE"
    CONVERSION_DROP = "CONVERSION_DROP"
    DEAD_ZONE = "DEAD_ZONE"

class EventCreate(BaseModel):
    event_id: str = Field(..., max_length=36)
    store_id: str = Field(..., max_length=20)
    camera_id: Optional[str] = Field(None, max_length=20)
    visitor_id: str = Field(..., max_length=50)
    event_type: EventType
    timestamp: datetime
    zone_id: Optional[str] = Field(None, max_length=50)
    dwell_ms: Optional[int] = None
    is_staff: bool = False
    confidence: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None

class EventResponse(EventCreate):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class IngestRequest(BaseModel):
    events: List[EventCreate] = Field(..., max_length=500)

class IngestResponse(BaseModel):
    accepted: int
    rejected: int
    errors: List[Dict[str, Any]]

class MetricsResponse(BaseModel):
    unique_visitors: int
    conversion_rate: float
    avg_dwell_per_zone: Dict[str, float]
    queue_depth: int
    abandonment_rate: float

class FunnelStage(BaseModel):
    name: str
    count: int
    dropoff_pct: float

class FunnelResponse(BaseModel):
    stages: List[FunnelStage]

class HeatmapZone(BaseModel):
    zone_id: str
    frequency: int
    avg_dwell_ms: float
    normalized_score: float
    data_confidence: str

class HeatmapResponse(BaseModel):
    zones: List[HeatmapZone]

class AnomalyResponse(BaseModel):
    anomaly_id: str
    type: AnomalyType
    severity: Severity
    message: str
    suggested_action: str
    detected_at: datetime

class AnomaliesListResponse(BaseModel):
    anomalies: List[AnomalyResponse]

class HealthResponse(BaseModel):
    status: str
    db_status: str
    last_event_timestamp: Optional[datetime]
    stale_feed_warning: bool
    version: str

class TransactionCreate(BaseModel):
    order_id: str = Field(..., max_length=20)
    store_id: str = Field(..., max_length=20)
    timestamp: datetime
    product_id: str = Field(..., max_length=20)
    brand_name: str = Field(..., max_length=100)
    total_amount: float

class ErrorResponse(BaseModel):
    error: str
''',

    "app/routers/__init__.py": "",

    "app/routers/ingest.py": '''from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import uuid
from datetime import datetime

from ..schemas import IngestRequest, IngestResponse, TransactionCreate, ErrorResponse
from ..database import get_db
from ..models import Event, Transaction
from ..services.conversion_service import correlate_pos

router = APIRouter()

@router.post("/events/ingest", response_model=IngestResponse)
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
''',

    "app/routers/metrics.py": '''from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from datetime import datetime

from ..schemas import MetricsResponse
from ..database import get_db
from ..services.metrics_service import compute_metrics

router = APIRouter()

@router.get("/stores/{store_id}/metrics", response_model=MetricsResponse)
async def get_metrics(
    store_id: str,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    db: AsyncSession = Depends(get_db)
):
    return await compute_metrics(store_id, date_from, date_to, db)
''',

    "app/routers/funnel.py": '''from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from datetime import datetime

from ..schemas import FunnelResponse
from ..database import get_db
from ..services.metrics_service import compute_funnel

router = APIRouter()

@router.get("/stores/{store_id}/funnel", response_model=FunnelResponse)
async def get_funnel(
    store_id: str,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    db: AsyncSession = Depends(get_db)
):
    return await compute_funnel(store_id, date_from, date_to, db)
''',

    "app/routers/heatmap.py": '''from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from datetime import datetime

from ..schemas import HeatmapResponse
from ..database import get_db
from ..services.metrics_service import compute_heatmap

router = APIRouter()

@router.get("/stores/{store_id}/heatmap", response_model=HeatmapResponse)
async def get_heatmap(
    store_id: str,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    db: AsyncSession = Depends(get_db)
):
    return await compute_heatmap(store_id, date_from, date_to, db)
''',

    "app/routers/anomalies.py": '''from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from ..schemas import AnomaliesListResponse, Severity
from ..database import get_db
from ..services.anomaly_service import detect_anomalies

router = APIRouter()

@router.get("/stores/{store_id}/anomalies", response_model=AnomaliesListResponse)
async def get_anomalies(
    store_id: str,
    severity: Optional[Severity] = None,
    hours_back: int = Query(24, ge=1),
    db: AsyncSession = Depends(get_db)
):
    anomalies = await detect_anomalies(store_id, db, hours_back, severity)
    return AnomaliesListResponse(anomalies=anomalies)
''',

    "app/routers/health.py": '''from fastapi import APIRouter, Depends
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
''',

    "app/services/__init__.py": "",

    "app/services/session_service.py": '''from sqlalchemy.ext.asyncio import AsyncSession
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
''',

    "app/services/metrics_service.py": '''from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from datetime import datetime
from typing import Optional
from ..models import Event, Session
from ..schemas import MetricsResponse, FunnelResponse, FunnelStage, HeatmapResponse, HeatmapZone

async def compute_metrics(store_id: str, date_from: Optional[datetime], date_to: Optional[datetime], db: AsyncSession) -> MetricsResponse:
    uv_query = select(func.count(func.distinct(Event.visitor_id))).where(
        Event.store_id == store_id,
        Event.is_staff == False,
        Event.event_type == "ENTRY"
    )
    if date_from: uv_query = uv_query.where(Event.timestamp >= date_from)
    if date_to: uv_query = uv_query.where(Event.timestamp <= date_to)
    
    uv_result = await db.execute(uv_query)
    unique_visitors = uv_result.scalar() or 0

    session_query = select(func.count(Session.id)).where(
        Session.store_id == store_id,
        Session.is_staff == False
    )
    conv_query = session_query.where(Session.converted == True)

    total_sessions = (await db.execute(session_query)).scalar() or 0
    conv_sessions = (await db.execute(conv_query)).scalar() or 0
    conversion_rate = (conv_sessions / total_sessions) if total_sessions > 0 else 0.0

    dwell_query = select(Event.zone_id, func.avg(Event.dwell_ms)).where(
        Event.store_id == store_id,
        Event.event_type == "ZONE_DWELL",
        Event.zone_id.isnot(None)
    ).group_by(Event.zone_id)
    if date_from: dwell_query = dwell_query.where(Event.timestamp >= date_from)
    if date_to: dwell_query = dwell_query.where(Event.timestamp <= date_to)
    
    dwell_res = await db.execute(dwell_query)
    avg_dwell_per_zone = {str(row[0]): float(row[1] or 0) for row in dwell_res.all()}

    join_q = select(func.count(Event.id)).where(Event.store_id == store_id, Event.event_type == "BILLING_QUEUE_JOIN")
    abandon_q = select(func.count(Event.id)).where(Event.store_id == store_id, Event.event_type == "BILLING_QUEUE_ABANDON")
    purchase_q = select(func.count(Event.id)).where(Event.store_id == store_id, Event.event_type == "PURCHASE")
    
    joins = (await db.execute(join_q)).scalar() or 0
    abandons = (await db.execute(abandon_q)).scalar() or 0
    purchases = (await db.execute(purchase_q)).scalar() or 0

    abandonment_rate = (abandons / joins) if joins > 0 else 0.0
    queue_depth = max(0, joins - abandons - purchases)

    return MetricsResponse(
        unique_visitors=unique_visitors,
        conversion_rate=conversion_rate,
        avg_dwell_per_zone=avg_dwell_per_zone,
        queue_depth=queue_depth,
        abandonment_rate=abandonment_rate
    )

async def compute_funnel(store_id: str, date_from: Optional[datetime], date_to: Optional[datetime], db: AsyncSession) -> FunnelResponse:
    q_entry = select(func.count(Event.id)).where(Event.store_id == store_id, Event.is_staff == False, Event.event_type == "ENTRY")
    if date_from: q_entry = q_entry.where(Event.timestamp >= date_from)
    if date_to: q_entry = q_entry.where(Event.timestamp <= date_to)
    entry_count = (await db.execute(q_entry)).scalar() or 0

    q_zone = select(func.count(func.distinct(Event.visitor_id))).where(Event.store_id == store_id, Event.event_type == "ZONE_ENTER")
    if date_from: q_zone = q_zone.where(Event.timestamp >= date_from)
    if date_to: q_zone = q_zone.where(Event.timestamp <= date_to)
    zone_count = (await db.execute(q_zone)).scalar() or 0

    q_billing = select(func.count(func.distinct(Event.visitor_id))).where(Event.store_id == store_id, Event.event_type == "BILLING_QUEUE_JOIN")
    if date_from: q_billing = q_billing.where(Event.timestamp >= date_from)
    if date_to: q_billing = q_billing.where(Event.timestamp <= date_to)
    billing_count = (await db.execute(q_billing)).scalar() or 0

    q_purchase = select(func.count(func.distinct(Event.visitor_id))).where(Event.store_id == store_id, Event.event_type == "PURCHASE")
    if date_from: q_purchase = q_purchase.where(Event.timestamp >= date_from)
    if date_to: q_purchase = q_purchase.where(Event.timestamp <= date_to)
    purchase_count = (await db.execute(q_purchase)).scalar() or 0

    stages = [
        {"name": "ENTRY", "count": entry_count},
        {"name": "ZONE_VISIT", "count": zone_count},
        {"name": "BILLING", "count": billing_count},
        {"name": "PURCHASE", "count": purchase_count}
    ]

    funnel_stages = []
    prev_count = 0
    for i, st in enumerate(stages):
        dropoff = 0.0
        if i > 0 and prev_count > 0:
            dropoff = max(0.0, float((prev_count - st["count"]) / prev_count * 100))
        funnel_stages.append(FunnelStage(name=st["name"], count=st["count"], dropoff_pct=dropoff))
        prev_count = st["count"]

    return FunnelResponse(stages=funnel_stages)

async def compute_heatmap(store_id: str, date_from: Optional[datetime], date_to: Optional[datetime], db: AsyncSession) -> HeatmapResponse:
    freq_q = select(Event.zone_id, func.count(Event.id)).where(Event.store_id == store_id, Event.event_type == "ZONE_ENTER", Event.zone_id.isnot(None)).group_by(Event.zone_id)
    if date_from: freq_q = freq_q.where(Event.timestamp >= date_from)
    if date_to: freq_q = freq_q.where(Event.timestamp <= date_to)
    freq_res = await db.execute(freq_q)
    frequencies = {str(row[0]): int(row[1]) for row in freq_res.all()}

    dwell_q = select(Event.zone_id, func.avg(Event.dwell_ms)).where(Event.store_id == store_id, Event.event_type == "ZONE_DWELL", Event.zone_id.isnot(None)).group_by(Event.zone_id)
    if date_from: dwell_q = dwell_q.where(Event.timestamp >= date_from)
    if date_to: dwell_q = dwell_q.where(Event.timestamp <= date_to)
    dwell_res = await db.execute(dwell_q)
    avg_dwells = {str(row[0]): float(row[1] or 0) for row in dwell_res.all()}

    max_freq = max(frequencies.values()) if frequencies else 1

    zones = []
    all_zones = set(frequencies.keys()).union(avg_dwells.keys())
    for zid in all_zones:
        f = frequencies.get(zid, 0)
        ad = avg_dwells.get(zid, 0.0)
        ns = (f / max_freq) * 100 if max_freq > 0 else 0
        dc = "high" if f > 50 else ("medium" if f > 10 else "low")
        zones.append(HeatmapZone(
            zone_id=zid,
            frequency=f,
            avg_dwell_ms=ad,
            normalized_score=ns,
            data_confidence=dc
        ))

    return HeatmapResponse(zones=zones)
''',

    "app/services/anomaly_service.py": '''from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from datetime import datetime, timedelta, timezone
import uuid
from typing import Optional

from ..models import Anomaly, Event, Session
from ..schemas import AnomalyResponse, AnomalyType, Severity

async def detect_anomalies(store_id: str, db: AsyncSession, hours_back: int = 24, severity: Optional[Severity] = None) -> list[AnomalyResponse]:
    anomalies = []
    
    qs_anomaly = await check_queue_spike(store_id, db)
    if qs_anomaly: anomalies.append(qs_anomaly)

    cd_anomaly = await check_conversion_drop(store_id, db)
    if cd_anomaly: anomalies.append(cd_anomaly)

    dz_anomalies = await check_dead_zones(store_id, db)
    anomalies.extend(dz_anomalies)

    result = []
    for a in anomalies:
        if not severity or a.severity == severity.value:
            result.append(AnomalyResponse(
                anomaly_id=a.anomaly_id,
                type=AnomalyType(a.anomaly_type),
                severity=Severity(a.severity),
                message=a.message,
                suggested_action=a.suggested_action,
                detected_at=a.detected_at
            ))
    return result

async def check_queue_spike(store_id: str, db: AsyncSession) -> Optional[Anomaly]:
    join_q = select(func.count(Event.id)).where(Event.store_id == store_id, Event.event_type == "BILLING_QUEUE_JOIN")
    abandon_q = select(func.count(Event.id)).where(Event.store_id == store_id, Event.event_type == "BILLING_QUEUE_ABANDON")
    purchase_q = select(func.count(Event.id)).where(Event.store_id == store_id, Event.event_type == "PURCHASE")
    
    joins = (await db.execute(join_q)).scalar() or 0
    abandons = (await db.execute(abandon_q)).scalar() or 0
    purchases = (await db.execute(purchase_q)).scalar() or 0

    queue_depth = max(0, joins - abandons - purchases)

    if queue_depth > 5:
        anomaly = Anomaly(
            anomaly_id=str(uuid.uuid4()),
            store_id=store_id,
            anomaly_type="QUEUE_SPIKE",
            severity="WARN",
            message=f"High queue depth detected: {queue_depth}",
            suggested_action="Open an additional billing counter.",
            detected_at=datetime.utcnow()
        )
        db.add(anomaly)
        await db.commit()
        return anomaly
    return None

async def check_conversion_drop(store_id: str, db: AsyncSession) -> Optional[Anomaly]:
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    seven_days_ago = today_start - timedelta(days=7)

    tot_7d = (await db.execute(select(func.count(Session.id)).where(Session.store_id == store_id, Session.created_at >= seven_days_ago, Session.created_at < today_start))).scalar() or 0
    conv_7d = (await db.execute(select(func.count(Session.id)).where(Session.store_id == store_id, Session.converted == True, Session.created_at >= seven_days_ago, Session.created_at < today_start))).scalar() or 0
    avg_7d_rate = (conv_7d / tot_7d) if tot_7d > 0 else 0.0

    tot_tdy = (await db.execute(select(func.count(Session.id)).where(Session.store_id == store_id, Session.created_at >= today_start))).scalar() or 0
    conv_tdy = (await db.execute(select(func.count(Session.id)).where(Session.store_id == store_id, Session.converted == True, Session.created_at >= today_start))).scalar() or 0
    tdy_rate = (conv_tdy / tot_tdy) if tot_tdy > 0 else 0.0

    if avg_7d_rate > 0 and (avg_7d_rate - tdy_rate) / avg_7d_rate > 0.2:
        anomaly = Anomaly(
            anomaly_id=str(uuid.uuid4()),
            store_id=store_id,
            anomaly_type="CONVERSION_DROP",
            severity="CRITICAL",
            message=f"Conversion dropped by more than 20% compared to 7-day average.",
            suggested_action="Investigate store operations and POS systems.",
            detected_at=now
        )
        db.add(anomaly)
        await db.commit()
        return anomaly
    return None

async def check_dead_zones(store_id: str, db: AsyncSession) -> list[Anomaly]:
    now = datetime.utcnow()
    thirty_mins_ago = now - timedelta(minutes=30)
    
    all_zones = (await db.execute(select(func.distinct(Event.zone_id)).where(Event.store_id == store_id, Event.zone_id.isnot(None)))).scalars().all()
    active_zones = (await db.execute(select(func.distinct(Event.zone_id)).where(Event.store_id == store_id, Event.zone_id.isnot(None), Event.timestamp >= thirty_mins_ago))).scalars().all()

    anomalies = []
    for zone in all_zones:
        if zone not in active_zones:
            anomaly = Anomaly(
                anomaly_id=str(uuid.uuid4()),
                store_id=store_id,
                anomaly_type="DEAD_ZONE",
                severity="INFO",
                message=f"No activity in zone {zone} for 30 minutes.",
                suggested_action="Check camera feed or store layout.",
                detected_at=now
            )
            db.add(anomaly)
            anomalies.append(anomaly)
    
    if anomalies:
        await db.commit()
    return anomalies
''',

    "app/services/conversion_service.py": '''from sqlalchemy.ext.asyncio import AsyncSession
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
            Event.event_type == "BILLING_QUEUE_JOIN",
            Event.timestamp >= time_limit,
            Event.timestamp <= tx.timestamp
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
''',

    "app/repositories/__init__.py": "",

    "app/middleware/__init__.py": "",

    "app/middleware/logging_middleware.py": '''import uuid
import time
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request
from fastapi.responses import JSONResponse
import structlog
from sqlalchemy.exc import SQLAlchemyError

logger = structlog.get_logger()

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        trace_id = str(uuid.uuid4())
        start_time = time.time()
        
        store_id = request.path_params.get("store_id", "unknown")

        try:
            response = await call_next(request)
            latency_ms = int((time.time() - start_time) * 1000)
            
            logger.info(
                "request_completed",
                trace_id=trace_id,
                store_id=store_id,
                endpoint=request.url.path,
                method=request.method,
                latency_ms=latency_ms,
                status_code=response.status_code
            )
            return response
            
        except SQLAlchemyError as e:
            latency_ms = int((time.time() - start_time) * 1000)
            logger.error(
                "database_error",
                trace_id=trace_id,
                store_id=store_id,
                endpoint=request.url.path,
                method=request.method,
                latency_ms=latency_ms,
                status_code=503,
                error=str(e)
            )
            return JSONResponse(
                status_code=503,
                content={"error": "DATABASE_UNAVAILABLE"}
            )
        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            logger.error(
                "internal_error",
                trace_id=trace_id,
                store_id=store_id,
                endpoint=request.url.path,
                method=request.method,
                latency_ms=latency_ms,
                status_code=500,
                error=str(e)
            )
            return JSONResponse(
                status_code=500,
                content={"error": "INTERNAL_SERVER_ERROR"}
            )
''',

    "app/main.py": '''from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import structlog
import asyncio
from typing import List

from .routers import ingest, metrics, funnel, heatmap, anomalies, health
from .middleware.logging_middleware import LoggingMiddleware

logger = structlog.get_logger()

app = FastAPI(
    title="Store Intelligence Platform API",
    description="Backend for Store Intelligence Platform",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(LoggingMiddleware)

app.include_router(health.router, tags=["Health"])
app.include_router(ingest.router, tags=["Ingest"])
app.include_router(metrics.router, tags=["Metrics"])
app.include_router(funnel.router, tags=["Funnel"])
app.include_router(heatmap.router, tags=["Heatmap"])
app.include_router(anomalies.router, tags=["Anomalies"])

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast_events(self, events: list):
        if not self.active_connections:
            return
        
        event_data = []
        for e in events:
            event_data.append({
                "event_id": e.event_id,
                "store_id": e.store_id,
                "event_type": e.event_type,
                "timestamp": e.timestamp.isoformat() if e.timestamp else None,
            })
            
        for connection in self.active_connections:
            try:
                await connection.send_json({"type": "NEW_EVENTS", "data": event_data})
            except Exception as e:
                logger.error("ws_broadcast_failed", error=str(e))

ws_manager = ConnectionManager()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)

@app.on_event("startup")
async def startup_event():
    logger.info("app_startup", message="Store Intelligence Platform API started.")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("app_shutdown", message="Store Intelligence Platform API shutting down.")
''',

    "alembic.ini": '''[alembic]
script_location = alembic
sqlalchemy.url = postgresql+asyncpg://postgres:postgres@postgres:5432/store_intelligence

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
''',

    "alembic/env.py": '''import asyncio
from logging.config import fileConfig
import os

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

from app.models import Base

config = context.config

if "DATABASE_URL" in os.environ:
    config.set_main_option("sqlalchemy.url", os.environ["DATABASE_URL"])

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()

async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()

def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
''',

    "alembic/script.mako": '''"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

revision: str = ${repr(up_revision)}
down_revision: Union[str, None] = ${repr(down_revision)}
branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}
depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
''',

    "alembic/versions/001_initial_tables.py": '''"""initial_tables

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('stores',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('store_id', sa.String(length=20), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=True),
        sa.Column('zones', sa.JSON(), nullable=True),
        sa.Column('cameras', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('store_id')
    )
    op.create_table('events',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('event_id', sa.String(length=36), nullable=False),
        sa.Column('store_id', sa.String(length=20), nullable=False),
        sa.Column('camera_id', sa.String(length=20), nullable=True),
        sa.Column('visitor_id', sa.String(length=50), nullable=True),
        sa.Column('event_type', sa.String(length=30), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('zone_id', sa.String(length=50), nullable=True),
        sa.Column('dwell_ms', sa.Integer(), nullable=True),
        sa.Column('is_staff', sa.Boolean(), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('metadata_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_events_event_id'), 'events', ['event_id'], unique=True)
    op.create_index(op.f('ix_events_event_type'), 'events', ['event_type'], unique=False)
    op.create_index(op.f('ix_events_store_id'), 'events', ['store_id'], unique=False)
    op.create_index(op.f('ix_events_timestamp'), 'events', ['timestamp'], unique=False)
    op.create_index(op.f('ix_events_visitor_id'), 'events', ['visitor_id'], unique=False)
    
    op.create_table('sessions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('session_id', sa.String(length=36), nullable=False),
        sa.Column('store_id', sa.String(length=20), nullable=False),
        sa.Column('visitor_id', sa.String(length=50), nullable=False),
        sa.Column('entry_time', sa.DateTime(), nullable=False),
        sa.Column('exit_time', sa.DateTime(), nullable=True),
        sa.Column('is_reentry', sa.Boolean(), nullable=True),
        sa.Column('is_staff', sa.Boolean(), nullable=True),
        sa.Column('converted', sa.Boolean(), nullable=True),
        sa.Column('total_dwell_ms', sa.Integer(), nullable=True),
        sa.Column('zones_visited', sa.JSON(), nullable=True),
        sa.Column('transaction_id', sa.String(length=36), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('session_id')
    )
    op.create_index(op.f('ix_sessions_store_id'), 'sessions', ['store_id'], unique=False)
    
    op.create_table('transactions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('transaction_id', sa.String(length=36), nullable=False),
        sa.Column('store_id', sa.String(length=20), nullable=False),
        sa.Column('order_id', sa.String(length=20), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('product_id', sa.String(length=20), nullable=True),
        sa.Column('brand_name', sa.String(length=100), nullable=True),
        sa.Column('total_amount', sa.Float(), nullable=True),
        sa.Column('matched_visitor_id', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('transaction_id')
    )
    op.create_index(op.f('ix_transactions_store_id'), 'transactions', ['store_id'], unique=False)
    
    op.create_table('anomalies',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('anomaly_id', sa.String(length=36), nullable=False),
        sa.Column('store_id', sa.String(length=20), nullable=False),
        sa.Column('anomaly_type', sa.String(length=30), nullable=False),
        sa.Column('severity', sa.String(length=10), nullable=False),
        sa.Column('message', sa.String(length=500), nullable=True),
        sa.Column('suggested_action', sa.String(length=500), nullable=True),
        sa.Column('detected_at', sa.DateTime(), nullable=False),
        sa.Column('resolved', sa.Boolean(), nullable=True),
        sa.Column('metadata_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('anomaly_id')
    )
    op.create_index(op.f('ix_anomalies_store_id'), 'anomalies', ['store_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_anomalies_store_id'), table_name='anomalies')
    op.drop_table('anomalies')
    op.drop_index(op.f('ix_transactions_store_id'), table_name='transactions')
    op.drop_table('transactions')
    op.drop_index(op.f('ix_sessions_store_id'), table_name='sessions')
    op.drop_table('sessions')
    op.drop_index(op.f('ix_events_visitor_id'), table_name='events')
    op.drop_index(op.f('ix_events_timestamp'), table_name='events')
    op.drop_index(op.f('ix_events_store_id'), table_name='events')
    op.drop_index(op.f('ix_events_event_type'), table_name='events')
    op.drop_index(op.f('ix_events_event_id'), table_name='events')
    op.drop_table('events')
    op.drop_table('stores')
'''
}

for path, content in files_to_create.items():
    full_path = os.path.join(BASE_DIR, path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)
print("Files generated successfully!")
