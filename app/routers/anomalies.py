from fastapi import APIRouter, Depends, Query
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
