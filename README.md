# Bookstore Inventory API

API REST para la prueba de Nextep: inventario de libros, precios, login y dos niveles de permisos. Python 3.12, Django 5.2, Django REST Framework, Knox y PostgreSQL 16.

**Listo:** código, autenticación, usuarios, tasas persistidas, actualizador independiente, Docker, tests, Swagger y Postman.

**Publicación elegida:** [Cloudflare Tunnel desde esta PC](docs/CLOUDFLARE.md), pendiente de conexión y comprobación pública. **Requisito pendiente del PDF:** PostgreSQL gestionado cloud; la base Docker sigue siendo local. El VPS y los servicios existentes de Dateo no se modifican.

## Documentación

- [API: permisos, endpoints, ejemplos y errores](docs/API.md)
- [Defensa técnica y recorrido para aprender Django](docs/GUIA-DE-DEFENSA.md)
- [Despliegue y lista final de entrega](docs/DESPLIEGUE.md)
- [Seguridad: controles y límites](docs/SEGURIDAD.md)
- [Validación ejecutada](docs/VALIDACION.md)

## Arrancar con Docker

Requiere Docker con Compose. Desde esta carpeta:

```sh
docker compose up --build -d
docker compose exec web python manage.py bootstrap_api_admin --username administrador
docker compose exec web python manage.py seed_demo
```

El segundo comando pide una contraseña de al menos 12 caracteres sin mostrarla. No hay credenciales predeterminadas. Es idempotente: si el administrador ya existe, conserva su contraseña. Los demás usuarios se crean desde `POST /users`.

