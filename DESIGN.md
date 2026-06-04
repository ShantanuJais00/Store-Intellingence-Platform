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

Generative AI (GPT-4 / Gemini) was used extensively as a **design co-pilot** throughout the project. Below is a detailed accounting of every significant decision where AI analysis influenced the outcome.

### 6.1 Architecture Blueprinting

**Prompt**: "Design a scalable architecture for a real-time retail footfall analytics platform that processes CCTV feeds at the edge and exposes analytics via a REST API."

**AI Recommendation**: Bifurcate compute into two independent tiers — a GPU-bound CV pipeline at the edge and a stateless API tier in the cloud — connected via batched HTTP POST. The AI explicitly recommended against a monolithic approach where video processing and API serving share the same process, citing GPU memory contention and the inability to scale API workers independently.

**Adopted**: Yes. This is the foundational architecture of the platform. The CV pipeline runs as a separate process (`cv/run_pipeline.py`) and pushes JSONL batches to the FastAPI API over HTTP. This decoupling means we can scale API replicas behind a load balancer without touching the edge GPU nodes.

### 6.2 Model Selection (YOLOv8 Nano)

**Prompt**: "Compare YOLOv8, Detectron2, EfficientDet, and SSD MobileNet for real-time person detection on edge hardware with <8GB VRAM."

**AI Analysis**: AI produced a comparison matrix on FPS, mAP@0.5, VRAM usage, and deployment complexity. YOLOv8 Nano achieved 120+ FPS on RTX 3060 with 3.2M parameters — 4x faster than Detectron2 and with native TensorRT export. The AI flagged that Detectron2's Mask R-CNN head was unnecessary for our bounding-box-only use case.

**Adopted**: Yes. We use `yolov8n.pt` with confidence threshold 0.4 and NMS IoU 0.45.

### 6.3 Tracking Strategy (ByteTrack over DeepSORT)

**Prompt**: "What is the best multi-object tracker for crowded retail environments with frequent occlusions? Must maintain >15 FPS."

**AI Recommendation**: ByteTrack, because it uniquely uses low-confidence detection boxes for association via IoU, maintaining track continuity through occlusions without requiring a per-frame ReID embedding (which DeepSORT demands). The AI quantified the FPS impact: DeepSORT at ~8 FPS vs. ByteTrack at ~25 FPS on the same hardware, with comparable MOTA scores.

**Adopted**: Yes. ByteTrack is used for intra-camera tracking (`cv/tracker.py`), while the heavier OSNet ReID model is invoked only for cross-camera identity stitching — a deliberate two-tier strategy suggested by the AI.

### 6.4 Staff Detection Heuristic

**Prompt**: "Should we train a separate classifier for staff vs. visitor detection, or use heuristic rules?"

**AI Analysis**: AI recommended **logical heuristics** over a trained classifier for two reasons: (a) no labeled training data for staff exists, and (b) staff exhibit strong behavioural signals — presence for >4 hours, frequent visits to restricted billing zones (>5 visits). Training a classifier would require data collection and annotation effort disproportionate to the accuracy gain. AI suggested a `StaffDetector` class with configurable `presence_ratio` and `billing_visit_threshold` parameters.

**Adopted**: Yes. Implemented in `cv/reid.py::StaffDetector` with `STAFF_PRESENCE_RATIO=0.6` and `STAFF_BILLING_VISITS=5`. All downstream metrics (`compute_metrics`, `compute_funnel`) filter `WHERE is_staff = False`.

### 6.5 Event Schema Normalisation

**Prompt**: "The input data has 3 different event formats (entry/exit with id_token, zone events with track_id, queue events with queue_event_id). How should we normalise these?"

**AI Recommendation**: Define a single canonical `Event` schema with a UUID `event_id`, standardised `event_type` enum, and a flexible `metadata` JSONB column for format-specific fields. The AI stressed the importance of a unified schema for clean aggregation queries and suggested mapping `id_token` and `track_id` to a normalised `visitor_id` during ingestion.

**Adopted**: Yes. The `EventCreate` Pydantic schema and `Event` SQLAlchemy model use a single flat structure. The `ingest_dataset.py` and `generate_events.py` scripts handle the heterogeneous-to-canonical transformation.

### 6.6 API Design Patterns

**Prompt**: "What FastAPI patterns are best for high-throughput event ingestion with batch processing?"

**AI Recommendations** (all adopted):
- **Batch ingestion endpoint** with a 500-event cap to reduce HTTP overhead while preventing memory exhaustion.
- **Idempotent deduplication**: Pre-check `event_id` existence with `SELECT event_id WHERE event_id IN (...)` before inserting, making retries safe.
- **`dependency_overrides`** for testing: Override `get_db` with an in-memory `aiosqlite` session, enabling full integration tests without a PostgreSQL instance.
- **Versioned API prefix** (`/api/v1/`) to allow non-breaking schema evolution.

### 6.7 Test Strategy

**Prompt**: "How do we write async integration tests for a FastAPI app with PostgreSQL without needing a real database?"

**AI Recommendation**: Use `aiosqlite` as an in-memory async SQLAlchemy backend with `dependency_overrides[get_db]`. Each test gets a fresh database via `create_all` / `drop_all` in an `autouse` fixture. The AI also recommended `httpx.AsyncClient` with `ASGITransport` over `TestClient` for true async test execution.

**Adopted**: Yes. See `tests/conftest.py` — this pattern enables the entire test suite to run in ~2 seconds with zero external dependencies.

### 6.8 Timezone and Edge-Case Handling

**Prompt**: "The sample data has timestamps without timezone info. How should we handle this across ingestion, session building, and anomaly detection?"

**AI Analysis**: AI identified a subtle bug pattern where naive timestamps from the CV pipeline would cause `TypeError` when compared with `datetime.now(timezone.utc)`. The recommendation was to normalise to UTC at the API boundary (Pydantic parses ISO strings with optional `Z` suffix) and treat all stored timestamps as UTC-naive internally for SQLite test compatibility, using explicit `replace(tzinfo=timezone.utc)` only when computing time deltas.

**Adopted**: Yes. See `sessions.py::build_sessions` lines 164-172 where timezone-aware arithmetic is handled defensively.

### 6.9 Re-entry Detection Logic

**Prompt**: "How should we distinguish a genuine re-entry from a first-time entry? The CV pipeline may fire ENTRY events for the same person after they exit."

**AI Recommendation**: Use a time-window heuristic: if the same `visitor_id` enters within 30 minutes of their last EXIT event, emit a `REENTRY` event type instead of `ENTRY`. Track exit timestamps in a dictionary keyed by visitor_id. The AI noted this avoids double-counting in footfall metrics while preserving the ability to analyse return behaviour.

**Adopted**: Yes. Implemented in `cv/event_generator.py` and demonstrated in `generate_events.py` (ID_60001 exits at 18:12 and re-enters at 18:25).

## 7. Performance Considerations

Performance optimization strategies include:
- **Batch Ingestion**: Network overhead is minimized by batching up to 500 events per POST request, combined with `executemany` async bulk inserts in SQLAlchemy.
- **Connection Pooling**: `asyncpg` combined with SQLAlchemy connection pooling prevents connection exhaustion under heavy Edge-node request load.
- **Frame Skipping**: The CV pipeline processes video at 15 FPS rather than the native 30/60 FPS. This halves GPU usage with negligible impact on tracking accuracy for slow-moving retail pedestrians.
- **Embedding Caching**: ReID OSNet embeddings are aggressively cached locally in FAISS to speed up cross-camera matching without re-computing tensors.

