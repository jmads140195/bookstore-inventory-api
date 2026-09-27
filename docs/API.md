# Referencia de la API

Versión 2.1. Base local: `http://127.0.0.1:14559`. Base pública verificada: `https://pruebanextep.dateoapp.com`. En esta PC, la configuración pública exige HTTPS; utiliza el subdominio cuando esté activo el archivo Compose del túnel. Interfaz de inventario: `/app`; documentación interactiva: `/docs`; contrato OpenAPI: `/schema`. Todas las rutas de API van **sin barra final**. Cuerpos JSON con `Content-Type: application/json`.

## 1. Acceso y sesiones

### POST /auth/login — público

```json
{"username":"administrador","password":"TU_CONTRASEÑA_PRIVADA"}
```

Devuelve 200:

```json
{
  "token": "TOKEN_ALEATORIO",
  "token_type": "Bearer",
  "expires_at": "2026-09-28T00:00:00Z",
  "user": {
    "id": 1, "username": "administrador", "email": "",
    "first_name": "", "last_name": "", "role": "full",
    "is_active": true, "date_joined": "2026-09-27T12:00:00Z"
  }
}
```

Las fechas y el token anteriores son ilustrativos. Guarda el token como secreto y envía:

```http
Authorization: Bearer TOKEN_ALEATORIO
```

Sesión válida durante 8 horas, sin renovación automática. Máximo 5 sesiones activas por cuenta; para iniciar otra, cierra una sesión o espera a su expiración. Después del vencimiento inicia sesión nuevamente. Usuario inexistente, contraseña incorrecta y usuario inactivo devuelven el mismo 401. No hay endpoint público para registrarse.

### Endpoints de la cuenta autenticada

| Método y ruta | Entrada | Resultado |
| --- | --- | --- |
| `GET /auth/me` | Sin cuerpo | 200, perfil propio; sin hash ni contraseña. |
| `POST /auth/logout` | Sin cuerpo | 204, revoca el token usado. |
| `POST /auth/logout-all` | Sin cuerpo | 204, revoca todas sus sesiones. |
| `POST /auth/change-password` | `current_password`, `new_password` | 204, cambia su contraseña y revoca todas sus sesiones. |

Las contraseñas requieren mínimo 12 caracteres, máximo 128 en la API y validadores Django contra contraseñas comunes, enteramente numéricas o demasiado parecidas al usuario. Se guardan con hash de contraseña. Los tokens se guardan mediante digest SHA-512 con Knox. El valor completo del token solo se devuelve al iniciar sesión.

## 2. Usuarios y permisos

`basic`: consulta libros, filtros y tasa; gestiona su propia contraseña y sesiones.

`full`: además modifica el inventario, recalcula precios, sincroniza tasas y administra usuarios. El cálculo requiere full porque **guarda** el nuevo precio. No hay separación de inventarios por usuario ni por empresa.

Todas las rutas `/users` requieren `full`:

| Método y ruta | Función | Éxito |
| --- | --- | --- |
| `GET /users?page=1` | Usuarios, incluidos inactivos; 20 por página. | 200 |
| `GET /users/{id}` | Consultar un usuario. | 200 |
| `POST /users` | Crear una cuenta. | 201 |
| `PATCH /users/{id}` | Cambiar `role` y/o `is_active`. | 200 |
| `POST /users/{id}/reset-password` | Establecer `new_password`. | 204 |

Crear usuario:

```json
{
  "username": "operador",
  "password": "CONTRASEÑA_PRIVADA_LARGA",
  "role": "basic",
  "email": "",
  "first_name": "", "last_name": ""
}
```

`username` (máximo 150) y `password` son obligatorios. `role` admite `basic` o `full`; si se omite queda básico. Los demás campos son opcionales. Nombres de usuario se usan tal como se crearon al iniciar sesión. No se aceptan propiedades como `is_staff`, `is_superuser`, `groups` o `user_permissions`.

Ejemplos de cambios:

```json
{"role":"full"}
```

```json
{"is_active":false}
```

```json
{"new_password":"OTRA_CONTRASEÑA_PRIVADA_LARGA"}
```

Cambiar rol, activar/desactivar o restablecer contraseña revoca todas las sesiones del usuario afectado. Se puede reactivar con `is_active:true`. No hay `DELETE /users/{id}`: se desactiva la cuenta. Un administrador no puede cambiar su propio rol, desactivarse ni usar la ruta de restablecimiento sobre sí mismo; usa `/auth/change-password`. Los superusuarios de Django se administran desde la consola, no desde estas rutas. Esto reduce bloqueos accidentales del acceso administrativo.

El administrador inicial se crea por consola con `bootstrap_api_admin`. El rol completo no concede `is_staff` ni acceso a `/admin/`.

## 3. Inventario

