# Seguridad y decisiones de alcance

La API incorpora controles para esta evaluación; no se presenta como una auditoría completa ni como un producto listo para operar datos sensibles.

## Controles implementados

| Riesgo | Control aplicado | Cómo comprobarlo |
| --- | --- | --- |
| Acceso anónimo al inventario | Autenticación obligatoria por defecto. | `GET /books` sin token devuelve 401. |
| Escalada de privilegios | Permisos por rol y lista explícita de campos; sin registro público. | Básico recibe 403 al modificar libros o crear usuarios; `is_superuser` en POST /users genera 400. |
| Robo de sesiones desde la base | Knox guarda digest del token, no el token completo; vencimiento a 8 h. | Test del almacenamiento y expiración; logout invalida el token. |
| Cuentas desactivadas con sesión | Desactivar, cambiar rol o contraseña revoca tokens. | Un token emitido antes del cambio recibe 401. |
| Ataques de contraseña | Hash de contraseña de Django, validadores y mínimo 12 caracteres. | Alta débil devuelve 400; errores de login genéricos. |
| Intentos masivos de login | Ventanas por IP y usuario en PostgreSQL, con incremento condicional atómico. | Límites devuelven 429; compartidos entre workers, sin caché local por proceso. |
| Abuso de API/proveedor | 120 peticiones por usuario/minuto; refresh manual 1/minuto global; worker con concesión temporal. | Tests de límites y sincronización ocupada. |
| JSON excesivo | Parser lee como máximo 64 KiB + 1 y rechaza cuerpos mayores. | 413 en tests de login y creación. |
| SQL injection | ORM Django y filtros con parámetros; sin SQL construido desde entradas. | Las consultas usan `filter`, `get`, `select_for_update`; sin interpolación de SQL del cliente. |
| Valores inconsistentes | Serializers, validadores y restricciones SQL de Book. | Tests de ISBN, costo, stock, país y duplicados. |
| Precio manipulado por cliente | Precio de solo lectura; cálculo exclusivamente en servidor. | Enviar `selling_price_local` no cambia el precio. |
| Precio calculado con costo concurrente antiguo | Transacción y bloqueo de la fila Book en PostgreSQL. | Test con dos conexiones reales. |
| Secretos en Git | Variables de entorno y exclusiones .gitignore/.dockerignore; Postman sin secretos. | Revisar archivos antes de publicar y mantener credenciales locales fuera del repo. |
| Filtración por errores | Respuestas sanitizadas; DEBUG desactivado y validado en producción. | Tests de 500/503 no incluyen el mensaje interno. |
| Transporte inseguro | HTTPS, HSTS y cookies seguras en producción; TLS de conexión PostgreSQL en Render. | `manage.py check --deploy` y comprobación real tras publicar. |
| Privilegios del contenedor | Usuario de sistema sin root, PostgreSQL sin puerto expuesto en Compose. | Dockerfile y configuración Compose. |

## Qué significan 401 y 403

401: no pudimos autenticar la sesión. 403: sabemos quién eres, pero tu rol no permite la acción. Ocultar un botón en un frontend no es un control suficiente; la comprobación ocurre en el backend antes del endpoint.

El rol full incluye administración de usuarios porque solo se pidieron dos niveles. En una organización real convendría separar operador (edita inventario) de administrador de cuentas. Por ahora, asignar full significa confiar también la gestión de otras cuentas.

## Cookies, CSRF y CORS

Las rutas API aceptan tokens Bearer enviados explícitamente en la cabecera; no autentican con cookies de sesión. El panel Django usa sus sesiones y protección CSRF habitual. Si se añade un frontend que guarde sesiones en cookies, habrá que diseñar CSRF y cookies para ese flujo.

No se habilitó CORS abierto. Postman y llamadas entre servidores funcionan sin CORS. Un frontend en otro origen requerirá una lista explícita de orígenes autorizados. CORS no sustituye autenticación ni restringe clientes que no sean navegadores.

