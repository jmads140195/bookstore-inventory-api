# Guía de defensa técnica: Bookstore Inventory API

Esta guía acompaña el código de la prueba de Nextep. Está pensada para alguien
que conoce arquitectura y está retomando Python y Django. Practica las respuestas
con el proyecto abierto y verifica que puedes señalar el código correspondiente.

**Estado de la entrega:** la implementación y su ejecución local están preparadas.
El despliegue público y PostgreSQL gestionado requieren completar la configuración
de Render. Consulta `DESPLIEGUE.md` y `VALIDACION.md` para separar preparación de
resultados efectivamente verificados.

## 1. Explicación de 90 segundos

> Construí una API REST de inventario de libros con Django y Django REST Framework.
> El modelo Book tiene los datos del enunciado y restricciones de integridad.
> Los serializers validan las peticiones y convierten los modelos en JSON.
> El ViewSet expone el CRUD y los endpoints adicionales de búsqueda, stock bajo
> y cálculo de precio.
>
> El cálculo consulta una API de tasas, convierte el costo en dólares y aplica
> el recargo del 40 % que muestra el ejemplo. Trabajo con Decimal y redondeo a
> dos decimales al final. Si el proveedor falla, uso una tasa de respaldo
> configurable e indico en la respuesta que se utilizó. Si tampoco hay un
> respaldo válido, respondo 503.
>
> El proyecto incluye pruebas automatizadas, Postman, documentación OpenAPI y
> Docker. PostgreSQL es la base del entorno Docker y del despliegue propuesto.
> La configuración de producción exige PostgreSQL y secretos externos.

Adapta la última parte al estado real de tu despliegue. Cuando esté publicado,
muestra su URL y el resultado de Postman en producción.

## 2. El mapa que debes poder dibujar

```text
Cliente / Postman
       |
       v
config/urls.py -> books/urls.py -> BookViewSet
                                      |
                     +----------------+----------------+
                     |                                 |
              BookSerializer                    services.py
           valida entradas/salidas          consulta tasas y calcula
                     |                                 |
                     +----------> modelo Book <--------+
                                      |
                                     ORM
                                      |
                                  PostgreSQL
```

Para un POST de creación, el serializer valida y guarda. Para calcular el precio,
la vista localiza el libro, llama al servicio y serializa el resultado.

| Archivo | Qué debes saber explicar |
| --- | --- |
| `books/models.py` | Campos, tipos, unicidad y restricciones SQL. |
| `books/validators.py` | Normalización, ISBN-10/13 y país ISO. |
| `books/serializers.py` | JSON, validación, campos de solo lectura, duplicados y actualización. |
| `books/views.py` | Rutas del CRUD, filtros y coordinación del cálculo. |
| `books/services.py` | Proveedor, fallback, Decimal y transacción del precio. |
| `config/exceptions.py` | Respuestas uniformes y errores sanitizados. |
| `config/settings.py` | Entornos, conexión, moneda, respaldo y seguridad. |
| `Dockerfile`, `docker-compose.yml` | Aplicación, Gunicorn, PostgreSQL y arranque. |
| `render.yaml` | Recursos propuestos en la nube y variables. |

## 3. Python y Django imprescindibles

| Construcción | Lectura práctica |
| --- | --- |
| `from books.models import Book` | Importar la clase Book. |
| `class Book(models.Model)` | Definir un modelo que hereda las herramientas del ORM. |
| `def calculate_book_price(book_id)` | Definir una función que recibe un identificador. |
| `self` | Referencia al objeto actual dentro de un método. |
| `return {...}` | Devolver un diccionario de claves y valores. |
| `with transaction.atomic()` | Ejecutar un bloque dentro de una transacción. |
| `try / except` | Tratar un fallo previsto y decidir cómo responder. |
| `@action(...)` | Declarar una acción adicional del ViewSet y su ruta. |
| `Book.objects.get(pk=...)` | Buscar una fila por clave primaria. |
| `filter(stock_quantity__lt=10)` | Buscar filas cuyo stock sea menor que 10. |
| `Decimal("15.99")` | Construir un valor decimal a partir de texto. |

