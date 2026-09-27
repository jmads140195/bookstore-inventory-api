# Bookstore Inventory API

Proyecto de aprendizaje para resolver la prueba técnica de Nextep por etapas.

## Estado: paso 2

Django arranca y responde a `GET /health` con JSON. Este endpoint comprueba que
la aplicación responde; todavía no comprueba la conexión con la base de datos.

```json
{
  "status": "ok",
  "message": "Django montado JMA"
}
```

Ya existe el modelo `Book`, su migración inicial, validaciones básicas y cinco
pruebas automatizadas. `seed_demo` permite guardar un libro de ejemplo.

El CRUD HTTP, la normalización y validación completa del ISBN, la integración
de tasas, PostgreSQL, Docker, Postman y el despliegue se implementarán en las
siguientes etapas. Esta base todavía no es la entrega final de la prueba.

Continúa con [Paso 2: modelos, migraciones y consultas](docs/02-modelo-y-migraciones.md).

## Qué hace cada pieza

| Archivo | Responsabilidad |
| --- | --- |
| `manage.py` | Ejecutar comandos de Django, como iniciar el servidor. |
| `config/settings.py` | Configurar el proyecto y sus componentes. |
| `config/urls.py` | Asociar una URL con la función que atenderá la petición. |
| `config/views.py` | Contener nuestra primera función que responde a una petición. |
| `books/models.py` | Definir los campos y restricciones del libro. |
| `books/migrations/0001_initial.py` | Registrar cómo crear la tabla de libros. |
| `books/tests.py` | Comprobar las reglas básicas y restricciones de la base de datos. |
| `requirements.txt` | Registrar las versiones de las dependencias instaladas. |

Flujo: navegador → `GET /health` → `urls.py` → `health(request)` → respuesta JSON.

En Django, una función que recibe una petición y devuelve una respuesta se
llama una *view*. Puede devolver JSON; no tiene por qué generar una página HTML.

## Ejecutar en otro equipo (Windows / PowerShell)

Requisito: Python 3.12 instalado, disponible con el comando `python`.
Desde la carpeta del proyecto:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py seed_demo
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

Abrir <http://127.0.0.1:8000/health>. La raíz `/` todavía no tiene una ruta.

Para detener el servidor: `Ctrl+C`. Mientras se ejecuta `runserver`, Django
recarga el código cuando guardas cambios en los archivos Python.

## Entorno preparado en esta sesión

Para esta sesión se utilizó Python del entorno de Codex y se creó el entorno
virtual fuera del código, en `../../work/.venv`. Desde esta carpeta puedes
reiniciar el servidor con:

```powershell
& ..\..\work\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

Si ya hay un servidor en ese puerto, utiliza el que está ejecutándose.

## Primer ejercicio

1. Abre `config/views.py` y observa la función `health`.
2. Cambia el texto de `message` por `Ya entiendo mi primer endpoint`.
3. Guarda el archivo y recarga `/health` en el navegador.
4. Comprueba que la respuesta contiene tu nuevo texto.

Vocabulario de Python para leer esa función:

- `from ... import ...`: traer una herramienta definida en otro módulo.
- `def`: definir una función.
- `request`: la petición que Django entrega a nuestra función.
- `return`: devolver el resultado de la función.
- `{...}`: un diccionario de Python con claves y valores.
- `JsonResponse(...)`: convertir esos datos en una respuesta HTTP con JSON.
- `@require_GET`: permitir que la función atienda únicamente peticiones GET.
- La indentación delimita el cuerpo de la función.

## Configuración de esta etapa

Se conserva la configuración local que genera Django: `DEBUG=True`, una clave
de desarrollo y SQLite. `/health` no consulta tablas. Para guardar y consultar
libros hay que ejecutar las migraciones. En esta sesión ya están aplicadas.

Antes del despliegue cambiaremos esta configuración por secretos externos,
`DEBUG=False`, hosts explícitos y PostgreSQL gestionado, como exige la prueba.

## Referencia

[Tutorial oficial de Django 5.2: peticiones y respuestas](https://docs.djangoproject.com/en/5.2/intro/tutorial01/).
