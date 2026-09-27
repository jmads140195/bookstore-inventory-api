# Paso 2: de una clase Python a una tabla SQL

Objetivo: definir un libro, crear su tabla y guardar/consultar una fila.
El endpoint `/health` del paso anterior conserva tu mensaje.

## 1. Proyecto y aplicación

`config` contiene la configuración general del proyecto. `books` es una
aplicación Django: un módulo que agrupa el código de una parte del negocio.
Ambos viven en el mismo proyecto y se ejecutan en el mismo servidor.

La aplicación se creó con `manage.py startapp books` y se añadió a
`INSTALLED_APPS` en `config/settings.py` para que Django la reconozca.

## 2. El modelo

En `books/models.py`, `class Book(models.Model)` define una clase Python que
hereda de la clase base de modelos de Django. Esa herencia le da capacidades
para guardar datos y consultarlos.

Correspondencias en este proyecto:

| Python / Django | Base de datos |
| --- | --- |
| Clase `Book` | Tabla `books_book` |
| Campo `title` | Columna `title` |
| Un objeto `book` guardado | Una fila |
| `book.id` | Clave primaria de esa fila |

Fragmento del modelo:

```python
title = models.CharField(max_length=255)
author = models.CharField(max_length=255)
stock_quantity = models.PositiveIntegerField(default=0)
```

`CharField` describe texto; `PositiveIntegerField`, un entero no negativo.
`default=0` proporciona el valor si no lo indicas al crear el objeto.

El modelo completo incluye título, autor, ISBN, costo, precio de venta,
stock, categoría, país del proveedor y fechas. Django añade `id` automáticamente.

Decisiones relevantes:

- `isbn` tiene `unique=True`: la base impide dos filas con el mismo ISBN.
- Los importes usan `DecimalField`, con dos posiciones decimales. En los
  ejemplos construimos los valores con `Decimal("15.99")`.
- `selling_price_local` permite `NULL`: todavía no hemos calculado ese precio.
  En Python, ese valor se representa como `None`.
- `created_at` se establece al insertar; `updated_at` se actualiza al usar `save()`.
- `Meta.constraints` añade reglas a la base de datos: costo positivo,
  stock no negativo y precio de venta no negativo si existe.

## 3. La migración

Modificar el modelo cambia el código. Para actualizar la estructura de la base
de datos se necesitan estos dos pasos, que ya ejecutamos en esta sesión:

```text
manage.py makemigrations books
manage.py migrate
```

`makemigrations` compara el modelo con el historial de migraciones y genera
un archivo que describe el cambio. Aquí creó `books/migrations/0001_initial.py`.

`migrate` aplica las migraciones pendientes en la base de datos.
La migración se guarda junto con el código para que otro entorno pueda crear
la misma estructura. No necesitas escribir el SQL manualmente.

Puedes ver el SQL generado con `manage.py sqlmigrate books 0001`.

## 4. Consultar el libro que ya guardamos

Desde la carpeta `bookstore-inventory-api`, abre la consola de Django.
En el entorno preparado en esta sesión, el comando de PowerShell es:

```powershell
& ..\..\work\.venv\Scripts\python.exe manage.py shell
```

Si creaste tu propio entorno virtual dentro del proyecto, usa:

```powershell
.\.venv\Scripts\python.exe manage.py shell
```

Después del indicador `>>>`, introduce estas líneas de Python una a una:

```python
from books.models import Book

book = Book.objects.get(isbn="9788437604947")
print(book.title)
print(book.stock_quantity)
print(book.selling_price_local)
```

Con los datos iniciales verás `El Quijote`, `25` y `None`.

`Book.objects` es el punto de acceso al ORM de Django: las herramientas para
consultar la base usando Python. `get` busca exactamente una fila. Si no la
encuentra, lanza `Book.DoesNotExist`.

La consulta equivale conceptualmente a:

```sql
SELECT * FROM books_book WHERE isbn = '9788437604947';
```

El ORM envía los valores de estas consultas como parámetros al controlador de
la base de datos. Evita construir SQL concatenando texto recibido del usuario.

## 5. Tu ejercicio: cambia el stock y confirma la persistencia

En esa misma consola, ejecuta:

```python
book.stock_quantity = 30
book.full_clean()
book.save()

reloaded = Book.objects.get(isbn="9788437604947")
print(reloaded.stock_quantity)
```

La salida esperada es `30`. La última consulta vuelve a leer la fila desde
la base de datos; no se limita a mostrar el objeto que modificaste en memoria.

Aquí hay tres acciones distintas:

1. Asignar `book.stock_quantity = 30` cambia el objeto en memoria.
2. `book.full_clean()` ejecuta las validaciones del modelo.
3. `book.save()` persiste los datos.

Para salir de la consola: `exit()`.

## 6. Qué está validado y qué falta

En esta etapa se valida el costo positivo, stock y precio no negativos, campos
obligatorios, ISBN de 10 o 13 caracteres sin separadores (con X admitida al final
del ISBN-10), unicidad y formato de dos letras mayúsculas para el país.
El ISBN se almacena sin guiones: `9788437604947`.

La comprobación del dígito de control del ISBN y la aceptación/normalización
de entradas con guiones se abordarán al construir la entrada de la API.
El país comprueba el formato de dos letras, no su pertenencia a un catálogo ISO.

`save()` no llama automáticamente a `full_clean()`. Por eso lo hacemos
explícitamente en los ejemplos y en el comando que crea el libro de muestra.
Las restricciones SQL de unicidad y de importes/stock se aplican incluso si
se omite `full_clean()`; los validadores Python de formato no son restricciones SQL.

## 7. Reproducir lo hecho y ejecutar las pruebas

Comandos para el entorno preparado, desde la raíz del proyecto:

```powershell
& ..\..\work\.venv\Scripts\python.exe manage.py migrate
& ..\..\work\.venv\Scripts\python.exe manage.py seed_demo
& ..\..\work\.venv\Scripts\python.exe manage.py test books
```

`seed_demo` crea El Quijote si no existe. Si ya existe su ISBN, conserva los
cambios que hayas hecho. Los tests usan una base de datos temporal separada y
no cambian tus libros de práctica.

La próxima etapa conecta estos datos con HTTP usando Django REST Framework:
empezaremos por consultar libros y recibir datos para crearlos.

## Referencias oficiales

- [Modelos](https://docs.djangoproject.com/en/5.2/topics/db/models/)
- [Migraciones](https://docs.djangoproject.com/en/5.2/topics/migrations/)
- [Validación y full_clean](https://docs.djangoproject.com/en/5.2/ref/models/instances/#validating-objects)
