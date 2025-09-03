# GCP

> Este README lo escribí para guiar el proceso de entendimiento de lo que desarrollé.  
> La idea es que cualquier persona del equipo pueda seguirlo y entender cómo resolví cada punto de la evaluación.

---

## Contenidos
- [0. Requisitos previos]
- [1. Arquitectura orientada a eventos]
- [2. CI/CD: GitHub Actions + Terraform]
- [3. Airflow DAG]
- [4. Caso API Call Center]
- [5. Estructura del repositorio]
- [6. Seguridad]

---

## 0. Requisitos previos
Para que esto corra bien necesitamos:
- Proyecto GCP con Billing habilitado.
- Tener instalados gcloud, gsutil, Terraform y Python.
- Permisos para crear recursos: Storage, Pub/Sub, Cloud Functions Gen2, BigQuery y Service Accounts/IAM.
- Si usas GitHub, debes crear un secreto `GCP_CREDENTIALS` con el JSON del Service Account.  

---

## 1. Arquitectura orientada a eventos 

La idea fue que cada vez que llegue un archivo a un bucket, automáticamente se procese y se guarde la información en BigQuery.

- Cuando subo un archivo a `wom-data-bucket`, se dispara un evento `OBJECT_FINALIZE`.  
- Ese evento lo recibe un Pub/Sub topic (`wom-gcs-object-events`).  
- Una Cloud Function Gen2 escucha el topic y procesa el evento:  
  - Guarda una fila en la tabla raw (`wom_data.files_raw`).  
  - Guarda otra fila ya transformada en la tabla processed (`wom_data.files_processed`).  

Esto permite que cada archivo que entra quede registrado y procesado sin intervención manual.

**Cómo probarlo:**  
```bash
echo "id,name,amount
1,Ana,100" > sample.csv
gsutil cp sample.csv gs://wom-data-bucket/input/sample.csv

---

## 2. CI/CD: GitHub Actions + Terraform 

No quería que esto se despliegue a mano, así que armé un pipeline para automatizarlo.

El pipeline en `.github/workflows/terraform-cf-deploy.yml` hace lo siguiente:

- Empaqueta el código de la función en un `function.zip`.
- Sube ese ZIP al bucket de código (`wom-func-code-bucket`).
- Ejecuta `terraform init`, `validate`, `plan` y `apply`.

La gracia es que el objeto se nombra con el SHA del commit, así siempre sé qué versión está desplegada.

Si la empresa quiere usar GitLab en vez de GitHub, dejé también un `.gitlab-ci.yml` que hace lo mismo, e incluso lo preparé con WIF para no usar llaves JSON.

---

## 3. Airflow DAG

En este punto me pidieron usar Airflow y operadores nativos. Lo resolví así:

- El DAG (`airflow/dags/gcs_to_bq_transform_dag.py`) espera archivos en el bucket con un **sensor de GCS**.  
- Cuando detecta archivos, usa GCSToBigQueryOperator para cargarlos en la tabla raw.  
- Luego corre un BigQueryInsertJobOperator con una query que transforma y guarda el resultado en la tabla processed.  

De esta forma, el flujo completo de ingesta y transformación queda automatizado y auditable desde Airflow (Composer en GCP).

---

## 4. Caso API Call Center (10 req/s, 600 registros/hora)

Preguntas que haría al negocio:
- ¿Cuál es la ventana máxima aceptable para completar todas las llamadas?
- ¿Necesitan trazabilidad por cliente?
- ¿Hay alguna métrica clave que debamos reportar a nivel de datos en este proceso?
- ¿El volumen de 600 registros/hora es estable o se espera un crecimiento sostenido en el tiempo?

Preguntas al proveedor de la API:
- ¿Qué formatos de autenticación soportan?
- ¿Hay un ambiente de sandbox para pruebas de carga sin afectar producción?
- ¿Qué información entregan en la respuesta de error?

### ¿Por qué esta arquitectura?

La API del proveedor permite máximo 10 req/s y el volumen esperado es ~600 registros/hora (~0,17 req/s). Mi objetivo es respetar ese límite siempre, absorber altos sin perder datos y tener trazabilidad completa para negocio.

---

#### 1) Cola gestionada 
- Desacoplo la generación de trabajos del consumo.
- Con Cloud Tasks obtengo:
  - Rate limit y concurrencia nativos por cola.
  - Retries con backoff y deduplicación por `task name` (evita duplicados si reintento).
  - Entrega garantizada: si mi worker falla, la tarea vuelve a la cola.
- Con Pub/Sub (alternativa), hago lo mismo, pero el rate limit lo implemento en el worker (token bucket). Elegí Tasks cuando quiero **control de ritmo out-of-the-box**.

Resultado: aunque el tráfico llegue a ráfagas, no voy a estar perdiendo mensajes y respeto el límite del proveedor.

---

#### 2) Workers en Cloud Run 
- Cloud Run escala de 0 a N instancias según el tamaño de la cola. Yo fijo la concurrencia y combino con el rate de Cloud Tasks para que el agregado no pase de 10 req/s.
- Pago por uso real terminando que el costo es mínimo.

---

#### 3) Retries con backoff exponencial + DLQ → resiliencia y diagnóstico
- No todas las fallas son iguales:
  - Errores 5xx / timeouts reintento con backoff exponencial.
  - Errores 4xx permanentes mando a DLQ sin insistir.

El sistema se recupera solo de fallas temporales.

---

#### 4) Métricas en BigQuery + Logging → trazabilidad end-to-end
- Inserto en BigQuery un registro por intento.
- Esto habilita dashboards (Looker Studio/GA4), alertas por SLO y análisis por segmento.
- Con Cloud Logging veo causas raíz y tasas de error.

---

#### 5) Cumplimiento de límites y capacidad
- Límite proveedor de 10 req/s.
- Carga esperada: ~600/h = 0,17 req/s que termina estando muy por debajo del límite.
- Escenarios de altos: la cola amortigua y el sistema drena a 10 req/s sostenidos hasta vaciar, sin perder datos ni terminar de saturar la API.
