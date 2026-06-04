import numpy as np
import cv2
import uuid
import torch
import torchreid

class ReIDExtractor:
    def __init__(self, model_name='osnet_x1_0', threshold=0.7):
        self.threshold = threshold
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        
        # Load OSNet model via torchreid
        self.model = torchreid.models.build_model(
            name=model_name,
            num_classes=1000, # dummy
            loss='softmax',
            pretrained=True
        )
        self.model.eval()
        self.model.to(self.device)
        
        self.embeddings: dict[str, np.ndarray] = {}  # visitor_id -> embedding
        self.track_to_visitor: dict[int, str] = {}   # track_id -> visitor_id

    def extract_embedding(self, frame: np.ndarray, bbox: list[float]) -> np.ndarray:
        x1, y1, x2, y2 = map(int, bbox)
        
        # Keep inside frame bounds
        h, w = frame.shape[:2]
        x1 = max(0, x1)
        y1 = max(0, y1)
        x2 = min(w, x2)
        y2 = min(h, y2)
        
        if x2 <= x1 or y2 <= y1:
            return np.zeros((512,))  # OSNet usually 512d
            
        crop = frame[y1:y2, x1:x2]
        crop = cv2.resize(crop, (128, 256)) # width, height for torchreid
        crop = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
        
        # Normalize and run through model
        img = crop.astype(np.float32) / 255.0
        mean = np.array([0.485, 0.456, 0.406])
        std = np.array([0.229, 0.224, 0.225])
        img = (img - mean) / std
        
        img = np.transpose(img, (2, 0, 1)) # HWC to CHW
        img = np.expand_dims(img, axis=0)
        img_tensor = torch.from_numpy(img).to(self.device)
        
        with torch.no_grad():
            features = self.model(img_tensor)
            
        feat_np = features.cpu().numpy().flatten()
        # Normalize to unit length for cosine similarity
        norm = np.linalg.norm(feat_np)
        if norm > 0:
            feat_np = feat_np / norm
            
        return feat_np

    def match_or_register(self, embedding: np.ndarray, track_id: int) -> tuple[str, bool]:
        if track_id in self.track_to_visitor:
            # We already know this track
            # Optionally update embedding
            visitor_id = self.track_to_visitor[track_id]
            self.embeddings[visitor_id] = 0.9 * self.embeddings[visitor_id] + 0.1 * embedding
            self.embeddings[visitor_id] /= np.linalg.norm(self.embeddings[visitor_id])
            return visitor_id, False
            
        best_match = None
        best_sim = -1.0
        
        for vid, emb in self.embeddings.items():
            sim = np.dot(embedding, emb)
            if sim > best_sim:
                best_sim = sim
                best_match = vid
                
        if best_sim > self.threshold and best_match is not None:
            self.track_to_visitor[track_id] = best_match
            return best_match, True
        else:
            new_visitor_id = f"VIS_{str(uuid.uuid4())[:8].upper()}"
            self.embeddings[new_visitor_id] = embedding
            self.track_to_visitor[track_id] = new_visitor_id
            return new_visitor_id, False

    def get_visitor_id(self, track_id: int) -> str | None:
        return self.track_to_visitor.get(track_id)


class StaffDetector:
    def __init__(self, presence_ratio=0.6, billing_visit_threshold=5):
        self.presence_ratio = presence_ratio
        self.billing_visit_threshold = billing_visit_threshold
        
        # Tracking states
        self.visitor_frames: dict[str, int] = {}
        self.visitor_billing_visits: dict[str, int] = {}
        
        # To count distinct visits, we need to know the last zone
        self.visitor_last_zone: dict[str, str] = {}

    def update(self, visitor_id: str, frame_id: int, total_frames: int, zone_id: str = None):
        self.visitor_frames[visitor_id] = self.visitor_frames.get(visitor_id, 0) + 1
        
        if zone_id == 'BILLING' or zone_id == 'CASH_COUNTER':
            last_zone = self.visitor_last_zone.get(visitor_id)
            if last_zone != zone_id:
                self.visitor_billing_visits[visitor_id] = self.visitor_billing_visits.get(visitor_id, 0) + 1
                
        if zone_id:
            self.visitor_last_zone[visitor_id] = zone_id

    def is_staff(self, visitor_id: str, total_frames: int) -> bool:
        if total_frames <= 0:
            return False
            
        frames_present = self.visitor_frames.get(visitor_id, 0)
        ratio = frames_present / float(total_frames)
        if ratio > self.presence_ratio:
            return True
            
        visits = self.visitor_billing_visits.get(visitor_id, 0)
        if visits > self.billing_visit_threshold:
            return True
            
        return False
