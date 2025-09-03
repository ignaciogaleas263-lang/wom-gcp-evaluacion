
from datetime import datetime, timedelta
import os
from airflow import DAG
from airflow.providers.google.cloud.operators.gcs_to_bigquery import GCSToBigQueryOperator
from airflow.providers.google.cloud.operators.bigquery import BigQueryInsertJobOperator
from airflow.providers.google.cloud.sensors.gcs import GCSObjectsWithPrefixExistenceSensor

PROJECT_ID = os.getenv("PROJECT_ID", "wom-data-eng")
BUCKET = os.getenv("DATA_BUCKET", "wom-data-bucket")
DATASET = os.getenv("BQ_DATASET", "wom_data")
RAW_TABLE = os.getenv("RAW_TABLE", "files_raw")
TRANSFORMED_TABLE = os.getenv("TRANSFORMED_TABLE", "files_processed")
INPUT_PREFIX = os.getenv("INPUT_PREFIX", "input/")

default_args = {
    "owner": "data-eng",
    "depends_on_past": False,
    "email_on_failure": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=2),
}

with DAG(
    dag_id="gcs_to_bq_transform",
    default_args=default_args,
    start_date=datetime(2025, 1, 1),
    schedule_interval="@hourly",
    catchup=False,
    tags=["gcp", "wom", "bq"],
) as dag:

    wait_for_files = GCSObjectsWithPrefixExistenceSensor(
        task_id="wait_for_files",
        bucket=BUCKET,
        prefix=INPUT_PREFIX,
        poke_interval=60,
        timeout=60 * 30,
        mode="reschedule",
    )

    load_to_bq = GCSToBigQueryOperator(
        task_id="load_to_bq",
        bucket=BUCKET,
        source_objects=[f"{INPUT_PREFIX}*.csv"],
        destination_project_dataset_table=f"{PROJECT_ID}.{DATASET}.{RAW_TABLE}",
        write_disposition="WRITE_APPEND",
        source_format="CSV",
        autodetect=True,
        skip_leading_rows=1,
        field_delimiter=",",
    )

    transform_sql = f"""
    CREATE OR REPLACE TABLE `{PROJECT_ID}.{DATASET}.{TRANSFORMED_TABLE}` AS
    SELECT
      name,
      CAST(size AS INT64) AS size,
      CURRENT_TIMESTAMP() AS ingested_at
    FROM `{PROJECT_ID}.{DATASET}.{RAW_TABLE}`
    WHERE name IS NOT NULL;
    """

    transform_job = BigQueryInsertJobOperator(
        task_id="transform_job",
        configuration={
            "query": { "query": transform_sql, "useLegacySql": False }
        },
    )

    wait_for_files >> load_to_bq >> transform_job
