from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime, JSON, text
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
