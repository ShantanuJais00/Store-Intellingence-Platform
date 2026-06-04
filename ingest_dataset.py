import json
import csv
import httpx
import asyncio
from datetime import datetime
import uuid

API_URL = "http://localhost:8000"

# Mapping dataset event types to API EventType enum
EVENT_TYPE_MAP = {
    "entry": "ENTRY",
    "exit": "EXIT",
    "zone_entered": "ZONE_ENTER",
    "zone_exited": "ZONE_EXIT",
    "zone_dwell": "ZONE_DWELL"
}

async def ingest_events(file_path):
    print(f"Reading events from {file_path}...")
    events_payload = []
    
    with open(file_path, 'r') as f:
        for line in f:
            if not line.strip(): continue
            data = json.loads(line)
            
            # Map dataset schema to our API schema
            event_type_raw = data.get("event_type", "").lower()
            api_event_type = EVENT_TYPE_MAP.get(event_type_raw, "ZONE_ENTER")
            
            event = {
                "event_id": str(uuid.uuid4()),
                "store_id": data.get("store_code") or data.get("store_id", "UNKNOWN"),
                "camera_id": str(data.get("camera_id"))[:20] if data.get("camera_id") else None,
                "visitor_id": data.get("id_token") or f"TRK_{data.get('track_id')}",
                "event_type": api_event_type,
                "timestamp": data.get("event_timestamp") or data.get("event_time") or datetime.utcnow().isoformat(),
                "zone_id": data.get("zone_id"),
                "is_staff": data.get("is_staff", False),
                "metadata": {
                    "gender": data.get("gender_pred") or data.get("gender"),
                    "age": data.get("age_pred") or data.get("age"),
                    "group_id": data.get("group_id")
                }
            }
            events_payload.append(event)

    print(f"Parsed {len(events_payload)} events. Sending to API...")
    
    # Send in chunks of 500 (API limit)
    async with httpx.AsyncClient() as client:
        for i in range(0, len(events_payload), 500):
            chunk = events_payload[i:i+500]
            try:
                response = await client.post(f"{API_URL}/api/v1/events/batch", json={"events": chunk})
                if response.status_code == 200:
                    print(f"[SUCCESS] Ingested {len(chunk)} events successfully.")
                else:
                    print(f"[ERROR] Failed to ingest events: {response.text}")
            except Exception as e:
                print(f"[ERROR] Connection error: {e}")

async def ingest_transactions(file_path):
    print(f"\nReading transactions from {file_path}...")
    transactions_payload = []
    
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                dt_str = f"{row['order_date']} {row['order_time']}"
                dt = datetime.strptime(dt_str, "%d-%m-%Y %H:%M:%S")
            except ValueError:
                dt = datetime.utcnow()
                
            tx = {
                "order_id": row["order_id"],
                "store_id": row["store_id"],
                "timestamp": dt.isoformat(),
                "product_id": row["product_id"],
                "brand_name": row["brand_name"],
                "total_amount": float(row["total_amount"])
            }
            transactions_payload.append(tx)

    print(f"Parsed {len(transactions_payload)} transactions. Sending to API...")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(f"{API_URL}/api/v1/transactions/ingest", json=transactions_payload)
            if response.status_code == 200:
                print(f"[SUCCESS] Ingested {len(transactions_payload)} transactions successfully.")
            else:
                print(f"[ERROR] Failed to ingest transactions: {response.text}")
        except Exception as e:
            print(f"[ERROR] Connection error: {e}")

async def main():
    events_file = "../sample_eventsbe42122.jsonl"
    pos_file = "../POS - sample transactionsb1e826f.csv"
    
    await ingest_events(events_file)
    await ingest_transactions(pos_file)

if __name__ == "__main__":
    asyncio.run(main())