| Método y ruta | Rol | Éxito |
| --- | --- | --- |
| `GET /books?page=1` | basic/full | 200, lista paginada. |
| `GET /books/{id}` | basic/full | 200, libro. |
| `GET /books/search?category=Novela` | basic/full | 200, categoría exacta sin distinguir mayúsculas. |
| `GET /books/low-stock?threshold=10` | basic/full | 200, stock estrictamente menor; default 10. |
| `GET /books/overview` | basic/full | 200, resumen global y categorías para la interfaz. |
| `POST /books` | full | 201, libro creado. |
| `PUT /books/{id}` | full | 200, reemplazar campos editables obligatorios. |
| `PATCH /books/{id}` | full | 200, modificar algunos campos. |
| `DELETE /books/{id}` | full | 204, sin cuerpo. |
| `POST /books/{id}/calculate-price` | full | 200, calcula y guarda; sin cuerpo. |

El listado admite filtros opcionales combinables: `q` busca por título, autor o ISBN (hasta 150 caracteres; los guiones y espacios del ISBN se normalizan); `category` compara la categoría exacta sin distinguir mayúsculas (hasta 100 caracteres); `stock` admite `all`, `low` (menos de 10) y `out` (cero). Los filtros se aplican en el servidor antes de paginar. Por ejemplo: `GET /books?q=quijote&stock=low&page=1`.

`GET /books/overview` devuelve `total_titles`, `total_units`, `low_stock`, `out_of_stock`, `unpriced`, `low_stock_threshold`, `currency` y `categories`. Sus indicadores abarcan todo el inventario e ignoran los filtros de la tabla. Este endpoint no consulta al proveedor de tasas y requiere autenticación.

Cuerpo de creación / PUT:

```json
{
  "title": "El Quijote",
  "author": "Miguel de Cervantes",
  "isbn": "978-84-376-0494-7",
  "cost_usd": "15.99",
  "stock_quantity": 25,
  "category": "Literatura Clásica",
  "supplier_country": "ES"
}
```

| Campo | Regla |
| --- | --- |
| `title`, `author` | Texto no vacío, hasta 255 caracteres. |
| `isbn` | ISBN-10/13 válido por checksum; admite guiones/espacios, se normaliza y debe ser único. |
| `cost_usd` | Decimal positivo, hasta 10 dígitos enteros y 2 decimales. |
| `stock_quantity` | Entero entre 0 y 2147483647; obligatorio al crear. |
| `category` | Texto no vacío, hasta 100 caracteres. |
| `supplier_country` | País ISO 3166-1 alpha-2; se convierte a mayúsculas. |
| `id`, `created_at`, `updated_at` | Solo lectura; generados por servidor. |
| `selling_price_local` | Solo lectura, hasta 16 enteros y 2 decimales, comienza null. |

En `POST /books`, `PUT /books/{id}` y `PATCH /books/{id}`, los campos desconocidos y los campos de solo lectura generan 400 con el mensaje personalizado siguiente y el detalle de los campos rechazados. Se rechaza toda la operación: tampoco se guardan otros campos válidos incluidos en la misma petición. El cliente no puede imponer el precio, el ID ni las fechas del servidor. Esta versión sustituye el comportamiento anterior que ignoraba los campos de solo lectura.

```json
{
  "error": {
    "code": "validation_error",
    "message": "Tratando de romper mi endpoint amigo? Suerte la proxima, saludos",
    "details": {
      "selling_price_local": ["Campo de solo lectura; lo establece el servidor."],
      "exchange_rate": ["Campo desconocido."]
    }
  }
}
```

Los errores de datos editables, como ISBN inválido, costo negativo o duplicados, conservan el mensaje `Datos inválidos.` y sus detalles. El mensaje personalizado identifica campos no admitidos; no implica que se haya detectado un ataque.

Cambiar `cost_usd` en una petición válida vuelve el precio a `null`; cambiar stock lo conserva. Las listas ordenan por ID, con 20 registros por página:

```json
{"count": 0, "next": null, "previous": null, "results": []}
```

Importes y tasas se representan como cadenas decimales. Timestamps ISO 8601 en UTC.

### Cálculo de precio

```text
cost_local = cost_usd × exchange_rate
selling_price_local = redondear(cost_local × 1.40, dos decimales, HALF_UP)
```

Ejemplo ilustrativo con 0.85:

```json
{
  "book_id": 1, "cost_usd": "15.99", "exchange_rate": "0.85",
  "cost_local": "13.59", "margin_percentage": 40,
  "selling_price_local": "19.03", "currency": "EUR",
  "calculation_timestamp": "2026-09-27T16:00:00Z",
  "rate_source": "stored", "used_fallback": false,
  "provider_updated_at": "2026-09-27T00:00:00Z",
  "rate_age_seconds": 57600, "warning": null
}
```

No se redondea el costo intermedio antes de calcular. `margin_percentage` conserva el nombre del enunciado, aunque la fórmula aplica un recargo sobre costo, no un margen sobre venta. Se relee y bloquea la fila del libro en PostgreSQL para persistir un precio calculado con su costo vigente.

## 4. Tasas

`GET /rates/current` requiere basic/full y devuelve `base_currency`, `currency`, `exchange_rate`, `rate_source`, `provider_updated_at`, `rate_age_seconds` y `warning`.