La indentación delimita bloques en Python. Un diccionario es una estructura
de Python; JSON es el formato de intercambio. El framework transforma entre
ambos. `None` en Python se representa como `null` en JSON.

Una aplicación Django como `books` es un módulo del proyecto. No implica otro
servidor ni un microservicio. El proyecto conserva una sola aplicación desplegable.

## 4. Recorrido del CRUD

### Crear

1. `POST /books` llega al router y a la acción `create` heredada del ViewSet.
2. El serializer normaliza ISBN y país antes de validar.
3. Comprueba tipos, campos obligatorios, ISBN, costo positivo y stock no negativo.
4. La validación de unicidad detecta un ISBN ya registrado.
5. El ORM inserta la fila; la restricción UNIQUE también protege la base.
6. La respuesta es 201 con el libro creado.

### Consultar

`GET /books` devuelve una lista paginada de 20 elementos, ordenada por ID.
`GET /books/{id}` obtiene un registro; un ID inexistente devuelve 404.

### Actualizar

`PUT` requiere los campos editables obligatorios; `PATCH` permite cambios
parciales. Si cambia `cost_usd`, se borra el precio calculado y queda `null`.
Cambiar solamente el stock conserva el precio. ID, fechas y precio de venta
son de solo lectura en la API; los valores enviados en esos campos se ignoran.

### Eliminar

`DELETE` devuelve 204 sin cuerpo. Consultar ese ID después devuelve 404.
No hay borrado lógico en esta prueba.

## 5. El cálculo que debes poder hacer a mano

Con los valores del enunciado:

```text
cost_usd = 15.99
exchange_rate = 0.85

cost_local exacto = 15.99 × 0.85 = 13.5915
precio exacto = 13.5915 × 1.40 = 19.02810
precio guardado = 19.03
cost_local mostrado = 13.59
```

**Decisión:** interpretar el 40 % siguiendo el ejemplo como recargo sobre el
costo. Un margen bruto del 40 % sobre el precio final usaría `costo / 0.60`
y produciría otro resultado. Se conserva `margin_percentage` porque así lo
llama el contrato del enunciado.

**Redondeo:** usar el costo convertido sin redondear para aplicar el recargo.
Redondear primero el costo puede alterar el precio final. Hay una prueba con
costo `0.01` y tasa `0.45`: el costo mostrado es `0.00`, pero el precio final
redondeado es `0.01`.

**Representación:** los importes salen en JSON como cadenas, por ejemplo
`"19.03"`. Esa decisión conserva la precisión y los ceros decimales. El PDF
usa números en su ejemplo; esta diferencia de representación está documentada.

**Moneda:** EUR por defecto, configurable con `LOCAL_CURRENCY`. El modelo sigue
el enunciado y tiene un solo precio local. Si cambia la moneda global, hay que
recalcular los precios existentes. No se mantiene un historial multimoneda.

## 6. Qué significa «tiempo real» aquí

Cada petición de cálculo intenta consultar el endpoint de tasas indicado en
la prueba. Se utiliza la última cotización que entregue ese proveedor.
La consulta bajo demanda no garantiza cotizaciones de mercado por segundo;
la frecuencia de actualización depende del proveedor y de su plan.

La implementación usa `https://api.exchangerate-api.com/v4/latest/USD`.
No guarda todas las cotizaciones ni implementa caché. Una evolución sería
cachear respetando la cadencia del proveedor y registrar la antigüedad de la tasa.

## 7. Fallos del proveedor y fallback

Se comprueban errores HTTP, timeout, JSON inválido, base distinta de USD,
moneda ausente y tasas nulas, negativas, no finitas o fuera del límite admitido.

- Si la API responde correctamente: `rate_source="api"` y `used_fallback=false`.
- Si falla y existe respaldo válido: 200, `rate_source="fallback"`,
  `used_fallback=true` y un aviso visible.
