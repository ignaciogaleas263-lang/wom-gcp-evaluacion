
locals { labels = { app = "event-arch-demo", company = "wom" } }

resource "google_storage_bucket" "code_bucket" {
  name                        = var.code_bucket_name
  location                    = var.region
  uniform_bucket_level_access = true
  force_destroy               = true
  labels                      = local.labels
}

resource "google_storage_bucket" "data_bucket" {
  name                        = var.data_bucket_name
  location                    = var.region
  uniform_bucket_level_access = true
  force_destroy               = true
  labels                      = local.labels
  lifecycle_rule {
    action { type = "Delete" }
    condition { age = 30 }
  }
}

resource "google_pubsub_topic" "gcs_topic" {
  name   = var.pubsub_topic_name
  labels = local.labels
}

resource "google_storage_notification" "gcs_to_pubsub" {
  bucket         = google_storage_bucket.data_bucket.name
  topic          = google_pubsub_topic.gcs_topic.id
  payload_format = "JSON_API_V1"
  event_types    = ["OBJECT_FINALIZE"]
}

resource "google_service_account" "fn_sa" {
  account_id   = "${var.function_name}-sa"
  display_name = "SA for Cloud Function v2 (WOM)"
}

resource "google_project_iam_member" "sa_run_invoker" {
  project = var.project_id
  role    = "roles/run.invoker"
  member  = "serviceAccount:${google_service_account.fn_sa.email}"
}

resource "google_project_iam_member" "sa_bq_admin" {
  project = var.project_id
  role    = "roles/bigquery.admin"
  member  = "serviceAccount:${google_service_account.fn_sa.email}"
}

resource "google_project_iam_member" "sa_storage_admin" {
  project = var.project_id
  role    = "roles/storage.admin"
  member  = "serviceAccount:${google_service_account.fn_sa.email}"
}

resource "google_project_iam_member" "sa_pubsub_sub" {
  project = var.project_id
  role    = "roles/pubsub.subscriber"
  member  = "serviceAccount:${google_service_account.fn_sa.email}"
}

resource "google_bigquery_dataset" "ds" {
  dataset_id                 = var.dataset_id
  location                   = var.location
  delete_contents_on_destroy = true
  labels                     = local.labels
}

resource "google_bigquery_table" "raw" {
  dataset_id = google_bigquery_dataset.ds.dataset_id
  table_id   = var.raw_table_id
  labels     = local.labels
  schema = jsonencode([
    {"name":"bucket","type":"STRING"},
    {"name":"name","type":"STRING"},
    {"name":"size","type":"INTEGER"},
    {"name":"time","type":"TIMESTAMP"}
  ])
}

resource "google_bigquery_table" "processed" {
  dataset_id = google_bigquery_dataset.ds.dataset_id
  table_id   = var.processed_table_id
  labels     = local.labels
  schema = jsonencode([
    {"name":"name","type":"STRING"},
    {"name":"size","type":"INTEGER"},
    {"name":"ingested_at","type":"TIMESTAMP"}
  ])
}

resource "google_cloudfunctions2_function" "fn" {
  provider = google-beta
  name     = var.function_name
  location = var.region
  labels   = local.labels

  build_config {
    runtime     = "python310"
    entry_point = "handle_gcs_event"
    source {
      storage_source {
        bucket = google_storage_bucket.code_bucket.name
        object = var.source_object_path
      }
    }
  }

  service_config {
    max_instance_count             = 3
    available_memory               = "256M"
    timeout_seconds                = 60
    ingress_settings               = "ALLOW_INTERNAL_ONLY"
    service_account_email          = google_service_account.fn_sa.email
    all_traffic_on_latest_revision = true
    environment_variables = {
      PROJECT_ID         = var.project_id
      DATASET_ID         = var.dataset_id
      RAW_TABLE_ID       = var.raw_table_id
      PROCESSED_TABLE_ID = var.processed_table_id
    }
  }

  event_trigger {
    trigger_region = var.region
    event_type     = "google.cloud.pubsub.topic.v1.messagePublished"
    pubsub_topic   = google_pubsub_topic.gcs_topic.id
    retry_policy   = "RETRY_POLICY_RETRY"
  }
}