`POST /rates/refresh` requiere full y fuerza una consulta al proveedor. Devuelve `{"status":"updated"}`; `busy` significa que otro proceso está sincronizando. `superseded` significa que otro proceso obtuvo la concesión tras vencer la anterior. Máximo una petición manual por minuto globalmente; un fallo del proveedor devuelve 503 y conserva la tasa anterior. El comando de mantenimiento también puede devolver `not_due`.

| `rate_source` | Significado |
| --- | --- |
| `stored` | Última cotización guardada; no hay fallo pendiente ni se alcanzó la próxima publicación anunciada. |
| `last_known` | Hay fallo de sincronización o publicación pendiente; conserva la cotización anterior con advertencia. |
| `fallback` | Nunca hubo cotización guardada y se usó el respaldo explícito. No hay fecha del proveedor. |

`used_fallback` solo es true para el respaldo configurado. `last_known` sigue siendo una cotización real anterior. La antigüedad se mide desde la fecha del proveedor, no desde la última descarga: volver a descargar la misma tasa no la rejuvenece. Superar 48 horas genera 503, incluso si existe un respaldo fijo.

El worker comprueba cada minuto si corresponde sincronizar. Lo hace al arrancar sin estado previo y a las 08:00/15:00 de Caracas; las fechas internas se guardan en UTC. Reintenta tras 1, 5, 15 y luego 60 minutos mientras haya fallos. Una concesión de 2 minutos y bloqueo de estado evitan consultas simultáneas de workers. Los cálculos nunca disparan consultas externas. Reiniciar la API conserva tanto la tasa como el estado de sincronización.

La política 48 horas y el respaldo inicial son decisiones configurables para esta prueba. Para operación real se deben acordar con negocio. Los precios existentes no se recalculan automáticamente cuando cambia la tasa: se recalculan explícitamente por libro.

## 5. Límites y errores

Límites por ventanas fijas compartidas en PostgreSQL:

- Login: 30 intentos por IP y 10 por nombre de usuario cada 15 minutos.
- API autenticada: 120 peticiones por cuenta y minuto.
- Actualización manual de tasa: una por minuto globalmente.
- JSON: 64 KiB al procesar el cuerpo. Listas: 20 elementos por página.

Las ventanas fijas permiten ráfagas cerca de sus límites; no sustituyen protección de tráfico en el proxy. Con proxy y configuración por defecto, la IP observada puede ser la del proxy y compartir el límite entre clientes. Consulta SEGURIDAD.md antes de habilitar cabeceras reenviadas.

| HTTP | Significado |
| --- | --- |
| 400 | Datos inválidos, duplicado, contraseña débil o modificación propia prohibida. |
| 401 | Token ausente, inválido, revocado, vencido; o login inválido. |
| 403 | Autenticado pero sin permiso; modificación de superusuario bloqueada. |
| 404 | Registro o ruta inexistente. |
| 405 | Método no permitido. |
| 413 | Cuerpo JSON demasiado grande. |
| 415 | Tipo de contenido no admitido. |
| 429 | Límite de peticiones o sesiones activas; `Retry-After` cuando hay espera calculable. |
| 500 | Error inesperado, sin detalles internos en la respuesta. |
| 503 | Base no disponible, tasa no utilizable o precio fuera de capacidad. |

```json
{"error":{"code":"validation_error","message":"Datos inválidos.","details":{"isbn":["Ya existe un libro con este ISBN."]}}}
```

Otros errores usan el mismo objeto `error` con `code` y `message`; `details` solo aparece cuando aplica. Un 503 al calcular no modifica el precio anterior. No reintentes automáticamente un POST de creación sin comprobar si ya se completó; no hay claves de idempotencia.

## 6. Salud y documentación pública

`GET /health`: 200 si el proceso responde. `GET /ready`: verifica PostgreSQL; 200 o 503. `/docs` y `/schema` son públicos para evaluación. `/app` sirve la interfaz y su pantalla de login sin exponer datos del inventario en el HTML inicial; las consultas posteriores requieren el token. `/admin/` usa sesiones y CSRF de Django, con un superusuario creado separadamente por consola.

## 7. Ejemplo PowerShell

```powershell
$baseUrl = 'http://127.0.0.1:14559'
$credential = Get-Credential -Message 'Cuenta de la API'
$loginBody = @{username=$credential.UserName; password=$credential.GetNetworkCredential().Password} | ConvertTo-Json
$session = Invoke-RestMethod "$baseUrl/auth/login" -Method Post -ContentType 'application/json' -Body $loginBody
$headers = @{Authorization="Bearer $($session.token)"}
Invoke-RestMethod "$baseUrl/auth/me" -Headers $headers
Invoke-RestMethod "$baseUrl/books" -Headers $headers
Invoke-RestMethod "$baseUrl/rates/current" -Headers $headers
Invoke-RestMethod "$baseUrl/auth/logout" -Method Post -Headers $headers
Remove-Variable loginBody, session, headers, credential
```

No publiques capturas de respuestas de login ni exportes tokens al repositorio.
