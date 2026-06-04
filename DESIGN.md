# System Design Document

## 1. System Architecture

The Store Intelligence Platform is designed as a distributed, service-oriented architecture tailored for real-time edge AI processing and scalable cloud analytics. The architecture bifurcates the heavy compute (Computer Vision) from the transactional metrics engine (FastAPI + PostgreSQL) to ensure that the API remains responsive regardless of video processing load.

```text
+---------------------+        +---------------------+        +--------------------+
|    Edge / Store     |        |    Cloud / Server   |        |    Client Side     |
|                     |        |                     |        |                    |
| +-----------------+ |  HTTP  | +-----------------+ |        | +----------------+ |
| |  CCTV Cameras   | |  JSON  | |  Load Balancer  | |        | | React SPA Dash | |
| +-------+---------+ |  Batch | +-------+---------+ |        | +--------+-------+ |
|         |           |=======>|         |           |        |          |         |
|         v           |        |         v           |        |          |         |
| +-----------------+ |        | +-----------------+ |  REST/ |          |         |
| |   CV Pipeline   | |        | |   FastAPI App   | |<======>|          |         |
| | (YOLO+ByteTrack)| |        | | (Async Workers) | |   WS   |          |         |
| +-----------------+ |        | +-------+---------+ |        |          |         |
|                     |        |         |           |        |          |         |
+---------------------+        |         v           |        +--------------------+
                               | +-----------------+ |
                               | |  PostgreSQL 16  | |
                               | +-----------------+ |
                               +---------------------+
```

## 2. Event Flow Pipeline

The system is fundamentally event-driven. The data lifecycle traverses the following stages:

1. **Video Ingestion**: RTSP streams or video files are captured by the CV Pipeline at the edge.
2. **Object Detection**: `YOLOv8` processes frames to identify "person" bounding boxes.
3. **Tracking**: `ByteTrack` assigns temporal IDs to bounding boxes within a single camera's field of view.
4. **Re-Identification (ReID)**: `OSNet` extracts feature embeddings of detected individuals. These embeddings are compared against a store-wide active gallery to stitch cross-camera journeys into a single universal `person_id`.
5. **Zone Mapping**: The trajectory coordinates of the tracked individuals are intersected with predefined polygon zones (e.g., "entrance", "shoes", "checkout") using Point-in-Polygon (`shapely`) math.
6. **Event Generation**: Abstract movements are translated into distinct, semantic JSON events like `ENTRY`, `ZONE_ENTER`, `ZONE_EXIT`, and `QUEUE_DEPTH`.
7. **API Ingestion**: These events are buffered and POSTed in batches (up to 500 events) to the FastAPI `/events/batch` endpoint.
8. **Storage & Materialization**: FastAPI validates the schemas via Pydantic and persists them to PostgreSQL. Background tasks or views aggregate these into active sessions.
9. **Dashboard Delivery**: The React dashboard fetches aggregated metrics via REST and receives live critical anomalies (e.g., queue spikes) via WebSocket.

## 3. Data Model Design

The database schema is heavily optimized for write-heavy timeseries data while maintaining relational integrity.

- **stores**: Stores static metadata (location, name, active hours) for multiple retail locations.
- **cameras**: Defines spatial coordinates, FOV types (e.g., entry, overhead), and the store they belong to.
- **zones**: Represents physical polygons within a camera's view (e.g., shelves, registers) linked to camera IDs.
- **events**: The core timeseries table. Contains `event_id`, `timestamp`, `event_type`, `person_id`, `zone_id`, `store_id`. Heavily indexed on `(store_id, timestamp)` for fast metric aggregations.
- **transactions**: POS integration table recording successful purchases (`transaction_id`, `timestamp`, `amount`). Used to correlate with dwell sessions for conversion rate calculation.

Indices are critical here: a BRIN (Block Range Index) or B-Tree index on `timestamp` enables rapid timeseries windowing functions, while UUID primary keys prevent sequential bottlenecking during massive parallel batch inserts.

## 4. Scaling Strategy

As the platform expands to hundreds of stores, scaling is handled at multiple tiers:
- **API (Horizontal Scaling)**: FastAPI workers are completely stateless. They can be scaled horizontally behind an Nginx or AWS ALB load balancer. 
- **Database (Read Replicas & Partitioning)**: PostgreSQL handles rapid writes. We will implement table partitioning on the `events` table based on `store_id` and `date`. Read-heavy dashboard queries are routed to read-replicas.
- **Ingestion (Queue-Based)**: If API load spikes, ingestion requests are decoupled using a message broker (RabbitMQ/Redis/Kafka) replacing direct HTTP DB writes, allowing the DB to drain the queue at a sustainable pace.
- **CV Pipeline (Distributed)**: The most compute-intensive part remains on-premise at the edge, scaling naturally with the addition of edge GPU nodes per physical store.

## 5. Failure Handling

Robustness is built-in to prevent cascading failures:
- **Circuit Breakers**: If the PostgreSQL database becomes unresponsive, the API responds with 503s instead of hanging forever, signaling the Edge to buffer data locally.
- **Retry Logic & Buffering**: The CV pipeline writes events to a local JSONL cache if HTTP requests fail. An exponential backoff algorithm retries sending batches when the API recovers.
- **Graceful Degradation**: If the primary DB fails, the API can serve slightly stale metrics from an in-memory Redis cache (if implemented).
- **Stale Feed Detection**: A continuous health-check monitors the `timestamp` of the last received event per store. If no events arrive within a defined threshold (e.g., 5 minutes), the dashboard surfaces a "Stale Feed / Camera Down" warning.

## 6. AI-Assisted Design Decisions

Generative AI heavily accelerated the architecture blueprinting:
- **Model Selection**: AI analysis confirmed YOLOv8 Nano as the optimal choice over Detectron2 for our specific 30 FPS, low-VRAM edge constraint.
- **API Patterns**: The recommendation to utilize FastAPI’s `dependency_overrides` heavily simplified our isolated unit testing strategy using `aiosqlite`.
- **Heuristics**: AI suggested using logical heuristics for "staff detection" (e.g., people spending >4 hours in store or frequenting the restricted register zone) rather than training a separate costly classifier.

## 7. Performance Considerations

Performance optimization strategies include:
- **Batch Ingestion**: Network overhead is minimized by batching up to 500 events per POST request, combined with `executemany` async bulk inserts in SQLAlchemy.
- **Connection Pooling**: `asyncpg` combined with SQLAlchemy connection pooling prevents connection exhaustion under heavy Edge-node request load.
- **Frame Skipping**: The CV pipeline processes video at 15 FPS rather than the native 30/60 FPS. This halves GPU usage with negligible impact on tracking accuracy for slow-moving retail pedestrians.
- **Embedding Caching**: ReID OSNet embeddings are aggressively cached locally in FAISS to speed up cross-camera matching without re-computing tensors.
