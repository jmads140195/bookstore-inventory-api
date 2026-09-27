# Validación de la entrega

Fecha: 27 de septiembre de 2026. Estas verificaciones corresponden al entorno
local; no constituyen una prueba de despliegue cloud.

| Comprobación | Resultado observado |
| --- | --- |
| Django tests en SQLite | 36 tests descubiertos; 35 pasaron y 1 se omitió porque necesita bloqueo real de filas. |
| Django tests en PostgreSQL 16 dentro de Docker | 36 tests pasaron, incluida concurrencia con dos conexiones. |
| Postman con Newman contra Gunicorn + PostgreSQL | 17 peticiones y 33 aserciones, cero fallos. |
| OpenAPI | Generación y validación sin errores ni advertencias. |
| Migraciones | Aplicadas; `makemigrations --check --dry-run` no detecta cambios pendientes. |
| Configuración de producción | `check --deploy --fail-level WARNING` no reporta incidencias con variables de producción de prueba. |
| Docker Compose | Imagen construida; aplicación y PostgreSQL en estado healthy. |
| Cobertura local de líneas | 87 % al excluir tests, migraciones y puntos ASGI/WSGI; no es cobertura de ramas ni de todos los entornos. |

## Integración externa real

Durante el recorrido de Postman, la API consultó al proveedor y obtuvo:

```json
{
  "book_id": 2,
  "cost_usd": "15.99",
  "exchange_rate": "0.878",
  "cost_local": "14.04",
  "margin_percentage": 40,
  "selling_price_local": "19.65",
  "currency": "EUR",
  "calculation_timestamp": "2026-09-27T14:21:41.371900Z",
  "rate_source": "api",
  "used_fallback": false,
  "warning": null
}
```

El libro creado por la colección se eliminó al finalizar. La cotización es la
observada durante esta ejecución, no un valor fijo esperado en futuras pruebas.

## Casos automatizados

- Crear, listar, paginar, consultar, PUT, PATCH y eliminar.
- ISBN con guiones/espacios, checksum inválido, ISBN-10 con X y duplicados.
- Costos inválidos, stock negativo/fraccionario, país desconocido y campos extra.
- Filtros de categoría y frontera estricta del stock bajo.
- Ejemplo exacto del PDF, redondeo final, persistencia e invalidación del precio.
- Timeout, error HTTP, JSON inválido, tasas no finitas y respaldo ausente/inválido.
- 404 sin llamar al proveedor y 500/503 sin filtrar detalles internos al cliente.
- Relectura del costo después de la llamada externa y bloqueo concurrente en PostgreSQL.
- Readiness ante fallo de base de datos.
- Rechazo de debug, clave débil, SQLite, URL vacía y host comodín en producción.

Los tests de fallos provocan mensajes 400/500/503 y trazas controladas en los
logs. Son escenarios simulados; el resumen final indica si la prueba pasó.

## Reproducir

```sh
docker compose up --build -d
docker compose exec web python manage.py test
docker compose exec web python manage.py makemigrations --check --dry-run
docker compose exec web python manage.py spectacular --file /tmp/schema.yml --validate --fail-on-warn
npx newman run postman/bookstore.postman_collection.json -e postman/local.postman_environment.json
```

Para repetir el cálculo exacto del ejemplo, usa el test con la tasa simulada
0.85. La colección real puede obtener una tasa distinta.

## Pendiente de verificar externamente

- Provisionar PostgreSQL gestionado y publicar la API.
- Configurar el entorno Postman de producción con la URL asignada.
- Ejecutar la colección contra esa URL pública y registrar el resultado.

La configuración cloud está preparada en `render.yaml`; consulta `DESPLIEGUE.md`.
No se ha modificado el dominio ni el VPS de ninguna aplicación existente.
