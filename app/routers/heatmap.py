from fastapi import APIRouter, Depends
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
