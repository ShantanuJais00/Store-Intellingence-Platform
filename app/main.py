from fastapi import FastAPI, WebSocket, WebSocketDisconnect, APIRouter
from fastapi.middleware.cors import CORSMiddleware
import structlog
import asyncio
from typing import List

from .routers import ingest, metrics, funnel, heatmap, anomalies, health, sessions
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

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router, tags=["Health"])
api_router.include_router(ingest.router, tags=["Ingest"])
api_router.include_router(metrics.router, tags=["Metrics"])
api_router.include_router(funnel.router, tags=["Funnel"])
api_router.include_router(heatmap.router, tags=["Heatmap"])
api_router.include_router(anomalies.router, tags=["Anomalies"])
api_router.include_router(sessions.router, tags=["Sessions"])

app.include_router(api_router)

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
