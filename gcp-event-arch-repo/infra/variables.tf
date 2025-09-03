
variable "project_id" { description = "GCP Project ID"; type = string }
variable "region"     { description = "Region (e.g., us-central1)"; type = string; default = "us-central1" }
variable "location"   { description = "BQ location (US/EU)"; type = string; default = "US" }
variable "function_name" { description = "Function Gen2 name"; type = string; default = "wom-gcs-event-processor" }
variable "code_bucket_name" { description = "Bucket for function code"; type = string }
variable "data_bucket_name" { description = "Data bucket (GCS)"; type = string }
variable "pubsub_topic_name" { description = "Topic for GCS events"; type = string; default = "wom-gcs-object-events" }
variable "dataset_id" { description = "BQ dataset id"; type = string; default = "wom_data" }
variable "raw_table_id" { description = "BQ raw table"; type = string; default = "files_raw" }
variable "processed_table_id" { description = "BQ processed table"; type = string; default = "files_processed" }
variable "source_object_path" { description = "Function zip path in code bucket"; type = string }
