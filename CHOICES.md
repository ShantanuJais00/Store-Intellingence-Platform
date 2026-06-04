# Technology Choices & Rationale

Building a real-time Store Intelligence platform requires balancing accuracy, execution speed, edge-hardware constraints, and developer velocity. Below is a detailed breakdown of the critical technology choices made during development.

### 1. Object Detection: YOLOv8
**Options Considered**: YOLOv8, YOLOv5, Detectron2, EfficientDet, SSD MobileNet  
**AI Suggestion**: YOLOv8 recommended for best speed-accuracy trade-off in real-time retail  
**Final Decision**: YOLOv8 (nano variant)  

**Rationale**: 
The object detection model is the engine of the Computer Vision pipeline. We required a model capable of real-time inference (30+ FPS) on modest edge hardware (e.g., Nvidia Jetson Orin or entry-level RTX GPUs) while handling severe occlusions typical of retail aisles. YOLOv8 (specifically `yolov8n.pt`) outperformed Detectron2 in raw FPS and offered a significantly lower memory footprint than EfficientDet. Furthermore, Ultralytics has built an incredibly robust, pythonic ecosystem around YOLOv8. It provides native PyTorch integration, out-of-the-box TensorRT export capabilities for edge deployment, and requires minimal boilerplate compared to older YOLO iterations or SSD MobileNet. The mean Average Precision (mAP) for the Nano variant is more than sufficient for large pedestrian bounding boxes, making it the undisputed winner.

### 2. Multi-Object Tracking: ByteTrack
**Options Considered**: ByteTrack, DeepSORT, SORT, FairMOT, OC-SORT  
**AI Suggestion**: ByteTrack for superior occlusion handling in crowded retail environments  
**Final Decision**: ByteTrack  

**Rationale**: 
Tracking individuals consistently across a single camera's frame is notoriously difficult in physical retail due to constant occlusions (shelves, pillars, other shoppers). Older trackers like SORT fail completely when an object is momentarily hidden. DeepSORT solves this by incorporating an appearance model (ReID) at every step, but this severely degrades FPS. ByteTrack revolutionizes this by utilizing "low confidence" detection boxes that are usually discarded by other trackers. By associating these low-score boxes via spatial IoU (Intersection over Union), ByteTrack maintains track identities through heavy occlusion without needing a computationally expensive ReID model at the tracking stage. This decision allows us to keep the tracking loop extremely fast, reserving the heavy ReID operations only for cross-camera handoffs.

### 3. Database: PostgreSQL
**Options Considered**: PostgreSQL, SQLite, TimescaleDB, MongoDB, ClickHouse  
**AI Suggestion**: PostgreSQL for relational integrity with JSON flexibility  
**Final Decision**: PostgreSQL 16  

**Rationale**: 
Retail intelligence data is inherently dual-natured. On one hand, we need strict relational integrity for store metadata, camera configurations, and defined spatial zones. On the other hand, the event stream (Entries, Exits, Dwell times) behaves like timeseries data and occasionally requires flexible schemas (e.g., an anomaly event might contain arbitrary JSON metadata). PostgreSQL 16 handles this perfectly. Its native `JSONB` column type provides NoSQL-like flexibility, while its robust ACID compliance ensures financial transaction data from POS integrations is never corrupted. While TimescaleDB or ClickHouse are superior for pure timeseries ingestion at massive scale, plain PostgreSQL is far easier to deploy, backup, and maintain for our initial target of dozens of stores. Combined with the `asyncpg` driver, it can easily handle thousands of batch inserts per second.

### 4. Web Framework: FastAPI
**Options Considered**: FastAPI, Flask, Django, Starlette, Litestar  
**AI Suggestion**: FastAPI for async-native performance and automatic OpenAPI docs  
**Final Decision**: FastAPI  

**Rationale**: 
The backend API is designed to ingest high-velocity data streams from edge devices while simultaneously serving complex analytical queries to a React dashboard. Flask and Django, being traditionally synchronous (WSGI), require heavy workarounds (like Celery or Gunicorn thread pooling) to prevent blocking operations during high I/O wait times. FastAPI is built natively on ASGI and `asyncio`, allowing a single thread to handle thousands of concurrent I/O-bound requests (such as waiting for PostgreSQL inserts). Additionally, FastAPI's deep integration with Pydantic means that every incoming event payload from the edge is automatically schema-validated with extremely informative error messages. The automatic generation of OpenAPI (Swagger) documentation drastically accelerates frontend development and third-party POS integrations.

### 5. Re-Identification: OSNet
**Options Considered**: OSNet, ResNet50-IBN, MGN, TransReID, BoT (Bag of Tricks)  
**AI Suggestion**: OSNet for lightweight yet accurate person ReID  
**Final Decision**: OSNet (`osnet_x1_0`)  

**Rationale**: 
Re-Identification (ReID) is required to understand that a person leaving Camera A's view is the same person entering Camera B's view. This is traditionally done by cropping the person's bounding box and generating a mathematical feature vector (embedding). TransReID (transformer-based) offers state-of-the-art accuracy but is entirely unsuited for real-time edge processing due to its massive parameter count. ResNet50-IBN is a solid baseline but is still quite heavy. OSNet (Omni-Scale Network) was chosen because its architecture is explicitly designed to learn features across multiple spatial scales (from global clothing color down to local features like a logo on a shirt) while remaining incredibly lightweight. The `osnet_x1_0` model runs inferences in milliseconds, allowing us to maintain high system throughput while achieving excellent Rank-1 accuracy on standard datasets like Market-1501.
