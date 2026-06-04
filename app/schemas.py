from pydantic import BaseModel, Field
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
