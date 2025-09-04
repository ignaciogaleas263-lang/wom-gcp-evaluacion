# main.py
import os, json
from datetime import datetime
from google.cloud import bigquery

PROJECT_ID         = os.getenv("PROJECT_ID")
DATASET_ID         = os.getenv("DATASET_ID", "wom_data")
RAW_TABLE_ID       = os.getenv("RAW_TABLE_ID", "files_raw")
PROCESSED_TABLE_ID = os.getenv("PROCESSED_TABLE_ID", "files_processed")

_bq = None
def _bq_client():
    global _bq
    if _bq is None:
        # si PROJECT_ID no viene, BigQuery usa el proyecto por defecto del SA
        _bq = bigquery.Client(project=PROJECT_ID or None)
    return _bq

def _to_int(v):
    try:
        return int(v) if v is not None else None
    except Exception:
        return None

def _insert_raw_row(bucket, name, size, ts):
    table_id = f"{PROJECT_ID}.{DATASET_ID}.{RAW_TABLE_ID}"
    rows = [{"bucket": bucket, "name": name, "size": _to_int(size), "time": ts}]
    errors = _bq_client().insert_rows_json(table_id, rows)
    if errors:
        raise RuntimeError(f"BigQuery insert errors (RAW): {errors}")

def _insert_processed_row(name, size):
    table_id = f"{PROJECT_ID}.{DATASET_ID}.{PROCESSED_TABLE_ID}"
    rows = [{"name": name, "size": _to_int(size), "ingested_at": datetime.utcnow().isoformat()}]
    errors = _bq_client().insert_rows_json(table_id, rows)
    if errors:
        raise RuntimeError(f"BigQuery insert errors (PROCESSED): {errors}")

# Entry point (GCS finalize)
def on_gcs_finalize(event, context=None):
    try:
        name   = event.get("name")
        bucket = event.get("bucket")
        size   = event.get("size")
        ts     = event.get("timeCreated") or datetime.utcnow().isoformat()

        print(json.dumps({
            "status": "RECEIVED", "bucket": bucket, "name": name, "size": size, "timeCreated": ts
        }))

        _insert_raw_row(bucket=bucket, name=name, size=size, ts=ts)
        _insert_processed_row(name=name, size=size)

        print("[WOM] OK: BigQuery rows inserted")
    except Exception as e:
        # imprime error para verlo en logs de arranque/ejecución
        print(f"[WOM][ERROR] {e}")
        raise