Abre [Swagger local](http://127.0.0.1:8080/docs). Ejecuta `POST /auth/login`, copia el `token` devuelto y pégalo en **Authorize** (solo el token; Swagger añade `Bearer`). Después puedes probar las rutas protegidas.

Compose inicia PostgreSQL, la API y `rate-worker`. La base persiste en un volumen y no publica un puerto al host; la API solo escucha en el host local. El worker consulta si toca sincronizar cada minuto; normalmente hace dos consultas al proveedor al día, a las 08:00 y 15:00 de Caracas, además de la inicialización y reintentos.

```sh
docker compose ps
docker compose logs --tail=30 web rate-worker
docker compose exec web python manage.py test
docker compose stop
```

Para reanudar: `docker compose start`. `API_PORT` cambia el puerto local (8080 por defecto). `seed_demo` crea El Quijote sin sobrescribir un libro existente. Las claves de PostgreSQL de Compose son exclusivamente de demo.

## Probar con Postman

Importa `postman/bookstore.postman_collection.json` y `postman/local.postman_environment.json`. En el entorno local rellena `admin_username` y `admin_password` con tu cuenta completa, mantén estos valores privados y ejecuta **las 38 peticiones en orden** con Collection Runner.

La colección inicia sesión, prueba el CRUD y los precios, crea un usuario básico, comprueba sus restricciones, cambia permisos y contraseñas, desactiva ese usuario y cierra sesión. El libro temporal se elimina; el usuario temporal queda inactivo. Los tokens se borran del entorno al terminar correctamente. Si interrumpes la colección, cierra la sesión y limpia los valores sensibles antes de exportar. Nunca subas un entorno con credenciales o tokens reales.

## Ejecutar con Python / PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py bootstrap_api_admin --username administrador
.\.venv\Scripts\python.exe manage.py seed_demo
.\.venv\Scripts\python.exe manage.py refresh_rates --force
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

En otra terminal ejecuta `python manage.py run_rate_scheduler` usando ese mismo entorno virtual. En Linux/macOS el ejecutable está en `.venv/bin/python`. El `.env` permite SQLite para aprender; producción exige PostgreSQL. Los tests de bloqueos concurrentes necesitan PostgreSQL.

En la sesión local preparada, el entorno virtual está en `../../work/.venv`. La instancia Python en 8000 y Docker en 8080 utilizan bases separadas. Para la entrega y Postman usa Docker en 8080.

## Roles

| Acción | Básico (`basic`) | Completo (`full`) |
| --- | --- | --- |
| Consultar libros, filtros y tasa | Sí | Sí |
| Crear, actualizar, eliminar y recalcular libros | No | Sí |
| Crear/listar usuarios, cambiar rol, desactivar, restablecer contraseñas ajenas | No | Sí |
| Consultar su perfil, cambiar su contraseña y cerrar sus sesiones | Sí | Sí |
| Forzar actualización de tasa | No | Sí |

El rol completo es administrador de esta API; no concede acceso al servidor ni al panel Django `/admin/`. Todos comparten el mismo inventario. No hay registro público, interfaz gráfica de login ni multitenencia.

## Configuración

| Variable | Función |
| --- | --- |
| `DJANGO_ENV` | `development` o `production`. |
| `DJANGO_DEBUG` | `false` obligatorio en producción. |
| `DJANGO_SECRET_KEY` | Secreto externo; al menos 50 caracteres aleatorios en producción. |
| `DJANGO_ALLOWED_HOSTS` | Hosts explícitos separados por coma; sin comodín en producción. |
| `DATABASE_URL` | PostgreSQL obligatorio en producción; vacío permite SQLite local. |
| `DATABASE_SSL_REQUIRE` | Solicita TLS para PostgreSQL cloud. |
| `LOCAL_CURRENCY` | ISO 4217, EUR por defecto. |
| `DEFAULT_EXCHANGE_RATE` | Respaldo inicial; 0.85 para EUR reproduce el ejemplo, no una tasa actual. |
| `ALLOW_CONFIGURED_RATE_FALLBACK` | `true` permite ese respaldo solo si nunca se guardó una tasa. |
| `RATE_MAX_AGE_HOURS` | Antigüedad máxima desde la publicación del proveedor: 48 horas. |
| `SECURE_SSL_REDIRECT` | HTTPS, activo por defecto en producción. |
| `TRUST_PROXY_HEADERS` | Solo si el proxy controla `X-Forwarded-Proto`. |
| `AUTH_TRUSTED_PROXY_COUNT` | 0: usa IP de conexión; aumenta solo tras verificar proxies y `X-Forwarded-For`. |
| `CSRF_TRUSTED_ORIGINS` | Orígenes HTTPS de formularios del admin, si se usa. |
| `BOOTSTRAP_ADMIN_USERNAME/PASSWORD` | Primer administrador en despliegue no interactivo; retirar tras crearlo. |
| `RUN_MIGRATIONS` | 1: migrar antes de Gunicorn; usar una sola instancia durante migraciones. |
| `WEB_CONCURRENCY`, `PORT` | Dos workers y puerto 8000 por defecto. |

Tasas proporcionadas por [ExchangeRate-API](https://www.exchangerate-api.com/). Se usa su endpoint abierto v6 con fecha de publicación y próxima actualización. Este proveedor publica una vez al día; consultar dos veces no garantiza dos cotizaciones diferentes. [Documentación del proveedor](https://www.exchangerate-api.com/docs/free).

## Precio y disponibilidad

```text
precio = ROUND_HALF_UP(costo_USD × tasa × 1.40, 2 decimales)
15.99 × 0.85 × 1.40 = 19.02810 → 19.03
```

El 40 % es recargo sobre costo, como en el PDF. Se usa `Decimal`, sin redondear el costo intermedio. El precio se guarda con bloqueo de fila y un cambio del costo lo invalida. Los cálculos leen PostgreSQL, sin consultar al proveedor. Si la sincronización falla se conserva la última tasa; si supera 48 horas se devuelve 503 sin cambiar el precio. El respaldo configurado solo cubre un arranque sin historial.

## Verificación y estructura

```sh
docker compose exec web python manage.py test
docker compose exec web python manage.py makemigrations --check --dry-run
docker compose exec web python manage.py spectacular --file /tmp/schema.yml --validate --fail-on-warn
```

Con las dependencias de desarrollo: `python -m coverage run --source=books,config,accounts,rates manage.py test` y `python -m coverage report`. GitHub Actions ejecuta tests con PostgreSQL, valida migraciones/OpenAPI y construye Docker.

```text
accounts/   Login, tokens, usuarios, roles, límites y pruebas
books/      Modelo Book, validaciones, CRUD, precio y pruebas
rates/      Última tasa persistida, sincronización y worker
config/     Entornos, rutas, parser JSON, salud y errores
postman/    Colección y entornos sin secretos
scripts/    Configuración de la URL pública de Postman
docker/     Arranque de la API
docs/       API, seguridad, defensa, despliegue y evidencia
```

Para cerrar la entrega sigue [DESPLIEGUE.md](docs/DESPLIEGUE.md). El servicio local y las pruebas automatizadas no sustituyen el despliegue público solicitado.
