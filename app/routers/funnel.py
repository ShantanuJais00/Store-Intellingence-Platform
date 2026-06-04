from fastapi import APIRouter, Depends
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