- Si tampoco sirve el respaldo: 503 y el precio anterior no se modifica.

La tasa `0.85` es un respaldo ilustrativo para EUR, no una cotización actual.
Si se configura otra moneda, se debe configurar su tasa de respaldo explícita.
El código limita las tasas a un valor positivo y como máximo `1e12`; además
rechaza un precio que exceda la capacidad de `selling_price_local`.

Se configuran timeouts de conexión y lectura de 3.05 y 5 segundos. No hay un
bucle de reintentos que retenga un worker indefinidamente. Estos timeouts no
constituyen una garantía estricta del tiempo total de la petición.

## 8. Concurrencia: el punto fuerte para explicar

Dos solicitudes pueden intentar crear el mismo ISBN al mismo tiempo. Aunque
ambas pasen la consulta previa del serializer, la base impone UNIQUE. Se captura
el conflicto y se transforma en 400. La validación previa mejora el mensaje;
la restricción SQL garantiza integridad frente a esa carrera.

En el cálculo se consulta al proveedor **antes** de bloquear la fila. Después,
en una transacción, se obtiene el libro con `select_for_update()`, se lee su costo
actual y se guarda el precio. Las actualizaciones HTTP usan el mismo bloqueo.
Así una respuesta de red lenta no mantiene un bloqueo y el cálculo utiliza el
costo que encuentra al adquirirlo.

PostgreSQL proporciona el bloqueo real. SQLite no ofrece el mismo comportamiento;
por eso la prueba de concurrencia se omite en SQLite y se ejecuta en PostgreSQL.
El test toma un bloqueo, lanza el cálculo en otra conexión, modifica el costo,
libera la transacción y comprueba que el cálculo usa el costo confirmado.

## 9. Demo de ocho minutos

| Tiempo | Acción | Qué explicar |
| --- | --- | --- |
| 0:00–1:00 | Abrir `/docs` y `/ready`. | Contrato y comprobación de conexión a la base. |
| 1:00–2:00 | Crear un libro y mostrar su ID. | Validación y respuesta 201. |
| 2:00–3:00 | Repetir el ISBN y enviar costo cero. | Errores 400 y consistencia. |
| 3:00–4:30 | Calcular precio y volver a consultar el libro. | Tasa, recargo, redondeo y persistencia. |
| 4:30–5:30 | Cambiar el costo. | El precio anterior queda invalidado. |
| 5:30–6:30 | Filtrar categoría y stock bajo. | Parámetros y límite estrictamente menor. |
| 6:30–7:00 | Eliminar y consultar de nuevo. | 204 y 404. |
| 7:00–8:00 | Mostrar tests y Docker. | Casos de error reproducibles y PostgreSQL. |

La colección Postman recorre estos casos automáticamente. El ISBN de prueba
se genera por ejecución. No utiliza ni elimina los libros que ya hubiera en
el inventario. Para explicar un paso, también puedes ejecutar las peticiones
individualmente después de crear el libro.

Para demostrar exactamente `19.03`, ejecuta el test con tasa `0.85` simulada:

```text
docker compose exec web python manage.py test books.test_api.BookAPITests.test_price_matches_pdf_and_is_persisted
```

Para demostrar el fallo del proveedor de manera reproducible:

```text
docker compose exec web python manage.py test books.test_api.BookAPITests.test_provider_timeout_uses_fallback
```

Explica que es un test con una dependencia simulada. El cálculo real puede
devolver otro importe porque la tasa actual cambia.

## 10. Preguntas probables y respuestas defendibles

### ¿Por qué Django y Django REST Framework?

El enunciado prefiere Django. Su ORM, migraciones y restricciones cubren la
persistencia; DRF aporta serializers, ViewSets, parsers y respuestas HTTP.
La separación permite concentrar el código propio en las reglas del negocio.

### ¿Qué aporta un serializer?

Valida el JSON recibido y convierte objetos a datos serializables. Aquí
normaliza ISBN y país, protege los campos calculados y controla el guardado.
No es una tabla ni un servicio de tasas.

