# Publicación y entrega

## Estado actual y elección de alojamiento

La API funciona en Docker local con PostgreSQL y un actualizador de tasas independiente. El usuario eligió publicar desde esta PC mediante Cloudflare Tunnel en `pruebanextep.dateoapp.com`. El túnel ya está conectado y la URL pública se verificó con Postman: 38 peticiones y 57 aserciones aprobadas. Consultar [CLOUDFLARE.md](CLOUDFLARE.md) para iniciar/detener y conocer las limitaciones.

El túnel permite una URL HTTPS pública, pero **la base sigue siendo local**. El PDF pide una base gestionada en la nube: ese requisito continúa pendiente con esta modalidad. No se debe presentar el PostgreSQL local como cloud gestionado. La PC debe permanecer encendida, conectada y sin suspensión durante la evaluación.

Si se necesita cumplir literalmente el requisito de base gestionada, puede migrarse la conexión de la API a una PostgreSQL gestionada separada, manteniendo el túnel, o desplegar todo en Render. El repositorio conserva `render.yaml` para esa alternativa; no se creó ningún recurso de pago.

## Alternativa: API y PostgreSQL gestionado en Render

1. Inicia sesión en [Render](https://dashboard.render.com/) y conecta el repositorio de esta prueba.
2. **New → Blueprint**. Selecciona `render.yaml`. Propone únicamente una web Docker y una PostgreSQL nueva.
3. Revisa los planes y las condiciones antes de confirmar. La plantilla usa Free; puede no estar disponible en todas las cuentas.
4. Proporciona `DJANGO_SECRET_KEY` aleatorio de al menos 50 caracteres, `BOOTSTRAP_ADMIN_USERNAME` y una contraseña inicial robusta en `BOOTSTRAP_ADMIN_PASSWORD`. Nunca los agregues a Git. Puedes generar la clave con `python -c "import secrets; print(secrets.token_urlsafe(64))"`.
5. Aplica el Blueprint y espera **Live**. El arranque migra, crea el primer administrador y trata de obtener la primera tasa. Una sincronización fallida conserva el respaldo y no impide arrancar.
6. Comprueba login y elimina ambas variables BOOTSTRAP del entorno. La cuenta ya permanece en PostgreSQL; no se restablece su contraseña al reiniciar.
7. Abre la URL asignada por Render y verifica `/health`, `/ready`, `/docs` y `/books`. Esta última debe devolver 401 sin token y 200 con un token válido.

El Free web puede suspenderse por inactividad y el Free PostgreSQL caduca a los 30 días. También hay límites de capacidad y no incluye backups. Es una opción para una evaluación temporal, no una promesa de servicio continuo. [Condiciones oficiales](https://render.com/docs/free).

La plantilla acepta el host que Render suministra, activa HTTPS y TLS hacia PostgreSQL. `RUN_MIGRATIONS=1` está pensado para una sola instancia al desplegar. Con varias réplicas se deben ejecutar migraciones una vez como paso de release.

## Actualización programada de tasas en la nube

El Blueprint gratuito no incluye un worker ni un cron. El comando inicial de la web solo actualiza cuando corresponde al arrancar. Para funcionamiento programado continuo hay que crear también un **Background Worker**, con el mismo repositorio Docker, región y conexión de base:

```text
python manage.py run_rate_scheduler
```

En Render se configura como Docker Command. Copia las variables de entorno de aplicación/base de la web, con `RUN_MIGRATIONS=0`, y no copies las credenciales de bootstrap. Este worker ejecuta los horarios y reintentos descritos en API.md y limpia tokens/contadores vencidos. Este servicio no dispone del plan Free; revisa el precio mostrado antes de contratar. [Tipos de servicios gratuitos](https://render.com/docs/free).

Otra opción es un cron gestionado que ejecute `python manage.py refresh_rates --force` a `0 12,19 * * *` (UTC, equivalente a 08:00/15:00 Caracas). En esa modalidad no hay reintentos intermedios automáticos ni limpieza continua del worker. Render factura cron con un mínimo mensual de 1 USD según la documentación consultada; verifica la tarifa al habilitarlo. [Cron oficial](https://render.com/docs/cronjobs). Ninguna de estas opciones de pago ha sido creada.

## Configurar Postman con una URL pública verificada

Después de verificar la URL real:

```text
python scripts/configure_postman.py URL_HTTPS_PUBLICA_REAL
```

Importa la colección y `postman/production.postman_environment.json`. Completa `admin_username` y `admin_password` solo en tus valores privados del entorno. Ejecuta las 38 peticiones y conserva un resumen sin credenciales. No publiques reportes Newman JSON completos: pueden incluir contraseñas o tokens de las peticiones.

El script solo configura los archivos: no verifica conectividad ni declara completado el despliegue. Antes de subir a Git, revisa que password y token estén vacíos en todos los entornos exportados.

## Lista final de entrega

- Repositorio accesible: https://github.com/jmads140195/bookstore-inventory-api
- URL HTTPS pública verificada y enlace `/docs`.
- Colección y entorno Postman con URL real, sin contraseñas o tokens.
- Credenciales de evaluación creadas específicamente y compartidas por el canal de entrega privado, nunca en README/GitHub.
- README, manual API, Docker y guía de defensa actualizados.
- Pruebas locales y Postman público aprobados; CI del commit entregado en verde.
- Confirmación del requisito PostgreSQL gestionado o explicación explícita de que sigue pendiente.
- Garantizar disponibilidad durante la evaluación; con túnel, dejar PC/Docker/actualizador/túnel activos.

## Diagnóstico

| Síntoma | Revisar |
| --- | --- |
| 400 de host | Subdominio exacto en `DJANGO_ALLOWED_HOSTS`. |
| Redirecciones HTTPS repetidas | `TRUST_PROXY_HEADERS` y cabecera del proxy. |
| 401 en inventario | Login, cabecera Bearer, expiración o revocación. |
| 403 | Rol del usuario; no se resuelve cambiando el token de formato. |
| 429 al login | Espera la ventana; detrás del proxy varios clientes podrían compartir IP. |
| 503 de `/ready` | Base, TLS y migraciones. |
| 503 al calcular | Tasa vencida, sin respaldo válido o precio fuera de capacidad. |
| `last_known` | Actualizador pendiente o proveedor sin nueva publicación; revisar worker. |
| Login perdido | Usar consola de administración confiable; no hay recuperación pública por correo. |
