# Nota de entrega y decisión de despliegue

## Acceso a la evaluación

- [Repositorio y código fuente](https://github.com/jmads140195/bookstore-inventory-api).
- [API pública y documentación Swagger](https://pruebanextep.dateoapp.com/docs).
- [Colección Postman](../postman/bookstore.postman_collection.json) y [entorno público](../postman/production.postman_environment.json).
- Credenciales de una cuenta de evaluación con rol `full`, compartidas por correo privado.

El evaluador puede probar los endpoints desde Swagger o Postman sin instalar el proyecto en su equipo. El rol completo permite gestionar libros, calcular precios, actualizar la tasa y administrar usuarios de la API.

## Decisión de infraestructura

Para esta prueba opté por una demo autoalojada utilizando los recursos de los que ya dispongo. La API, PostgreSQL y el proceso de actualización de tasas se ejecutan en contenedores Docker en mi equipo; Cloudflare Tunnel proporciona el acceso público HTTPS mediante un subdominio dedicado.

Esta elección evita contratar recursos cloud adicionales o asumir cargos por consumo para mantener una evaluación temporal. Permite mostrar el funcionamiento del backend, conservar los datos en PostgreSQL y entregar una ejecución reproducible mediante Docker. La API utiliza Gunicorn y la configuración de producción de Django, con autenticación y autorización en los endpoints protegidos.

## Correspondencia con el enunciado

Los puntos 4 y 5 de los entregables solicitan alojamiento de la API en un proveedor cloud reconocido y una base de datos gestionada en la nube. La modalidad entregada difiere de ambos: **la API y PostgreSQL se alojan en mi equipo; Cloudflare actúa como acceso público y no como alojamiento de esos procesos**.

Esta diferencia se declara expresamente como una decisión de alcance para la demo. Su aceptación respecto a los requisitos de infraestructura corresponde al equipo evaluador.

| Elemento | Modalidad entregada |
| --- | --- |
| Código y documentación | Repositorio con README, manual de la API, seguridad y pruebas. |
| Contenedorización | Dockerfile y Docker Compose para API, PostgreSQL y actualizador. |
| Acceso remoto | URL HTTPS pública a través de Cloudflare Tunnel. |
| Alojamiento de la API | Equipo propio; no se ha desplegado el proceso en un proveedor cloud. |
| Base de datos | PostgreSQL 16 en Docker local con volumen persistente; sin servicio gestionado cloud. |
| Evaluación con Postman | Colección y entorno configurados con la URL pública. |

## Validación y disponibilidad

La validación del 27 de septiembre de 2026 registró 61 tests aprobados con PostgreSQL y 38 peticiones con 57 aserciones aprobadas en Postman contra la URL pública. El detalle está en [VALIDACION.md](VALIDACION.md).

La disponibilidad depende de que el equipo permanezca encendido, conectado y sin suspensión, con Docker y el túnel activos. Esta demo no ofrece alta disponibilidad ni un SLA. El volumen conserva los datos al reiniciar los contenedores, pero no sustituye una política de copias de seguridad.

## Portabilidad

El repositorio incluye configuración por variables de entorno, migraciones y una plantilla `render.yaml` como referencia para otro despliegue. Una migración futura requeriría provisionar y configurar los servicios, trasladar los datos que se quieran conservar y verificar de nuevo acceso, TLS, tareas programadas y Postman. Esa infraestructura no forma parte del despliegue entregado.

Las instrucciones operativas están en [CLOUDFLARE.md](CLOUDFLARE.md) y las alternativas de despliegue en [DESPLIEGUE.md](DESPLIEGUE.md).
