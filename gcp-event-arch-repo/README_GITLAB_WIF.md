# (GitLab + WIF) Sin llaves JSON

> Prefiero evitar llaves estáticas porque siempre representan un riesgo de seguridad.  
> Con Workload Identity Federation el runner de GitLab obtiene un token de corta duración en cada job y se autentica directamente contra GCP en tiempo de ejecución, sin necesidad de guardar archivos JSON.  
>  
> Nota: en este repo usamos como ejemplo el proyecto `wom-data-eng` y un Service Account de muestra para los despliegues:  
> `wom-ci-deployer@wom-data-eng.iam.gserviceaccount.com`.  
>  
> Esto asegura que el pipeline sea más seguro, auditable y fácil de rotar alineandolo a buenas prácticas de la programación.

