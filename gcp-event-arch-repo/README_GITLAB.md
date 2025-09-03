# (GitLab) 

---

## Qué resuelvo?

1. **Arquitectura orientada a eventos**  
   - Cuando llega un archivo a `wom-data-bucket`, se genera un evento de GCS que dispara una notificación a Pub/Sub.  
   - Ese evento lo procesa una Cloud Function, que inserta registros tanto en la tabla raw como en la tabla processed dentro del dataset `wom_data` en BigQuery.  

2. **Pipeline CI/CD en GitLab**  
   - Con el archivo `.gitlab-ci.yml` logro que el pipeline empaquete la función en un `.zip`, lo suba al bucket de código, y luego ejecute `terraform plan` y `terraform apply`.   

3. **Orquestación con Airflow**  
   - El DAG se activa alertando el bucket `wom-data-bucket` con un sensor de GCS, carga los datos con el operador nativo GCSToBigQueryOperator hacia la tabla raw, y después ejecuta una query de transformación con el BigQueryInsertJobOperator para generar la tabla procesada.  

4. **Escenario del call center (API con límite 10 req/s, ~600/hora)**  
   - Planteé las preguntas que haría al negocio y al proveedor para entender limitaciones reales.  
   - La arquitectura la pensé con Cloud Tasks o Pub/Sub + Cloud Run, aplicando un control de tasa a 10 req/s, con reintentos, DLQ* para errores y métricas en BigQuery.  



