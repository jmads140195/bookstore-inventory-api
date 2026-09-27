# Publicar desde la PC con Cloudflare Tunnel

**Estado verificado el 27/09/2026:** API publicada en [pruebanextep.dateoapp.com](https://pruebanextep.dateoapp.com/docs). Cloudflared funciona como servicio Windows en inicio automático; Docker publica el puerto local 14559. Postman público aprobó 38 peticiones y 57 aserciones. Base de datos: PostgreSQL local, no cloud gestionado.

El túnel conecta Cloudflare con `http://127.0.0.1:14559`. El acceso público usa HTTPS y la API sigue exigiendo login para consultar/modificar datos. La configuración debe enrutar solo este hostname y devolver 404 para cualquier otro. No se necesitan puertos de entrada abiertos en el router ni cambios en el VPS de Dateo.

## Opción elegida: asistente de Cloudflare y servicio Windows

En la cuenta se preparó el túnel administrado desde el dashboard `Pc-MSI-Jose`. El usuario completó la instalación del conector desde su navegador habitual. Se verificó el servicio Windows ejecutándose con inicio automático. El identificador del túnel es `6ba3fb0d-f12f-411f-972b-d6f98b91166f`. No es necesario crear un segundo túnel local.

En el asistente, instala el conector siguiendo el comando privado mostrado por Cloudflare. El servicio Windows debe aparecer conectado. Configura la ruta publicada:

| Campo | Valor |
| --- | --- |
| Subdomain | `pruebanextep` |
| Domain | `dateoapp.com` |
| Type | `HTTP` |
| URL | `127.0.0.1:14559` |
| Path | Vacío |

La API ya tiene su configuración de producción en `docker-compose.tunnel.yml`; el secreto está fuera del repositorio. Inicia la API con ese archivo además del Compose base. El comando de instalación del conector contiene un token: no lo publiques en Git, capturas o documentación.

## Iniciar o detener esta demo

La configuración pública de Django se activa con:

```text
docker compose --env-file RUTA_ENV_PRIVADO -f docker-compose.yml -f docker-compose.tunnel.yml up -d
```

En la carpeta local de entregables hay dos accesos PowerShell: `INICIAR_DEMO.ps1` levanta Docker con el entorno privado preparado; `DETENER_DEMO.ps1` detiene los contenedores y conserva los datos. Estos accesos pertenecen a esta PC y no forman parte del repositorio genérico. Abre Docker Desktop antes de iniciar.

Cloudflared es un servicio Windows configurado como automático. Para inspeccionarlo: `Get-Service Cloudflared`. Si necesitas iniciarlo/detenerlo manualmente, usa la consola Servicios de Windows con permisos de administrador. Detener Docker basta para dejar de servir la API, aunque el conector siga activo.

El secreto Django está en un archivo privado fuera del repositorio. El token del conector se conserva en la configuración del servicio Windows. No publiques archivos de credenciales ni borres la carpeta de trabajo que contiene el ejecutable mientras el servicio la utilice.

## Verificar

- `https://pruebanextep.dateoapp.com/ready`: 200.
- `/docs`: Swagger disponible.
- `/books` sin token: 401; con token válido: 200.
- Collection Runner con el entorno público: todas las peticiones aprobadas.
- Las respuestas API llevan `Cache-Control: no-store`.

En el modo público, Django exige HTTPS; el HTTP local de 14559 puede redirigir a HTTPS local y no servir para navegar directamente. Usa el dominio del túnel. Para volver a modo exclusivamente local, ejecuta `docker compose -f docker-compose.yml up -d` y usa http://127.0.0.1:14559.

## Disponibilidad y límites

La PC, Docker Desktop, PostgreSQL y el túnel deben estar activos. Cerrar el proceso del túnel, suspender la PC o perder internet deja de servir la API. El worker de tasas debe continuar activo, aunque nadie visite la web.

La API y PostgreSQL se ejecutan en esta PC. Esta modalidad se eligió para la evaluación utilizando infraestructura propia, sin contratar recursos cloud adicionales. Cloudflare proporciona el acceso público. La [nota de entrega](NOTA-DE-ENTREGA.md) documenta la diferencia respecto al alojamiento cloud y a la base gestionada solicitados en los puntos 4 y 5 del enunciado.

[Guía oficial de túnel local](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/do-more-with-tunnels/local-management/create-local-tunnel/) · [Descargas oficiales](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/downloads/)


## Resolución DNS durante la verificación

Los resolutores públicos de Cloudflare y Google confirmaron el subdominio. El resolver de esta conexión conservaba temporalmente una respuesta negativa previa. Para la primera prueba se resolvió la dirección pública mediante DoH y se usó en el proceso de test, conservando hostname, SNI y validación TLS. No se deshabilitó la verificación del certificado ni se modificó el DNS permanente del equipo. Si un navegador todavía indica que no encuentra el dominio, espera la caducidad de su caché/resolver y vuelve a abrirlo.
