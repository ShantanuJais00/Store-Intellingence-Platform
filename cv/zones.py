from shapely.geometry import Polygon, Point
from dataclasses import dataclass
from cv.tracker import Track

@dataclass
class ZoneEvent:
    event_type: str  # ZONE_ENTER, ZONE_EXIT, ZONE_DWELL
    track_id: int
    zone_id: str
    timestamp_ms: int
    dwell_ms: int = 0

class ZoneManager:
    def __init__(self, zone_config: dict[str, list[tuple[float, float]]]):
        self.polygons = {}
        for zone_id, points in zone_config.items():
            if len(points) >= 3:
                self.polygons[zone_id] = Polygon(points)
                
        # Per track state
        self.track_zone: dict[int, str] = {}
        self.track_enter_time: dict[int, int] = {}
        self.track_last_dwell: dict[int, int] = {}
        
        self.dwell_interval_ms = 30000

    def get_zone(self, x: float, y: float) -> str | None:
        p = Point(x, y)
        for zone_id, poly in self.polygons.items():
            if poly.contains(p):
                return zone_id
        return None

    def update_tracks(self, tracks: list[Track], frame_time_ms: int) -> list[ZoneEvent]:
        events = []
        
        current_active_tracks = set()
        
        for track in tracks:
            current_active_tracks.add(track.track_id)
            
            # Bottom center
            x1, y1, x2, y2 = track.bbox
            bx = (x1 + x2) / 2.0
            by = y2
            
            new_zone = self.get_zone(bx, by)
            old_zone = self.track_zone.get(track.track_id)
            
            if new_zone != old_zone:
                # Left old zone
                if old_zone is not None:
                    events.append(ZoneEvent(
                        event_type='ZONE_EXIT',
                        track_id=track.track_id,
                        zone_id=old_zone,
                        timestamp_ms=frame_time_ms,
                        dwell_ms=frame_time_ms - self.track_enter_time.get(track.track_id, frame_time_ms)
                    ))
                    
                # Entered new zone
                if new_zone is not None:
                    events.append(ZoneEvent(
                        event_type='ZONE_ENTER',
                        track_id=track.track_id,
                        zone_id=new_zone,
                        timestamp_ms=frame_time_ms,
                        dwell_ms=0
                    ))
                    self.track_enter_time[track.track_id] = frame_time_ms
                    self.track_last_dwell[track.track_id] = frame_time_ms
                    
                self.track_zone[track.track_id] = new_zone
                
            else:
                # Same zone, check dwell
                if new_zone is not None:
                    last_dwell = self.track_last_dwell.get(track.track_id, self.track_enter_time.get(track.track_id, frame_time_ms))
                    if frame_time_ms - last_dwell >= self.dwell_interval_ms:
                        events.append(ZoneEvent(
                            event_type='ZONE_DWELL',
                            track_id=track.track_id,
                            zone_id=new_zone,
                            timestamp_ms=frame_time_ms,
                            dwell_ms=frame_time_ms - self.track_enter_time.get(track.track_id, frame_time_ms)
                        ))
                        self.track_last_dwell[track.track_id] = frame_time_ms

        # Handle tracks that are lost
        for tid in list(self.track_zone.keys()):
            if tid not in current_active_tracks:
                old_zone = self.track_zone[tid]
                if old_zone is not None:
                    events.append(ZoneEvent(
                        event_type='ZONE_EXIT',
                        track_id=tid,
                        zone_id=old_zone,
                        timestamp_ms=frame_time_ms,
                        dwell_ms=frame_time_ms - self.track_enter_time.get(tid, frame_time_ms)
                    ))
                del self.track_zone[tid]
                if tid in self.track_enter_time:
                    del self.track_enter_time[tid]
                if tid in self.track_last_dwell:
                    del self.track_last_dwell[tid]

        return events
