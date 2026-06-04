import argparse
import cv2
import os
import json
from datetime import datetime, timedelta

from cv.config import MODEL_CONFIG, STORE_1_ZONES, STORE_2_ZONES, CAMERA_CONFIGS
from cv.detect import PersonDetector
from cv.tracker import ByteTracker
from cv.reid import ReIDExtractor, StaffDetector
from cv.zones import ZoneManager
from cv.event_generator import EventGenerator, VirtualLineCrossing, BillingTracker

def process_video(video_path, store_id, camera_id, camera_type, output_dir, zone_config_dict, skip_frames, entry_line=None):
    os.makedirs(output_dir, exist_ok=True)
    out_file = os.path.join(output_dir, f"{store_id}_{camera_id}_events.jsonl")
    
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Error: Could not open video {video_path}")
        return

    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        fps = 30.0

    # Components
    detector = PersonDetector(
        model_path=MODEL_CONFIG['YOLO_MODEL'],
        confidence=MODEL_CONFIG['YOLO_CONFIDENCE'],
        iou_threshold=MODEL_CONFIG['YOLO_IOU']
    )
    tracker = ByteTracker(track_buffer=int(fps))
    reid = ReIDExtractor(threshold=MODEL_CONFIG['REID_THRESHOLD'])
    staff_detector = StaffDetector(
        presence_ratio=MODEL_CONFIG['STAFF_PRESENCE_RATIO'],
        billing_visit_threshold=MODEL_CONFIG['STAFF_BILLING_VISITS']
    )
    zone_mgr = ZoneManager(zone_config_dict)
    event_gen = EventGenerator(store_id, camera_id)
    billing_tracker = BillingTracker(abandon_timeout_s=MODEL_CONFIG['QUEUE_ABANDON_TIMEOUT_S'])
    
    line_crossing = None
    if camera_type == 'entry' and entry_line:
        line_crossing = VirtualLineCrossing(tuple(entry_line[0]), tuple(entry_line[1]))

    # State
    frame_idx = 0
    start_time = datetime.utcnow()
    total_frames_processed = 0
    
    # Store track center history for line crossing
    track_history = {} # track_id -> last_center
    
    print(f"Processing {video_path}...")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        frame_idx += 1
        if frame_idx % skip_frames != 0:
            continue
            
        total_frames_processed += 1
        current_time = start_time + timedelta(seconds=frame_idx/fps)
        current_time_iso = current_time.isoformat() + "Z"
        current_time_ms = int((frame_idx/fps) * 1000)

        # 1. Detect
        detections = detector.detect(frame)
        
        # 2. Track
        tracks = tracker.update(detections, frame_idx)
        
        # 3. Process Tracks
        current_active_tracks = set()
        for track in tracks:
            tid = track.track_id
            current_active_tracks.add(tid)
            
            # ReID every 10 frames
            visitor_id = reid.get_visitor_id(tid)
            if visitor_id is None or frame_idx % 10 == 0:
                emb = reid.extract_embedding(frame, track.bbox)
                matched_id, is_reentry = reid.match_or_register(emb, tid)
                visitor_id = matched_id
                
                if is_reentry and not reid.get_visitor_id(tid): # Only fire once
                    event_gen.generate_reentry_event(visitor_id, current_time_iso, track.confidence)

            # Center point
            x1, y1, x2, y2 = track.bbox
            center = ((x1 + x2) / 2.0, y2) # Bottom center
            
            # Line Crossing
            if line_crossing:
                prev_center = track_history.get(tid)
                cross_type = line_crossing.check_crossing(prev_center, center)
                if cross_type == 'ENTRY':
                    event_gen.generate_entry_event(visitor_id, current_time_iso, track.confidence)
                elif cross_type == 'EXIT':
                    event_gen.generate_exit_event(visitor_id, current_time_iso, track.confidence)
                    
            track_history[tid] = center

        # Update Zones
        zone_events = zone_mgr.update_tracks(tracks, current_time_ms)
        
        # Process Zone Events
        for ze in zone_events:
            tid = ze.track_id
            vid = reid.get_visitor_id(tid)
            if not vid: continue
            
            conf = 1.0 # Approximate since we don't store it in ze
            is_staff = staff_detector.is_staff(vid, total_frames_processed)
            
            # Update staff detector stats
            staff_detector.update(vid, frame_idx, total_frames_processed, ze.zone_id)
            
            event_gen.generate_zone_event_full(
                ze.event_type, vid, current_time_iso, ze.zone_id, ze.dwell_ms, conf, is_staff
            )
            
            # Billing logic
            if camera_type == 'billing' or ze.zone_id in ('BILLING', 'CASH_COUNTER'):
                if ze.event_type == 'ZONE_ENTER':
                    queue_depth = len([t for t in tracks if zone_mgr.get_zone((t.bbox[0]+t.bbox[2])/2, t.bbox[3]) in ('BILLING', 'CASH_COUNTER')])
                    event_gen.generate_billing_join(vid, current_time_iso, queue_depth, conf)
                    billing_tracker.visitor_joined(vid, current_time_iso)
                elif ze.event_type == 'ZONE_EXIT':
                    is_abandon = billing_tracker.visitor_left(vid, current_time_iso)
                    if is_abandon:
                        event_gen.generate_billing_abandon(vid, current_time_iso, conf)

        # Cleanup track history
        for tid in list(track_history.keys()):
            if tid not in current_active_tracks and tid not in [t.track_id for t in tracker.tracks]: # including lost
                del track_history[tid]

    cap.release()
    
    # 5. Write to JSONL
    event_gen.write_jsonl(out_file)
    print(f"Finished processing. Generated {len(event_gen.events)} events.")
    print(f"Output saved to {out_file}")

def main():
    parser = argparse.ArgumentParser(description='Store Intelligence CV Pipeline')
    parser.add_argument('--video', required=True, help='Path to video file')
    parser.add_argument('--store-id', required=True, help='Store identifier')
    parser.add_argument('--camera-id', required=True, help='Camera identifier')
    parser.add_argument('--camera-type', choices=['entry', 'zone', 'billing'], required=True)
    parser.add_argument('--output-dir', default='./output', help='Output directory for JSONL')
    parser.add_argument('--zone-config', help='Path to zone config JSON (overrides default)')
    parser.add_argument('--skip-frames', type=int, default=2, help='Process every Nth frame')
    args = parser.parse_args()

    # Load zone config
    if args.zone_config:
        with open(args.zone_config, 'r') as f:
            zone_config_dict = json.load(f)
    else:
        if args.store_id == 'STORE_001':
            zone_config_dict = STORE_1_ZONES
        elif args.store_id == 'STORE_002':
            zone_config_dict = STORE_2_ZONES
        else:
            zone_config_dict = {}

    cam_key = f"{args.store_id}_{args.camera_id}"
    cam_config = CAMERA_CONFIGS.get(cam_key, {})
    entry_line = cam_config.get('entry_line')

    process_video(
        video_path=args.video,
        store_id=args.store_id,
        camera_id=args.camera_id,
        camera_type=args.camera_type,
        output_dir=args.output_dir,
        zone_config_dict=zone_config_dict,
        skip_frames=args.skip_frames,
        entry_line=entry_line
    )

if __name__ == '__main__':
    main()
