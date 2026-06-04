import uuid
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
