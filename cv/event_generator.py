import uuid
import json
from datetime import datetime
from cv.zones import ZoneEvent

class EventGenerator:
    def __init__(self, store_id: str, camera_id: str):
        self.store_id = store_id
        self.camera_id = camera_id
        self.events = []
        self._seq_counter = {}  # visitor_id -> seq

    def _get_seq(self, visitor_id: str) -> int:
        seq = self._seq_counter.get(visitor_id, 0) + 1
        self._seq_counter[visitor_id] = seq
        return seq

    def _make_event(self, event_type, visitor_id, timestamp_iso, **kwargs) -> dict:
        metadata = kwargs.get('metadata', {})
        metadata['session_seq'] = self._get_seq(visitor_id)
        
        event = {
            "event_id": str(uuid.uuid4()),
            "store_id": self.store_id,
            "camera_id": self.camera_id,
            "visitor_id": visitor_id,
            "event_type": event_type,
            "timestamp": timestamp_iso,
            "zone_id": kwargs.get('zone_id'),
            "dwell_ms": kwargs.get('dwell_ms', 0),
            "is_staff": kwargs.get('is_staff', False),
            "confidence": kwargs.get('confidence', 1.0),
            "metadata": metadata
        }
        self.events.append(event)
        return event

    def generate_entry_event(self, visitor_id, timestamp, confidence, is_staff=False) -> dict:
        return self._make_event('ENTRY', visitor_id, timestamp, confidence=confidence, is_staff=is_staff)

    def generate_exit_event(self, visitor_id, timestamp, confidence, is_staff=False) -> dict:
        return self._make_event('EXIT', visitor_id, timestamp, confidence=confidence, is_staff=is_staff)

    def generate_reentry_event(self, visitor_id, timestamp, confidence) -> dict:
        return self._make_event('REENTRY', visitor_id, timestamp, confidence=confidence)

    def generate_zone_event(self, zone_event: ZoneEvent, visitor_id, confidence, is_staff) -> dict:
        # Convert timestamp_ms to ISO format if needed, but we expect an ISO string passed as timestamp
        # So we expect caller to pass a preformatted iso string
        pass # Not used directly in this signature, handled below

    def generate_zone_event_full(self, event_type, visitor_id, timestamp, zone_id, dwell_ms, confidence, is_staff) -> dict:
        return self._make_event(
            event_type, 
            visitor_id, 
            timestamp, 
            zone_id=zone_id, 
            dwell_ms=dwell_ms, 
            confidence=confidence, 
            is_staff=is_staff
        )

    def generate_billing_join(self, visitor_id, timestamp, queue_depth, confidence) -> dict:
        return self._make_event(
            'BILLING_QUEUE_JOIN', 
            visitor_id, 
            timestamp, 
            confidence=confidence,
            metadata={"queue_depth": queue_depth}
        )

    def generate_billing_abandon(self, visitor_id, timestamp, confidence) -> dict:
        return self._make_event(
            'BILLING_QUEUE_ABANDON', 
            visitor_id, 
            timestamp, 
            confidence=confidence
        )

    def write_jsonl(self, output_path: str):
        with open(output_path, 'w') as f:
            for ev in self.events:
                f.write(json.dumps(ev) + '\n')


def ccw(A, B, C):
    return (C[1]-A[1]) * (B[0]-A[0]) > (B[1]-A[1]) * (C[0]-A[0])

def intersect(A, B, C, D):
    return ccw(A, C, D) != ccw(B, C, D) and ccw(A, B, C) != ccw(A, B, D)

class VirtualLineCrossing:
    def __init__(self, line_start: tuple, line_end: tuple):
        self.line_start = line_start
        self.line_end = line_end

    def check_crossing(self, prev_pos: tuple, curr_pos: tuple) -> str | None:
        if not prev_pos or not curr_pos:
            return None
            
        if intersect(self.line_start, self.line_end, prev_pos, curr_pos):
            # Determine direction using cross product
            # Line vector
            lx = self.line_end[0] - self.line_start[0]
            ly = self.line_end[1] - self.line_start[1]
            # Movement vector
            mx = curr_pos[0] - prev_pos[0]
            my = curr_pos[1] - prev_pos[1]
            
            cross = lx * my - ly * mx
            if cross > 0:
                return 'ENTRY'
            else:
                return 'EXIT'
        return None


class BillingTracker:
    def __init__(self, abandon_timeout_s=300):
        self.abandon_timeout_s = abandon_timeout_s
        self.joined_at = {}

    def visitor_joined(self, visitor_id, timestamp_iso):
        self.joined_at[visitor_id] = datetime.fromisoformat(timestamp_iso)

    def visitor_left(self, visitor_id, timestamp_iso) -> bool:
        if visitor_id in self.joined_at:
            del self.joined_at[visitor_id]
            # In a real system, we cross-reference with POS transactions
            # For now, if they leave we assume abandon unless POS says otherwise
            return True
        return False

    def check_abandoned(self, current_time_iso, pos_transactions) -> list[str]:
        # pos_transactions could be a list of visitor_ids that bought something
        abandoned = []
        curr = datetime.fromisoformat(current_time_iso)
        
        for vid, join_time in list(self.joined_at.items()):
            elapsed = (curr - join_time).total_seconds()
            if elapsed > self.abandon_timeout_s:
                if vid not in pos_transactions:
                    abandoned.append(vid)
                del self.joined_at[vid]
                
        return abandoned
