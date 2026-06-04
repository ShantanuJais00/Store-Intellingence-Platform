from dataclasses import dataclass
import numpy as np
from scipy.optimize import linear_sum_assignment
from cv.detect import Detection

@dataclass
class Track:
    track_id: int
    bbox: list[float]
    confidence: float
    state: str  # 'tentative', 'confirmed', 'lost', 'removed'
    age: int
    hits: int

def get_iou(bb1, bb2):
    # bb = [x1, y1, x2, y2]
    x_left = max(bb1[0], bb2[0])
    y_top = max(bb1[1], bb2[1])
    x_right = min(bb1[2], bb2[2])
    y_bottom = min(bb1[3], bb2[3])

    if x_right < x_left or y_bottom < y_top:
        return 0.0

    intersection_area = (x_right - x_left) * (y_bottom - y_top)
    bb1_area = (bb1[2] - bb1[0]) * (bb1[3] - bb1[1])
    bb2_area = (bb2[2] - bb2[0]) * (bb2[3] - bb2[1])
    iou = intersection_area / float(bb1_area + bb2_area - intersection_area)
    return iou

class ByteTracker:
    def __init__(self, track_buffer=30, match_threshold=0.8, high_thresh=0.6, low_thresh=0.1):
        self.track_buffer = track_buffer
        self.match_threshold = match_threshold
        self.high_thresh = high_thresh
        self.low_thresh = low_thresh
        
        self.tracks: list[Track] = []
        self.next_id = 1
        
        self.lost_tracks: list[Track] = []

    def update(self, detections: list[Detection], frame_id: int) -> list[Track]:
        # 1. Split detections
        high_dets = [d for d in detections if d.confidence >= self.high_thresh]
        low_dets = [d for d in detections if self.low_thresh <= d.confidence < self.high_thresh]

        # Combine active and lost tracks for matching
        active_tracks = [t for t in self.tracks if t.state in ('tentative', 'confirmed')]
        
        # 2. Match high-confidence detections
        matched_track_indices, matched_det_indices, unmatched_track_indices, unmatched_det_indices = \
            self._match(active_tracks + self.lost_tracks, high_dets)

        # Update matched tracks
        all_tracks = active_tracks + self.lost_tracks
        for t_idx, d_idx in zip(matched_track_indices, matched_det_indices):
            t = all_tracks[t_idx]
            d = high_dets[d_idx]
            t.bbox = d.bbox
            t.confidence = d.confidence
            t.hits += 1
            t.age = 0
            if t.state == 'tentative' and t.hits >= 3:
                t.state = 'confirmed'
            elif t.state == 'lost':
                t.state = 'confirmed'

        # 3. Match remaining tracks to low-confidence detections
        unmatched_tracks = [all_tracks[i] for i in unmatched_track_indices if all_tracks[i].state == 'confirmed']
        matched_track_indices_low, matched_det_indices_low, unmatched_track_indices_low, unmatched_det_indices_low = \
            self._match(unmatched_tracks, low_dets)

        for t_idx, d_idx in zip(matched_track_indices_low, matched_det_indices_low):
            t = unmatched_tracks[t_idx]
            d = low_dets[d_idx]
            t.bbox = d.bbox
            t.confidence = d.confidence
            t.hits += 1
            t.age = 0
            # remains confirmed

        # Update age of unmatched tracks
        new_lost = []
        for i in unmatched_track_indices_low:
            t = unmatched_tracks[i]
            t.age += 1
            t.state = 'lost'
            new_lost.append(t)
            
        for i in unmatched_track_indices:
            t = all_tracks[i]
            if t not in unmatched_tracks: # was tentative or already lost
                t.age += 1
                if t.state == 'tentative':
                    t.state = 'removed'
                elif t.state == 'lost':
                    if t.age > self.track_buffer:
                        t.state = 'removed'

        # 4. Create new tracks for unmatched high-confidence detections
        for d_idx in unmatched_det_indices:
            d = high_dets[d_idx]
            self.tracks.append(Track(
                track_id=self.next_id,
                bbox=d.bbox,
                confidence=d.confidence,
                state='tentative',
                age=0,
                hits=1
            ))
            self.next_id += 1

        # Collect tracks
        active_tracks = []
        self.lost_tracks = []
        
        for t in self.tracks:
            if t.state == 'removed':
                continue
            if t.state in ('tentative', 'confirmed'):
                active_tracks.append(t)
            elif t.state == 'lost':
                if t.age > self.track_buffer:
                    t.state = 'removed'
                else:
                    self.lost_tracks.append(t)
                    
        # Update self.tracks to only contain alive ones
        self.tracks = active_tracks + self.lost_tracks
        
        return [t for t in self.tracks if t.state == 'confirmed']

    def _match(self, tracks, detections):
        if not tracks or not detections:
            return [], [], list(range(len(tracks))), list(range(len(detections)))

        cost_matrix = np.zeros((len(tracks), len(detections)))
        for i, t in enumerate(tracks):
            for j, d in enumerate(detections):
                iou = get_iou(t.bbox, d.bbox)
                cost_matrix[i, j] = 1.0 - iou

        row_indices, col_indices = linear_sum_assignment(cost_matrix)

        matched_tracks = []
        matched_dets = []
        unmatched_tracks = list(range(len(tracks)))
        unmatched_dets = list(range(len(detections)))

        for r, c in zip(row_indices, col_indices):
            if cost_matrix[r, c] <= (1.0 - (1.0 - self.match_threshold)): 
                # This check actually means IOU >= threshold.
                # Oh wait, match_threshold in ByteTrack is max cost (e.g. 0.8),
                # meaning min IOU is 0.2.
                # If we want max cost to be match_threshold:
                if cost_matrix[r, c] <= self.match_threshold:
                    matched_tracks.append(r)
                    matched_dets.append(c)
                    unmatched_tracks.remove(r)
                    unmatched_dets.remove(c)

        return matched_tracks, matched_dets, unmatched_tracks, unmatched_dets
