from sqlalchemy.ext.asyncio import AsyncSession
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
