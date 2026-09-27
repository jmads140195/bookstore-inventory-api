# Bookstore Inventory API

API REST para la prueba técnica de Nextep: inventario de libros, validación de
ISBN y cálculo del precio de venta mediante tasas de cambio externas.

**Implementado:** CRUD, búsquedas opcionales, cálculo con fallback, pruebas,
Docker + PostgreSQL, Swagger/OpenAPI y colección Postman.

**Pendiente externo:** publicar la API y provisionar PostgreSQL gestionado en
Render; después configurar y probar Postman contra su URL pública. El archivo
`render.yaml` prepara ese despliegue. La demo local no sustituye esos entregables.

- [Guía de defensa técnica](docs/GUIA-DE-DEFENSA.md)
- [Despliegue cloud independiente](docs/DESPLIEGUE.md)
- [Resultados de validación](docs/VALIDACION.md)
- [Lección inicial: modelos y migraciones](docs/02-modelo-y-migraciones.md)

## Stack

Python 3.12, Django 5.2, Django REST Framework, PostgreSQL 16, Gunicorn y Docker.
Las versiones exactas están fijadas en `requirements.txt`. SQLite se permite
para aprendizaje local; el entorno de producción exige PostgreSQL.

## Ejecución recomendada: Docker

Requisitos: Docker Desktop o Docker Engine con Compose, y acceso a internet
para descargar las imágenes y consultar las tasas.

Desde la carpeta del proyecto:

```sh
docker compose up --build -d
docker compose exec web python manage.py seed_demo
```

Abrir:

- API y enlaces: <http://127.0.0.1:8080/>
- Swagger: <http://127.0.0.1:8080/docs>
- Libros: <http://127.0.0.1:8080/books>
- Disponibilidad: <http://127.0.0.1:8080/ready>

Compose aplica las migraciones antes de iniciar Gunicorn y espera a que
PostgreSQL esté disponible. `seed_demo` es opcional: crea El Quijote sin
sobrescribirlo si ya existe. El ID puede variar según los registros previos.

La base está en un volumen persistente y no publica un puerto al host. La API
se expone solo en el equipo local. El usuario y contraseña de Compose son
valores de demo; la nube usa las credenciales del proveedor.

```sh
docker compose logs --tail=50 web
docker compose exec web python manage.py test
docker compose stop
```

Para reanudar: `docker compose start`. Para cambiar el puerto, configura
`API_PORT` antes de ejecutar Compose. La moneda y el respaldo de esta demo se
fijan como EUR y 0.85 en `docker-compose.yml`; modifica ambos de forma coherente
si necesitas otra moneda.

## Ejecución con Python (Windows / PowerShell)

Requisito: Python 3.12 disponible como `python`.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py seed_demo
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

En Linux/macOS, usa `python3 -m venv .venv`, `cp .env.example .env` y el ejecutable
`.venv/bin/python` en lugar de `.venv\Scripts\python.exe`.

El `.env` de ejemplo utiliza SQLite y conserva sus datos en `db.sqlite3`.
La prueba de bloqueo concurrente se ejecuta en PostgreSQL y se omite en SQLite.
`runserver` es para desarrollo; Docker ejecuta Gunicorn.

En la sesión de aprendizaje de Codex, el entorno ya preparado se encuentra en
`../../work/.venv`. Desde esta carpeta puedes usar:

```powershell
& ..\..\work\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

La instancia de desarrollo en 8000 y la instancia Docker en 8080 tienen bases
separadas. Para evaluar la colección entregada utiliza 8080 con Docker.

## Configuración

| Variable | Uso |
| --- | --- |
| `DJANGO_ENV` | `development` o `production`; habilita las comprobaciones de producción. |
| `DJANGO_DEBUG` | Debe ser `false` en producción. |
| `DJANGO_SECRET_KEY` | Clave externa aleatoria, mínimo 50 caracteres en producción. |
| `DJANGO_ALLOWED_HOSTS` | Hosts separados por comas; sin `*` en producción. |
| `DATABASE_URL` | Conexión PostgreSQL; obligatoria en producción. |
| `DATABASE_SSL_REQUIRE` | `true` para solicitar TLS al conectar a PostgreSQL cloud. |
| `LOCAL_CURRENCY` | Código ISO 4217; EUR por defecto. |
| `DEFAULT_EXCHANGE_RATE` | Respaldo USD → moneda local. Por defecto 0.85 solo para EUR. |
| `SECURE_SSL_REDIRECT` | Redirección HTTPS; activa por defecto en producción. |
| `TRUST_PROXY_HEADERS` | Activar solo detrás de un proxy que controle esas cabeceras, como Render. |
| `CSRF_TRUSTED_ORIGINS` | Orígenes HTTPS permitidos para formularios admin si se usan. |
| `PORT` | Puerto del proceso Gunicorn; 8000 por defecto, Render puede suministrarlo. |
| `RUN_MIGRATIONS` | `1` aplica migraciones al arrancar el contenedor. |
| `WEB_CONCURRENCY` | Workers de Gunicorn; 2 por defecto. |

El endpoint del proveedor está fijado en settings a la URL del enunciado:
`https://api.exchangerate-api.com/v4/latest/USD`.
No se necesita clave de API para esa integración. Tasas proporcionadas por
[ExchangeRate-API](https://www.exchangerate-api.com/).

## Endpoints

Las rutas de la API no llevan barra final. No hay autenticación en el CRUD de
esta demo para facilitar la evaluación. Usa únicamente datos de prueba.

| Método | Ruta | Resultado |
| --- | --- | --- |
| POST | `/books` | Crear libro; 201. |
| GET | `/books?page=1` | Lista paginada de 20 libros. |
| GET | `/books/{id}` | Consultar libro. |
| PUT | `/books/{id}` | Actualizar los campos editables obligatorios. |
| PATCH | `/books/{id}` | Actualización parcial adicional. |
| DELETE | `/books/{id}` | Eliminar; 204 sin cuerpo. |
| GET | `/books/search?category=Novela` | Coincidencia exacta de categoría sin distinguir mayúsculas. |
| GET | `/books/low-stock?threshold=10` | Stock estrictamente menor al umbral. |
| POST | `/books/{id}/calculate-price` | Calcular, guardar y devolver el precio. No requiere cuerpo. |
| GET | `/health` | Proceso disponible. |
| GET | `/ready` | Conexión de base de datos disponible; 503 si falla. |
| GET | `/schema` | Esquema OpenAPI. |
| GET | `/docs` | Documentación Swagger interactiva. |

El admin está en `/admin/` y requiere un usuario creado con `createsuperuser`.
No hay credenciales de admin predeterminadas.

## Ejemplo completo en PowerShell

Utiliza un ISBN que no exista en tu base; repetir este ejemplo después de
haberlo creado produce el 400 de duplicado esperado.

```powershell
$baseUrl = 'http://127.0.0.1:8080'
$payload = @{
    title = 'Libro de ejemplo'
    author = 'Autor de ejemplo'
    isbn = '978-0-306-40615-7'
    cost_usd = '15.99'
    stock_quantity = 25
    category = 'Novela'
    supplier_country = 'ES'
} | ConvertTo-Json

$book = Invoke-RestMethod -Method Post -Uri "$baseUrl/books" -ContentType 'application/json' -Body $payload
Invoke-RestMethod "$baseUrl/books"
Invoke-RestMethod "$baseUrl/books/$($book.id)"
Invoke-RestMethod -Method Post -Uri "$baseUrl/books/$($book.id)/calculate-price"
Invoke-RestMethod -Method Patch -Uri "$baseUrl/books/$($book.id)" -ContentType 'application/json' -Body '{"stock_quantity":5}'
Invoke-RestMethod "$baseUrl/books/search?category=Novela"
Invoke-RestMethod "$baseUrl/books/low-stock?threshold=10"
Invoke-RestMethod -Method Delete -Uri "$baseUrl/books/$($book.id)"
```

La colección Postman incluye además PUT, fallos de validación, verificación del
precio persistido y consulta del ID eliminado.

## Reglas de negocio y decisiones

- `cost_usd` es mayor que cero y tiene hasta dos decimales; stock es un entero no negativo.
- ISBN-10/13 con checksum: acepta espacios, guiones y X final en ISBN-10; guarda
  la representación sin separadores. ISBN normalizado único en la base.
- El país se convierte a mayúsculas y se valida contra ISO 3166-1.
- El precio de venta y las fechas son de solo lectura en la API.
- Un costo modificado invalida el precio anterior; queda `null` hasta recalcular.
- Orden por ID y paginación de 20 registros; categoría exacta y stock `< threshold`.
- Importe y tasa se expresan como cadenas en JSON para preservar decimales.

Cálculo:

```text
precio = redondear(cost_usd × tasa × 1.40, 2 decimales)
15.99 × 0.85 × 1.40 = 19.02810 → 19.03
```

El 40 % se interpreta como recargo sobre costo, siguiendo el ejemplo del PDF.
Se utiliza Decimal y ROUND_HALF_UP. El costo intermedio no se redondea antes de
aplicar el recargo; solo se redondea para mostrarlo en la respuesta.

Ejemplo con tasa 0.85 (el proveedor real puede devolver otra):

```json
{
  "book_id": 1,
  "cost_usd": "15.99",
  "exchange_rate": "0.85",
  "cost_local": "13.59",
  "margin_percentage": 40,
  "selling_price_local": "19.03",
  "currency": "EUR",
  "calculation_timestamp": "2026-09-27T12:00:00Z",
  "rate_source": "api",
  "used_fallback": false,
  "warning": null
}
```

El timestamp anterior es ilustrativo. Con fallo del proveedor, `rate_source`
es `fallback` y la respuesta avisa que el respaldo no es una cotización actual.
Si no existe un respaldo válido, se devuelve 503 sin cambiar el precio guardado.
Cada cálculo consulta al proveedor; su frecuencia de actualización determina
la vigencia de la tasa. No se promete cotización por segundo ni se implementa caché.

La red se consulta antes de abrir la transacción. PostgreSQL bloquea la fila
para leer el costo actual y escribir el precio de manera consistente con las
actualizaciones HTTP. El test de concurrencia verifica ese comportamiento.

## Errores

| Estado | Cuándo |
| --- | --- |
| 400 | Datos inválidos, ISBN duplicado o parámetros inválidos. |
| 404 | Libro o ruta inexistentes. |
| 500 | Error inesperado; se registra en el servidor y no se expone el detalle interno. |
| 503 | Base no disponible, tasa y respaldo inutilizables o precio fuera de capacidad. |

Ejemplo de validación:

```json
{
  "error": {
    "code": "validation_error",
    "message": "Datos inválidos.",
    "details": {"isbn": ["Ya existe un libro con este ISBN."]}
  }
}
```

DRF también devuelve estados estándar como 405 para un método no permitido y
415 para un tipo de contenido no soportado. Los endpoints aceptan JSON.

## Pruebas y documentación

```sh
docker compose exec web python manage.py test
docker compose exec web python manage.py makemigrations --check --dry-run
docker compose exec web python manage.py spectacular --file /tmp/schema.yml --validate --fail-on-warn
```

En un entorno Python con `requirements-dev.txt`:

```sh
python -m coverage run --source=books,config manage.py test
python -m coverage report
```

Las pruebas no llaman al proveedor real: simulan sus respuestas y errores.
Postman/Newman verifica el recorrido HTTP contra el servidor en funcionamiento.
GitHub Actions ejecuta las pruebas con PostgreSQL, valida el esquema y construye
la imagen Docker en cada push o pull request.

## Postman

Importar:

1. `postman/bookstore.postman_collection.json`.
2. `postman/local.postman_environment.json`.

Seleccionar el entorno local y ejecutar las 17 peticiones en orden. La colección
genera un ISBN nuevo, guarda su ID y elimina su libro al finalizar. Son 33
comprobaciones sobre salud, CRUD, validación, precio y filtros.

Para nube, sigue [DESPLIEGUE.md](docs/DESPLIEGUE.md) y después ejecuta:

```text
python scripts/configure_postman.py URL_HTTPS_PUBLICA_REAL
```

El script configura la colección y `production.postman_environment.json`.
Ese entorno permanece vacío hasta tener la URL real, para no aparentar un
despliegue inexistente. La ejecución local puede seguir usando su entorno propio.

## Organización y límites

```text
books/          Modelo, validación, serializers, endpoints, servicio y tests
config/         Configuración, rutas globales, salud y manejo de errores
postman/        Colección y entornos
scripts/        Configuración de Postman después de publicar
docker/         Arranque del contenedor
docs/           Defensa, despliegue y evidencia
```

El proyecto tiene una moneda global y dos decimales; no guarda historial de
cotizaciones ni movimientos de stock. Cambiar de moneda requiere revisar la
precisión y recalcular precios. No convierte ISBN-10 a su equivalente ISBN-13.
La API pública de demo no incluye autenticación, autorización ni throttling.
El bloqueo de concurrencia cubre los flujos HTTP de la API; cualquier otro
escritor debe seguir el mismo protocolo. Para uso operativo añadiríamos esos
controles y auditoría, backups y observabilidad.