### ¿Por qué una capa de servicio?

La llamada HTTP al proveedor y el cálculo pueden probarse sin depender de
la ruta. La vista coordina la petición y el servicio resuelve esa operación.
No se añadió una capa genérica de repositorios sobre el ORM para este alcance.

### ¿Qué impide una SQL injection?

Las consultas del inventario utilizan filtros del ORM con parámetros.
No se concatena entrada del usuario para construir SQL. El único SQL explícito
es `SELECT 1` del readiness, sin entrada del usuario. Un ORM no protege una
consulta SQL cruda escrita de forma insegura: hay que mantener la parametrización.

### ¿Por qué validar en la API y en la base?

La API puede explicar el error antes de escribir. Las restricciones de la
base siguen protegiendo cuando hay solicitudes concurrentes o escrituras que
no pasan por el serializer. No todos los validadores Python se vuelven SQL:
el checksum ISBN se comprueba en la aplicación.

### ¿Django valida todo al llamar a save()?

No. `save()` no llama automáticamente a `full_clean()`. Los ejemplos de consola
y `seed_demo` lo llaman explícitamente; la API valida mediante el serializer.
Las restricciones SQL se aplican al guardar incluso sin `full_clean()`.

### ¿Qué valida el ISBN?

Quita espacios y guiones, admite ISBN-10 con X final e ISBN-13 con prefijo
978/979 y verifica el dígito de control. La unicidad se aplica al valor normalizado.
No consulta un catálogo para demostrar que el libro exista. Las representaciones
ISBN-10 e ISBN-13 equivalentes no se convierten a una identidad común.

### ¿Por qué Decimal y no float?

El costo y el precio requieren aritmética decimal y una regla explícita de
redondeo. Float representa fracciones binarias y puede introducir diferencias.
El modelo utiliza DecimalField; la respuesta mantiene los decimales como texto.

### ¿PUT y PATCH son lo mismo?

PUT exige los campos editables obligatorios del recurso. PATCH permite enviar
solo los campos que cambian. Ambos validan y bloquean la fila mientras actualizan.

### ¿Por qué el precio es de solo lectura?

Se deriva del costo, de la tasa y del recargo. Permitir escribirlo libremente
por el CRUD saltaría esa regla. El endpoint de cálculo es quien lo actualiza.

### ¿Qué significa stock bajo?

`stock_quantity < threshold`; por defecto el umbral es 10. Stock igual a 10
no aparece con ese umbral. Los umbrales negativos o no enteros devuelven 400.

### ¿Qué distingue 400, 404, 500 y 503?

400: entrada inválida; 404: libro o ruta inexistente; 500: error inesperado;
503: dependencia necesaria no disponible o imposibilidad de obtener un precio
válido. Un fallo del proveedor con fallback válido se resuelve con 200 y aviso.

### ¿Qué hace transaction.atomic()?

Agrupa la lectura bloqueada y la escritura del precio. Si el bloque falla,
se revierten sus escrituras. La consulta externa queda fuera de la transacción.

### ¿Esto ya está listo para un negocio real?

Cumple el alcance funcional de la prueba y tiene controles de integridad y
configuración de despliegue. Para un inventario real añadiría autenticación,
roles, auditoría de movimientos, backups verificados, observabilidad, límites
de solicitudes e historial de precios con tasa, moneda y origen.

### ¿Por qué no hay autenticación?

No forma parte del contrato de la prueba y se facilita la evaluación pública
de todos los endpoints. El CRUD está abierto y debe contener solo datos de demo.
Una versión operativa necesita permisos, especialmente en escrituras y precios.
El admin de Django sí exige una cuenta de personal, que no se crea automáticamente.

### ¿Docker resuelve la base gestionada?

El contenedor de PostgreSQL de Compose sirve para desarrollar y verificar.
La exigencia de base gestionada se cumple al desplegar con el PostgreSQL cloud
configurado en `DATABASE_URL`. Un contenedor local no cumple esa parte del PDF.

