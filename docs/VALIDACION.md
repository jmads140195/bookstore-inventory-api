# Validación de la versión 2

Comprobaciones ejecutadas el 27 de septiembre de 2026.

| Comprobación | Resultado |
| --- | --- |
| Suite Django con PostgreSQL 16 en Docker | 61 tests aprobados, sin omisiones. |
| Suite Django con SQLite local | 60 aprobados; 1 test de bloqueo de fila omitido por requerir PostgreSQL. |
| Postman mediante Newman, API Docker local | 38 peticiones y 57 aserciones; 0 fallos. |
| Esquema OpenAPI | Validado con `--validate --fail-on-warn`, sin advertencias. |
| Migraciones | `makemigrations --check --dry-run`: sin cambios pendientes. |
| Configuración de producción | `check --deploy`: sin incidencias, también con la configuración del túnel. |
| Cabeceras de respuestas privadas | Test específico aprobado tras añadir `Cache-Control: no-store`. |
| Cobertura previa al middleware de cabeceras | 88 % de líneas; excluye tests, migraciones, ASGI y WSGI. |
| Docker | Imagen construida; PostgreSQL/API saludables y worker de tasas ejecutándose. |
| URL pública / Cloudflare | HTTPS /ready y /docs correctos; /books sin token devuelve 401; Postman público: 38 peticiones, 57 aserciones, 0 fallos. |
| PostgreSQL gestionado cloud | Pendiente: el túnel utiliza PostgreSQL local. |

## Qué verifican los tests

- CRUD, paginación, filtros, validación de país/ISBN/costo/stock y duplicados.
- Recargo del ejemplo, redondeo final, persistencia e invalidación por cambio de costo.
- Cálculo concurrente con actualización de costo usando dos conexiones PostgreSQL.
- Login real, digest del token, caducidad, logout, logout-all y máximo de sesiones.
- Básico frente a completo; intentos de escalada mediante campos internos rechazados.
- Revocación por cambios de rol, desactivación y cambios/restablecimientos de contraseña.
- Límites por usuario/IP, respuesta Retry-After y rechazo de cuerpos JSON excesivos.
- Lectura de tasas sin llamadas HTTP; conservación de la anterior ante timeout/respuestas inválidas.
- Caducidad según fecha del proveedor, concesión ocupada, reintento y horarios de Caracas.
- Errores internos sanitizados, readiness y configuración de producción.

Postman inicia sesión y comprueba tanto éxitos como rechazos 400, 401, 403 y 404. Crea su propio libro y usuario: elimina el libro y desactiva el usuario al finalizar. Las pruebas Django usan una base de test separada.

La suite de tasas usa mocks: es reproducible y no depende del proveedor. Los logs de prueba incluyen errores esperados para comprobar el manejo de 4xx/5xx; el resultado final determina si una prueba pasó. El chequeo de Django no verifica DNS, disponibilidad pública, configuración de Cloudflare ni cumplimiento de base gestionada.

Los informes Newman detallados se conservaron fuera del repositorio porque pueden contener credenciales o tokens. Este documento solo publica el resumen. GitHub Actions vuelve a ejecutar la suite, el contrato y la construcción para cada commit publicado.

## Publicación comprobada

- URL: https://pruebanextep.dateoapp.com/docs
- Origen del túnel: `http://127.0.0.1:14559` en esta PC.
- Servicio Windows Cloudflared: ejecutándose, inicio automático.
- CI del cambio de implementación: [run 36329058676](https://github.com/jmads140195/bookstore-inventory-api/actions/runs/36329058676), aprobado.
- En el primer test público se sustituyó únicamente la resolución DNS del proceso por una IP del hostname verificada mediante DoH, debido a una caché negativa del resolver local. Se mantuvieron hostname, SNI y verificación de certificado HTTPS. No se accedió directamente al origen para ese recorrido.
- Cabeceras públicas comprobadas: HSTS, no-store en API, nosniff y DENY para frames.

La disponibilidad futura depende de esta PC y conexión. El resultado público comprueba el túnel y la aplicación; el requisito de PostgreSQL gestionado cloud sigue pendiente.
