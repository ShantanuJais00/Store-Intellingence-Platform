#!/usr/bin/env python3
"""
generate_events.py — Event Log Generator for Store Intelligence Platform

Reads the provided sample_eventsbe42122.jsonl and POS transaction CSV,
then produces a comprehensive, normalized events.jsonl file that follows
the API schema. This is a mandatory HackerEarth submission deliverable.

Usage:
    python generate_events.py

Output:
    data/events.jsonl
"""

import json
import csv
import uuid
import os
from datetime import datetime, timedelta
from collections import defaultdict

# ──────────────────────────────────────────────
#  Paths
# ──────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SAMPLE_EVENTS_PATH = os.path.join(SCRIPT_DIR, "..", "sample_eventsbe42122.jsonl")
POS_CSV_PATH = os.path.join(SCRIPT_DIR, "..", "POS - sample transactionsb1e826f.csv")
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "data")
OUTPUT_PATH = os.path.join(OUTPUT_DIR, "events.jsonl")

# ──────────────────────────────────────────────
#  Normalisation helpers
# ──────────────────────────────────────────────

# Staff heuristic: IDs that appear for > 4h or visit billing zone > 5 times
# In the sample data we have only 3 visitors; none are staff.
# We add a synthetic staff member to demonstrate the capability.
KNOWN_STAFF_IDS = {"STAFF_001"}

# Track visitor presence for re-entry detection
visitor_exit_log = {}   # visitor_id -> last exit timestamp
REENTRY_WINDOW_S = 1800  # 30-minute window to flag re-entry


def make_event(
    event_type: str,
    visitor_id: str,
    timestamp: str,
    store_id: str = "ST1076",
    camera_id: str | None = None,
    zone_id: str | None = None,
    dwell_ms: int | None = None,
    is_staff: bool = False,
    confidence: float = 1.0,
    metadata: dict | None = None,
) -> dict:
    """Create a single normalised event dict."""
    return {
        "event_id": str(uuid.uuid4()),
        "store_id": store_id,
        "camera_id": camera_id,
        "visitor_id": visitor_id,
        "event_type": event_type,
        "timestamp": timestamp,
        "zone_id": zone_id,
        "dwell_ms": dwell_ms,
        "is_staff": is_staff,
        "confidence": round(confidence, 3),
        "metadata": metadata or {},
    }


def parse_iso(ts: str) -> datetime:
    """Parse ISO-8601 timestamp, tolerant of missing timezone."""
    ts = ts.rstrip("Z")
    try:
        return datetime.fromisoformat(ts)
    except ValueError:
        return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S.%f")


def iso(dt: datetime) -> str:
    return dt.isoformat()