## Proxy y límites de tráfico

`AUTH_TRUSTED_PROXY_COUNT=0` usa la IP de la conexión. Detrás de un proxy puede tratar muchos clientes como una misma IP: es conservador pero puede limitar a usuarios legítimos. No se habilitan cabeceras reenviadas automáticamente.

Para habilitarlas, verifica qué proxy añade cada posición de `X-Forwarded-For`, que elimina cabeceras falsificadas cuando corresponde y que no se puede llegar directamente al backend saltando ese proxy. Después configura la cantidad de proxies confiables. `TRUST_PROXY_HEADERS` controla por separado la interpretación de HTTPS; solo debe activarse con un proxy que controle `X-Forwarded-Proto`.

Los límites de aplicación no son protección DDoS: el tráfico ya llegó al proceso, el login consume CPU para verificar contraseñas y la limitación consulta PostgreSQL. Las credenciales inválidas en endpoints protegidos pueden rechazarse antes del throttle de DRF. Un despliegue operativo necesita límites de conexiones, cuerpo y tráfico en el proxy/WAF. El límite JSON se aplica cuando el endpoint procesa el cuerpo; no limita físicamente toda conexión entrante.

Las ventanas son fijas; cerca de su frontera puede haber una ráfaga mayor al límite nominal en un intervalo móvil. El worker elimina ventanas y tokens vencidos. La expiración del token se comprueba aunque la limpieza no se haya ejecutado.

## Tasas y consistencia

El proveedor es una URL fija en el código; el cliente no puede elegir una URL arbitraria para inducir peticiones del servidor. Se validan moneda base, resultado, tasa positiva y finita, y timestamps. Hay timeouts de conexión y lectura. Las sincronizaciones conservan la cotización anterior ante fallos y rechazan respuestas que retroceden su fecha.

No se retiene historial completo de cotizaciones ni del precio usado por cada operación comercial. La tasa guardada y su fecha sirven para este cálculo sugerido de inventario. Para facturación habría que guardar el contexto del cálculo de forma inmutable y acordar una política monetaria.

La consistencia con bloqueos se valida en PostgreSQL. SQLite solo sirve para desarrollo. Los cambios de rol/desactivación bloquean las filas de usuarios en un orden fijo para evitar que administradores se desactiven mutuamente en una carrera. Esta solución favorece claridad y bajo volumen; habría que optimizarla para millones de usuarios. Solicitudes ya autorizadas y en ejecución pueden completar su operación durante una revocación concurrente.

## Mejoras siguientes, por prioridad

1. Auditoría de cambios: actor, operación, entidad, fecha y campos modificados, sin contraseñas/tokens; exportación con retención definida.
2. Backups automáticos y prueba real de restauración; alertas por tasa vencida, fallos del worker y errores 5xx.
3. Separar operador y administrador, MFA para administradores y recuperación segura de contraseña por canal verificado.
4. Credenciales de base con permisos mínimos, separando migraciones y ejecución; mayor aislamiento de red y política de rotación de secretos.
5. Límites en el proxy/WAF, análisis continuo de dependencias y pruebas de carga según tráfico real.
6. Si hay varias empresas: propiedad de registros y autorización por objeto/empresa, revisadas en todos los listados y operaciones.

No se implementó borrado de usuarios, registro abierto, envío de correo, MFA, auditoría completa ni controles por empresa. Los tests cubren los comportamientos descritos; no sustituyen una revisión de seguridad independiente.

## Referencias

- [Autenticación DRF](https://www.django-rest-framework.org/api-guide/authentication/)
- [Permisos DRF](https://www.django-rest-framework.org/api-guide/permissions/)
- [Límites y alcance del throttling de DRF](https://www.django-rest-framework.org/api-guide/throttling/)
- [Configuración Knox](https://jazzband.github.io/django-rest-knox/settings/)
- [Lista de despliegue Django](https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/)
