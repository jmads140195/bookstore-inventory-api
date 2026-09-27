# Despliegue independiente en Render

El proyecto incluye una configuración `render.yaml` para crear una API Docker
y una base PostgreSQL gestionada en Render. No necesita modificar un dominio, Cloudflare ni el VPS de otra aplicación.

## Estado real

El código y la configuración están preparados. La aplicación todavía no tiene
una URL pública ni una base de datos gestionada provisionada. El entorno Postman
de producción está vacío deliberadamente. Los requisitos cloud del enunciado
solo estarán cumplidos cuando se publique y se pruebe la URL real.

## 1. Cuenta y repositorio

1. Crea o abre tu cuenta en [Render](https://dashboard.render.com/).
2. Conecta GitHub y permite acceso únicamente al repositorio de esta prueba.
3. Comprueba el plan Free que muestra el proveedor antes de confirmar recursos.
   El archivo declara `plan: free` tanto para web como para PostgreSQL.
   Si tu cuenta no permite esos recursos, revisa las opciones antes de contratar.

Según la [documentación del plan gratuito](https://render.com/docs/free), el
servicio web puede suspenderse por inactividad y PostgreSQL gratuito tiene
límites y caducidad. Verifica las condiciones visibles en tu cuenta y que la
base siga activa durante la evaluación. Esta configuración es para una demo.

## 2. Crear los recursos

1. En Render, abre **New → Blueprint** y selecciona el repositorio.
2. Render lee `render.yaml` y propone dos recursos nuevos:
   `nextep-bookstore-api` y `nextep-bookstore-db`.
3. Comprueba que los nombres no corresponden a recursos tuyos existentes.
4. En `DJANGO_SECRET_KEY` pega una clave aleatoria de al menos 50 caracteres.
   Puedes generarla localmente con `python -c "import secrets; print(secrets.token_urlsafe(64))"`.
   Guárdala únicamente en la configuración de Render.
5. Revisa ambos recursos y aplica el Blueprint.
6. Espera a que termine la construcción Docker y el estado sea **Live**.

El Blueprint solicita la clave de Django, conecta `DATABASE_URL` con la base
gestionada y configura EUR, tasa de respaldo, HTTPS y hosts.
`RENDER_EXTERNAL_HOSTNAME` se añade automáticamente a `ALLOWED_HOSTS`.

Las migraciones se ejecutan al iniciar con `RUN_MIGRATIONS=1`. Esta solución
está pensada para una instancia de la demo. Para varias réplicas, ejecutar las
migraciones una vez como tarea de release y usar `RUN_MIGRATIONS=0` en las réplicas.

No se crean usuarios de administración ni se cargan datos automáticamente.
La colección Postman crea sus propios libros de prueba.

## 3. Verificar la URL asignada

Copia la dirección HTTPS que Render muestra para la API. No deduzcas la URL
a partir del nombre del servicio: puede tener un sufijo.

Comprueba estas rutas en ese mismo dominio:

| Ruta | Resultado esperado |
| --- | --- |
| `/health` | 200, proceso disponible |
| `/ready` | 200, conexión a base de datos disponible |
| `/docs` | Documentación Swagger |
| `/books` | 200, lista paginada |

El health check configurado utiliza `/ready`. Si no se levanta, revisa primero
los logs de migraciones y la conexión PostgreSQL.

## 4. Apuntar Postman a producción

Desde la carpeta del proyecto y con tu entorno Python activo:

```text
python scripts/configure_postman.py URL_HTTPS_REAL_ASIGNADA_POR_RENDER
```

Sustituye el argumento por la URL base real, sin `/books` ni `/docs`.
El script actualiza la variable de la colección y el entorno
`postman/production.postman_environment.json`.

Importa ambos JSON en Postman, selecciona el entorno de producción y ejecuta
las 17 peticiones en orden. La colección genera un ISBN nuevo y al finalizar
elimina únicamente su libro de prueba.

Alternativa con Node.js y Newman:

```text
npx newman run postman/bookstore.postman_collection.json -e postman/production.postman_environment.json
```

Conserva el resultado y sube los JSON configurados al repositorio. Hasta que
esto se ejecute contra la URL pública, la validación de producción está pendiente.

## 5. Entrega

- Enlace al repositorio accesible para los evaluadores.
- URL pública de la API y enlace `/docs`.
- Colección Postman y entorno de producción con la URL real.
- README e instrucciones Docker.
- Confirmación de que la base gestionada seguirá activa durante la evaluación.

## Diagnóstico habitual

| Síntoma | Revisar |
| --- | --- |
| Error al arrancar con `SECRET_KEY` | Debe existir, ser aleatoria y tener al menos 50 caracteres. |
| Error de `DATABASE_URL` | Debe apuntar a PostgreSQL; producción rechaza SQLite. |
| HTTP 400 por host | Dominio real en `RENDER_EXTERNAL_HOSTNAME` o `DJANGO_ALLOWED_HOSTS`. |
| Redirecciones HTTPS repetidas | Proxy del proveedor y `TRUST_PROXY_HEADERS=true`. |
| 503 en `/ready` | Estado de PostgreSQL, URL de conexión, TLS y migraciones. |
| Precio con `used_fallback=true` | Falló la consulta o su respuesta no fue válida; se usó respaldo. |
| 503 en calcular precio | No hay tasa válida de API ni respaldo, o el precio excede el campo. |
| Primer acceso lento | Verifica si el servicio gratuito estaba suspendido. |

`DEFAULT_EXCHANGE_RATE=0.85` reproduce el ejemplo EUR del enunciado. Ajusta
ese valor si necesitas un respaldo adecuado a otra moneda. No es una cotización
actual. Cambiar la moneda requiere recalcular los precios existentes.

## Referencias

- [Docker en Render](https://render.com/docs/docker)
- [Configuración Blueprint](https://render.com/docs/blueprint-spec)
- [Despliegue Django](https://render.com/docs/deploy-django)
- [Límites del plan Free](https://render.com/docs/free)