### ¿Qué pasa si el contenedor se reinicia?

Compose conserva PostgreSQL en un volumen. En cloud la base vive fuera del
contenedor de la aplicación. Los procesos de la API pueden reiniciarse sin
que sus archivos locales sean la fuente de verdad del inventario.

### ¿Qué hacen health y ready?

`/health` comprueba que el proceso responde. `/ready` ejecuta una consulta
mínima a la base y devuelve 503 si no puede conectarse. No comprueba el proveedor
de tasas porque existe fallback. Las migraciones se aplican antes del arranque
del servidor; readiness no compara por sí mismo todo el esquema.

### ¿Cómo probaste una caída del proveedor?

Los tests simulan timeout, errores HTTP, JSON inválido y tasas inválidas.
Así son repetibles y no consumen el proveedor. Postman complementa eso con
un recorrido real HTTP y una consulta de tasa desde el entorno ejecutándose.

### ¿Qué cambiarías para escalar?

Medir primero. Cachear tasas según su vigencia, indexar consultas frecuentes
si el volumen lo exige, añadir límites, controlar conexiones PostgreSQL y
migraciones de release. Una tarea en segundo plano tendría sentido para
recalcular miles de libros, no necesariamente para una petición individual.

### ¿Qué limitaciones reconoces?

Una moneda global y dos decimales; sin historial de tasas ni cache; stock
como cantidad absoluta, sin movimientos ni reservas; CRUD público para demo;
concurrencia controlada en la API, no en cualquier script que escriba con el ORM.
El formulario admin invalida el precio al cambiar el costo, pero no utiliza el
mismo protocolo de bloqueo de la API. Antes de uso operativo unificaría esas rutas.

## 11. Si piden un cambio durante la defensa

| Petición | Punto de entrada |
| --- | --- |
| Cambiar el recargo a 30 % | `MARGIN_PERCENTAGE` en `books/services.py`, ajustar pruebas esperadas. |
| Mostrar stock menor o igual | Cambiar `stock_quantity__lt` a `stock_quantity__lte` y el test de frontera. |
| Añadir un campo editorial | Modelo → migración → serializer → tests → Postman. |
| Cambiar la moneda | Configuración y respaldo; planificar recálculo de precios existentes. |
| Añadir búsqueda por autor | Nueva consulta validada en una acción o filtro. |
| Exigir autenticación | Configurar autenticación y permisos en DRF; actualizar Postman. |

Explica primero el impacto y luego modifica. Para campos persistidos, recuerda
la migración; para cambios de contrato, actualiza pruebas y ejemplos.

## 12. Preparación en 60–90 minutos

1. **15 minutos:** lee `models.py`, `serializers.py` y `views.py`; sigue un POST.
2. **15 minutos:** recorre `services.py` y calcula el ejemplo en papel.
3. **15 minutos:** ejecuta Postman; explica cada estado HTTP en voz alta.
4. **15 minutos:** ejecuta los tests de fallback y concurrencia; localiza los mocks.
5. **15–30 minutos:** ensaya el resumen y responde las preguntas sin leer.

Si te preguntan por herramientas de IA, describe con precisión cómo se generó
el proyecto, qué revisaste tú y qué puedes demostrar. Esta guía sirve para
aprender y explicar el código entregado; adapta las respuestas a tu experiencia real.

## 13. Referencias para repasar

- [Modelos Django](https://docs.djangoproject.com/en/5.2/topics/db/models/)
- [Migraciones](https://docs.djangoproject.com/en/5.2/topics/migrations/)
- [Validación de modelos](https://docs.djangoproject.com/en/5.2/ref/models/instances/#validating-objects)
- [Serializers DRF](https://www.django-rest-framework.org/api-guide/serializers/)
- [ViewSets DRF](https://www.django-rest-framework.org/api-guide/viewsets/)
- [Transacciones Django](https://docs.djangoproject.com/en/5.2/topics/db/transactions/)
- [Proveedor de tasas](https://www.exchangerate-api.com/)
