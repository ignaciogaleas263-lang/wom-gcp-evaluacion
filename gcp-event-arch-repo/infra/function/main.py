
import base64, json, os, datetime
from google.cloud import bigquery

PROJECT_ID         = os.getenv("PROJECT_ID")
DATASET_ID         = os.getenv("DATASET_ID", "wom_data")
RAW_TABLE_ID       = os.getenv("RAW_TABLE_ID", "files_raw")
PROCESSED_TABLE_ID = os.getenv("PROCESSED_TABLE_ID", "files_processed")
bq = bigquery.Client(project=PROJECT_ID)

def _insert_raw_row(bucket, name, size, ts):
    table_id = f"{PROJECT_ID}.{DATASET_ID}.{RAW_TABLE_ID}"
    rows_to_insert = [{"bucket": bucket, "name": name, "size": int(size) if size else None, "time": ts}]
    errors = bq.insert_rows_json(table_id, rows_to_insert)
    if errors: raise RuntimeError(f"BigQuery insert errors: {errors}")

def _insert_processed_row(name, size):
    table_id = f"{PROJECT_ID}.{DATASET_ID}.{PROCESSED_TABLE_ID}"
    rows_to_insert = [{"name": name, "size": int(size) if size else None, "ingested_at": datetime.datetime.utcnow().isoformat()}]
    errors = bq.insert_rows_json(table_id, rows_to_insert)
    if errors: raise RuntimeError(f"BigQuery insert errors: {errors}")

def handle_gcs_event(event, context=None):
    try:
        data_b64 = event.get("data")
        if not data_b64:
            print("No data in Pub/Sub message"); return
        payload = json.loads(base64.b64decode(data_b64).decode("utf-8"))
        name = payload.get("name"); bucket = payload.get("bucket"); size = payload.get("size")
        time_created = payload.get("timeCreated") or datetime.datetime.utcnow().isoformat()
        print(f"[WOM] Received object: gs://{bucket}/{name} size={size} time={time_created}")
        _insert_raw_row(bucket=bucket, name=name, size=size, ts=time_created)
        _insert_processed_row(name=name, size=size)
        print("[WOM] OK: Rows inserted into BigQuery")
    except Exception as e:
        print(f"[WOM][ERROR] {e}"); raise