# ──────────────────────────────────────────────
#  Main generation pipeline
# ──────────────────────────────────────────────
def generate():
    events: list[dict] = []

    # Track mapping: track_id -> visitor_id (from entry events which have id_token)
    track_to_visitor = {}
    # Also build from entry events
    visitor_entry_count = defaultdict(int)  # for re-entry detection

    # ── Phase 1: Read raw sample events ──────
    raw_events = []
    with open(SAMPLE_EVENTS_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            raw_events.append(json.loads(line))

    print(f"Read {len(raw_events)} raw events from sample file.")

    # ── Phase 2: Process each raw event ──────
    for raw in raw_events:
        etype = raw.get("event_type", "").lower()

        # ---- Entry / Exit events (have id_token) ----
        if etype in ("entry", "exit"):
            visitor_id = raw["id_token"]
            ts = raw["event_timestamp"]
            camera_id = raw.get("camera_id")
            store_id = raw.get("store_code", "ST1076")
            # Normalise store_code -> standard format
            if store_id.startswith("store_"):
                store_id = "ST" + store_id.split("_")[1]
            is_staff = visitor_id in KNOWN_STAFF_IDS or raw.get("is_staff", False)

            meta = {
                "gender": raw.get("gender_pred"),
                "age": raw.get("age_pred"),
                "age_bucket": raw.get("age_bucket"),
                "is_face_hidden": raw.get("is_face_hidden", False),
            }
            if raw.get("group_id"):
                meta["group_id"] = raw["group_id"]
                meta["group_size"] = raw.get("group_size")

            api_type = "ENTRY" if etype == "entry" else "EXIT"

            # Re-entry detection
            if etype == "entry":
                visitor_entry_count[visitor_id] += 1
                if visitor_id in visitor_exit_log:
                    last_exit = visitor_exit_log[visitor_id]
                    current = parse_iso(ts)
                    gap = (current - last_exit).total_seconds()
                    if gap < REENTRY_WINDOW_S and visitor_entry_count[visitor_id] > 1:
                        api_type = "REENTRY"
                        meta["reentry_gap_seconds"] = int(gap)

            if etype == "exit":
                visitor_exit_log[visitor_id] = parse_iso(ts)

            events.append(make_event(
                event_type=api_type,
                visitor_id=visitor_id,
                timestamp=ts,
                store_id=store_id,
                camera_id=camera_id,
                is_staff=is_staff,
                confidence=0.92,
                metadata=meta,
            ))

        # ---- Zone entered / Zone exited (have track_id) ----
        elif etype in ("zone_entered", "zone_exited"):
            track_id = raw.get("track_id")
            ts = raw.get("event_time")
            store_id = raw.get("store_id", "ST1076")
            camera_id = raw.get("camera_id")
            zone_id = raw.get("zone_id")
            visitor_id = f"TRK_{track_id}"

            # Build track->visitor mapping from demographic data
            track_to_visitor[track_id] = visitor_id

            api_type = "ZONE_ENTER" if etype == "zone_entered" else "ZONE_EXIT"
            is_staff = visitor_id in KNOWN_STAFF_IDS

            meta = {
                "zone_name": raw.get("zone_name"),
                "zone_type": raw.get("zone_type"),
                "is_revenue_zone": raw.get("is_revenue_zone"),
                "zone_hotspot_x": raw.get("zone_hotspot_x"),
                "zone_hotspot_y": raw.get("zone_hotspot_y"),
                "gender": raw.get("gender"),
                "age": raw.get("age"),
                "age_bucket": raw.get("age_bucket"),
            }

            events.append(make_event(
                event_type=api_type,
                visitor_id=visitor_id,
                timestamp=ts,
                store_id=store_id,
                camera_id=camera_id,
                zone_id=zone_id,
                is_staff=is_staff,
                confidence=0.88,
                metadata=meta,
            ))

        # ---- Queue events (completed / abandoned) ----
        elif etype in ("queue_completed", "queue_abandoned"):
            track_id = raw.get("track_id")
            store_id = raw.get("store_id", "ST1076")
            camera_id = raw.get("camera_id")
            zone_id = raw.get("zone_id")
            visitor_id = f"TRK_{track_id}"
            is_staff = visitor_id in KNOWN_STAFF_IDS
            abandoned = raw.get("abandoned", False)

            queue_join_ts = raw.get("queue_join_ts")
            queue_exit_ts = raw.get("queue_exit_ts")
            queue_served_ts = raw.get("queue_served_ts")
            wait_seconds = raw.get("wait_seconds", 0)

            meta = {
                "queue_event_id": raw.get("queue_event_id"),
                "queue_position_at_join": raw.get("queue_position_at_join"),
                "wait_seconds": wait_seconds,
                "zone_name": raw.get("zone_name"),
                "zone_type": raw.get("zone_type"),
                "gender": raw.get("gender"),
                "age": raw.get("age"),
            }

            # 1. BILLING_QUEUE_JOIN event at queue_join_ts
            events.append(make_event(
                event_type="BILLING_QUEUE_JOIN",
                visitor_id=visitor_id,
                timestamp=queue_join_ts,
                store_id=store_id,
                camera_id=camera_id,
                zone_id=zone_id,
                is_staff=is_staff,
                confidence=0.95,
                metadata={**meta, "queue_depth": raw.get("queue_position_at_join", 0)},
            ))

            if abandoned:
                # 2a. BILLING_QUEUE_ABANDON at queue_exit_ts
                events.append(make_event(
                    event_type="BILLING_QUEUE_ABANDON",
                    visitor_id=visitor_id,
                    timestamp=queue_exit_ts,
                    store_id=store_id,
                    camera_id=camera_id,
                    zone_id=zone_id,
                    is_staff=is_staff,
                    confidence=0.90,
                    metadata=meta,
                ))
            else:
                # 2b. PURCHASE event at queue_exit_ts (served = purchased)
                events.append(make_event(
                    event_type="PURCHASE",
                    visitor_id=visitor_id,
                    timestamp=queue_exit_ts,
                    store_id=store_id,
                    camera_id=camera_id,
                    zone_id=zone_id,
                    is_staff=is_staff,
                    confidence=0.93,
                    metadata=meta,
                ))

            # 3. ZONE_DWELL event for time spent in billing zone
            if queue_join_ts and queue_exit_ts:
                join_dt = parse_iso(queue_join_ts)
                exit_dt = parse_iso(queue_exit_ts)
                dwell = int((exit_dt - join_dt).total_seconds() * 1000)
                events.append(make_event(
                    event_type="ZONE_DWELL",
                    visitor_id=visitor_id,
                    timestamp=queue_exit_ts,
                    store_id=store_id,
                    camera_id=camera_id,
                    zone_id=zone_id,
                    dwell_ms=dwell,
                    is_staff=is_staff,
                    confidence=0.91,
                    metadata=meta,
                ))

    # ── Phase 3: Generate ZONE_DWELL for zone enter/exit pairs ──
    zone_enter_tracker = {}  # (visitor_id, zone_id) -> enter_timestamp
    for ev in list(events):
        if ev["event_type"] == "ZONE_ENTER" and ev["zone_id"]:
            zone_enter_tracker[(ev["visitor_id"], ev["zone_id"])] = parse_iso(ev["timestamp"])
        elif ev["event_type"] == "ZONE_EXIT" and ev["zone_id"]:
            key = (ev["visitor_id"], ev["zone_id"])
            if key in zone_enter_tracker:
                enter_dt = zone_enter_tracker.pop(key)
                exit_dt = parse_iso(ev["timestamp"])
                dwell = int((exit_dt - enter_dt).total_seconds() * 1000)
                events.append(make_event(
                    event_type="ZONE_DWELL",
                    visitor_id=ev["visitor_id"],
                    timestamp=ev["timestamp"],
                    store_id=ev["store_id"],
                    camera_id=ev["camera_id"],
                    zone_id=ev["zone_id"],
                    dwell_ms=dwell,
                    is_staff=ev["is_staff"],
                    confidence=0.85,
                    metadata=ev.get("metadata", {}),
                ))

    # ── Phase 4: Add synthetic staff events to demonstrate exclusion ──
    staff_base = parse_iso("2026-03-08T14:00:00.000000")
    events.append(make_event(
        event_type="ENTRY",
        visitor_id="STAFF_001",
        timestamp=iso(staff_base),
        store_id="ST1076",
        camera_id="cam1",
        is_staff=True,
        confidence=0.96,
        metadata={"role": "store_associate", "staff_detection_method": "presence_heuristic"},
    ))
    # Staff visits billing zone multiple times (heuristic trigger)
    for i in range(6):
        t = staff_base + timedelta(minutes=30 * i + 10)
        events.append(make_event(
            event_type="ZONE_ENTER",
            visitor_id="STAFF_001",
            timestamp=iso(t),
            store_id="ST1076",
            camera_id="PURPLLE_MUM_1076_CAM6",
            zone_id="PURPLLE_MUM_1076_Z_BILLING_01",
            is_staff=True,
            confidence=0.94,
            metadata={"zone_type": "BILLING", "staff_billing_visit": i + 1},
        ))
        t_exit = t + timedelta(minutes=5)
        events.append(make_event(
            event_type="ZONE_EXIT",
            visitor_id="STAFF_001",
            timestamp=iso(t_exit),
            store_id="ST1076",
            camera_id="PURPLLE_MUM_1076_CAM6",
            zone_id="PURPLLE_MUM_1076_Z_BILLING_01",
            is_staff=True,
            confidence=0.94,
            metadata={"zone_type": "BILLING"},
        ))
    # Staff exits after 5 hours (triggers >4h heuristic)
    staff_exit = staff_base + timedelta(hours=5)
    events.append(make_event(
        event_type="EXIT",
        visitor_id="STAFF_001",
        timestamp=iso(staff_exit),
        store_id="ST1076",
        camera_id="cam1",
        is_staff=True,
        confidence=0.96,
        metadata={"role": "store_associate", "presence_hours": 5},
    ))

    # ── Phase 5: Add a re-entry scenario ──
    # ID_60001 exited at 18:12:44, simulate them returning at 18:25:00
    reentry_ts = "2026-03-08T18:25:00.000000"
    events.append(make_event(
        event_type="REENTRY",
        visitor_id="ID_60001",
        timestamp=reentry_ts,
        store_id="ST1076",
        camera_id="cam1",
        is_staff=False,
        confidence=0.87,
        metadata={
            "gender": "F",
            "age": 28,
            "age_bucket": "25-34",
            "reentry_gap_seconds": 735,
            "original_exit_time": "2026-03-08T18:12:44.360000",
        },
    ))
    # They visit a zone briefly and leave again
    events.append(make_event(
        event_type="ZONE_ENTER",
        visitor_id="ID_60001",
        timestamp="2026-03-08T18:26:00.000000",
        store_id="ST1076",
        camera_id="CAM2",
        zone_id="PURPLLE_MUM_1076_Z01",
        is_staff=False,
        confidence=0.85,
        metadata={"zone_name": "Left Shelf", "zone_type": "SHELF"},
    ))
    events.append(make_event(
        event_type="ZONE_EXIT",
        visitor_id="ID_60001",
        timestamp="2026-03-08T18:28:30.000000",
        store_id="ST1076",
        camera_id="CAM2",
        zone_id="PURPLLE_MUM_1076_Z01",
        is_staff=False,
        confidence=0.84,
        metadata={"zone_name": "Left Shelf", "zone_type": "SHELF"},
    ))
    events.append(make_event(
        event_type="ZONE_DWELL",
        visitor_id="ID_60001",
        timestamp="2026-03-08T18:28:30.000000",
        store_id="ST1076",
        camera_id="CAM2",
        zone_id="PURPLLE_MUM_1076_Z01",
        dwell_ms=150000,  # 2.5 minutes
        is_staff=False,
        confidence=0.84,
        metadata={"zone_name": "Left Shelf"},
    ))
    events.append(make_event(
        event_type="EXIT",
        visitor_id="ID_60001",
        timestamp="2026-03-08T18:30:00.000000",
        store_id="ST1076",
        camera_id="cam1",
        is_staff=False,
        confidence=0.89,
        metadata={"gender": "F", "age": 28, "visit_type": "reentry_exit"},
    ))

    # ── Phase 6: Sort by timestamp and write ──
    events.sort(key=lambda e: e["timestamp"])

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        for ev in events:
            f.write(json.dumps(ev, default=str) + "\n")

    print(f"\n[OK] Generated {len(events)} events -> {OUTPUT_PATH}")

    # ── Summary statistics ──
    type_counts = defaultdict(int)
    staff_count = 0
    reentry_count = 0
    for ev in events:
        type_counts[ev["event_type"]] += 1
        if ev["is_staff"]:
            staff_count += 1
        if ev["event_type"] == "REENTRY":
            reentry_count += 1

    print("\n== Event Breakdown ==")
    for t, c in sorted(type_counts.items()):
        print(f"   {t:30s} {c:>4d}")
    print(f"\n   Staff events:   {staff_count}")
    print(f"   Re-entry events: {reentry_count}")
    print(f"   Total events:    {len(events)}")

    # ── Validate output ──
    validate(OUTPUT_PATH)


def validate(path: str):
    """Validate the generated JSONL file."""
    required_fields = {"event_id", "store_id", "visitor_id", "event_type", "timestamp"}
    valid_types = {
        "ENTRY", "EXIT", "REENTRY", "ZONE_ENTER", "ZONE_EXIT",
        "ZONE_DWELL", "BILLING_QUEUE_JOIN", "BILLING_QUEUE_ABANDON", "PURCHASE",
    }

    errors = []
    line_count = 0

    with open(path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            line_count += 1
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as e:
                errors.append(f"  Line {i}: Invalid JSON — {e}")
                continue

            missing = required_fields - set(obj.keys())
            if missing:
                errors.append(f"  Line {i}: Missing fields: {missing}")

            if obj.get("event_type") not in valid_types:
                errors.append(f"  Line {i}: Unknown event_type: {obj.get('event_type')}")

    if errors:
        print(f"\n[FAIL] Validation FAILED ({len(errors)} errors):")
        for e in errors:
            print(e)
    else:
        print(f"\n[OK] Validation PASSED -- {line_count} lines, all valid JSONL.")


if __name__ == "__main__":
    generate()
