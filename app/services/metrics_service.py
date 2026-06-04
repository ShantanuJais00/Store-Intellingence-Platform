from sqlalchemy.ext.asyncio import AsyncSession
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

    join_q = select(func.count(Event.id)).where(Event.store_id == store_id, Event.zone_id.like("%BILLING%"))
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

    q_billing = select(func.count(func.distinct(Event.visitor_id))).where(Event.store_id == store_id, Event.zone_id.like("%BILLING%"))
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
