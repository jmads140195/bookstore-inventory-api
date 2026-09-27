# Publicar desde la PC con Cloudflare Tunnel

**Estado:** cloudflared 2026.9.3 descargado del repositorio oficial y verificado con SHA-256. API preparada para el dominio; pendiente conectar el túnel y verificar la URL pública. Dominio solicitado: `pruebanextep.dateoapp.com`.

El túnel conecta Cloudflare con `http://127.0.0.1:8080`. El acceso público usa HTTPS y la API sigue exigiendo login para consultar/modificar datos. La configuración debe enrutar solo este hostname y devolver 404 para cualquier otro. No se necesitan puertos de entrada abiertos en el router ni cambios en el VPS de Dateo.

## Opción elegida: asistente de Cloudflare y servicio Windows

En la cuenta se preparó el túnel administrado desde el dashboard `Pc-MSI-Jose`. El usuario completa la instalación/autorización del conector desde su navegador habitual. No es necesario crear un segundo túnel local.

En el asistente, instala el conector siguiendo el comando privado mostrado por Cloudflare. El servicio Windows debe aparecer conectado. Configura la ruta publicada:

| Campo | Valor |
| --- | --- |
| Subdomain | `pruebanextep` |
| Domain | `dateoapp.com` |
| Type | `HTTP` |
| URL | `127.0.0.1:8080` |
| Path | Vacío |

La API ya tiene su configuración de producción en `docker-compose.tunnel.yml`; el secreto está fuera del repositorio. Inicia la API con ese archivo además del Compose base. El comando de instalación del conector contiene un token: no lo publiques en Git, capturas o documentación.

## Alternativa: túnel administrado por CLI

Estos pasos solo aplican si no se usa el túnel remoto anterior; no hacen falta ambos.


1. Descargar `cloudflared` desde el repositorio oficial de Cloudflare y verificar el checksum del release.
2. Autorizar `cloudflared tunnel login` con la cuenta del dominio.
3. Crear un túnel dedicado llamado `nextep-bookstore-pc`.
4. Crear la ruta DNS de `pruebanextep.dateoapp.com` hacia ese túnel. No sobrescribir un registro existente sin revisarlo.
5. Crear configuración local del túnel, con sus credenciales fuera del repositorio:

```yaml
tunnel: UUID_DEL_TUNEL
credentials-file: RUTA_PRIVADA_AL_JSON_DEL_TUNEL
ingress:
  - hostname: pruebanextep.dateoapp.com
    service: http://127.0.0.1:8080
  - service: http_status:404
```

6. Guardar en un archivo privado `TUNNEL_DJANGO_SECRET_KEY` con al menos 50 caracteres aleatorios. Activar el modo público de la API:

```text
docker compose --env-file RUTA_ENV_PRIVADO -f docker-compose.yml -f docker-compose.tunnel.yml up -d
```

7. Ejecutar el túnel:

```text
cloudflared tunnel --config RUTA_CONFIG_PRIVADA run nextep-bookstore-pc
```

Nunca publiques `cert.pem`, los JSON de credenciales del túnel, tokens ni archivos privados de entorno. La configuración pública del repositorio contiene solo la plantilla de Docker, sin secretos.

## Verificar

- `https://pruebanextep.dateoapp.com/ready`: 200.
- `/docs`: Swagger disponible.
- `/books` sin token: 401; con token válido: 200.
- Collection Runner con el entorno público: todas las peticiones aprobadas.
- Las respuestas API llevan `Cache-Control: no-store`.

En el modo público, Django exige HTTPS; el HTTP local de 8080 puede redirigir a HTTPS local y no servir para navegar directamente. Usa el dominio del túnel. Para volver a modo exclusivamente local, ejecuta `docker compose -f docker-compose.yml up -d` y usa http://127.0.0.1:8080.

## Disponibilidad y límites

La PC, Docker Desktop, PostgreSQL y el túnel deben estar activos. Cerrar el proceso del túnel, suspender la PC o perder internet deja de servir la API. El worker de tasas debe continuar activo, aunque nadie visite la web.

PostgreSQL sigue corriendo en esta PC. Cloudflare publica el acceso; no transforma la base local en una base gestionada cloud. Ver DESPLIEGUE.md para cerrar ese requisito del PDF.

[Guía oficial de túnel local](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/do-more-with-tunnels/local-management/create-local-tunnel/) · [Descargas oficiales](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/downloads/)

