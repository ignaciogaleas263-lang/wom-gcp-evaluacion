
output "function_uri" { value = google_cloudfunctions2_function.fn.service_config[0].uri }
output "data_bucket"  { value = google_storage_bucket.data_bucket.name }
output "code_bucket"  { value = google_storage_bucket.code_bucket.name }
output "pubsub_topic" { value = google_pubsub_topic.gcs_topic.name }
output "bq_dataset"   { value = google_bigquery_dataset.ds.dataset_id }
