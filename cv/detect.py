from dataclasses import dataclass
import numpy as np
from ultralytics import YOLO
import cv2

@dataclass
class Detection:
    bbox: list[float]  # [x1, y1, x2, y2]
    confidence: float
    class_id: int = 0

class PersonDetector:
    def __init__(self, model_path='yolov8n.pt', confidence=0.4, iou_threshold=0.45):
        self.model = YOLO(model_path)
        self.confidence = confidence
        self.iou_threshold = iou_threshold

    def detect(self, frame: np.ndarray) -> list[Detection]:
        results = self.model(
            frame, 
            conf=self.confidence, 
            iou=self.iou_threshold,
            classes=[0],  # 0 is person class in COCO
            verbose=False
        )
        
        detections = []
        if len(results) > 0:
            result = results[0]
            boxes = result.boxes
            for box in boxes:
                # box.xyxy format: [x1, y1, x2, y2]
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                conf = float(box.conf[0].cpu().numpy())
                cls_id = int(box.cls[0].cpu().numpy())
                
                if cls_id == 0:
                    detections.append(Detection(
                        bbox=[float(x1), float(y1), float(x2), float(y2)],
                        confidence=conf,
                        class_id=cls_id
                    ))
                    
        return detections
