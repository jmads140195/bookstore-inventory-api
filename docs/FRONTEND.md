# Estante: interfaz de inventario

La interfaz es una ampliación posterior a la entrega del backend. Se publica en [pruebanextep.dateoapp.com/app](https://pruebanextep.dateoapp.com/app). Swagger sigue disponible en `/docs` y los endpoints existentes conservan sus rutas.

## Entrar y trabajar

1. Abre `/app` e introduce el usuario y contraseña de la API. La cuenta de evaluación existente también sirve aquí.
2. La pantalla muestra el catálogo y cuatro indicadores de todo el inventario: títulos, ejemplares, libros con menos de 10 unidades y libros sin precio calculado.
3. Busca por título, autor o ISBN. Puedes combinar la búsqueda con categoría y stock bajo o agotado. Los resultados se paginan de 20 en 20.
4. Con rol `full`, pulsa **Añadir libro**. Copia un ISBN válido del libro, añade el costo en USD, las existencias, categoría y país del proveedor. El formulario acepta coma o punto decimal para el costo; la API sigue validando los datos.
5. El icono de lápiz abre la edición. Cambiar el costo invalida el precio anterior; modificar solo el stock lo conserva.
6. El icono de calculadora calcula y guarda el precio de venta. El detalle muestra costo, tasa, recargo, resultado, fechas y posibles advertencias. La operación sigue realizándose en el backend.
7. Para eliminar, abre la edición y pulsa **Eliminar**. La ventana de confirmación permite conservar el libro o confirmar su eliminación definitiva.
8. Usa el botón de salida junto a tu usuario para cerrar la sesión y revocar el token.

Las cuentas `basic` pueden consultar el listado y abrir el detalle, pero no ven controles de escritura. El backend comprueba los permisos en cada petición: ocultar botones no sustituye la autorización.

## Resumen y tasas

Los indicadores superiores representan todo el inventario, aunque la tabla tenga filtros. “Stock bajo” significa menos de 10 unidades e incluye los agotados. Los datos se vuelven a consultar al guardar, eliminar o calcular, y mediante **Actualizar**. No hay actualización en tiempo real entre navegadores.

El bloque inferior muestra la tasa guardada y su fecha de publicación. **Actualizar tasa** requiere rol completo y conserva el límite global de una petición por minuto. Las cotizaciones caducadas o indisponibles muestran una explicación; el resto del inventario sigue siendo utilizable. La interfaz no cambia las reglas de respaldo del backend.

## Implementación

La página usa una plantilla Django, CSS y JavaScript sin dependencias externas de frontend ni un proceso Node en producción. Docker recoge los recursos con `collectstatic` y WhiteNoise los sirve con nombres versionados. La interfaz y la API comparten origen.

| Archivo | Función |
| --- | --- |
| `books/frontend.py` | Página `/app`, países traducidos y cabeceras de seguridad. |
| `books/templates/books/inventory.html` | Pantallas, formularios y diálogos accesibles. |
| `books/static/books/ui.css` | Diseño adaptable a escritorio y móvil. |
| `books/static/books/ui.js` | Login, consultas, formularios, errores y acciones sobre la API. |
| `books/views.py` | Filtros opcionales del listado y resumen agregado. |

Se añadieron filtros opcionales `q`, `category` y `stock` a `GET /books`, y el endpoint autenticado `GET /books/overview`. Los endpoints del backend entregado siguen funcionando. No hay cambios de esquema ni migraciones de datos.

## Sesión y seguridad

El login obtiene el token de Knox automáticamente. Se guarda en `sessionStorage` para conservar la sesión al recargar esa pestaña; no se utiliza `localStorage` ni se guardan contraseñas. Los tokens mantienen su caducidad de ocho horas. Logout los revoca en el servidor; una respuesta 401 limpia la sesión del navegador y solicita login de nuevo.

Si al cerrar sesión no hay conexión, se elimina el token de esa pestaña y se informa de que no se pudo revocar en el servidor; su caducidad original se mantiene. Cerrar la pestaña por sí solo no revoca un token en el backend.

Las peticiones usan `Authorization: Bearer` y omiten cookies. La página tiene `Cache-Control: no-store` y una política CSP que limita scripts, estilos y conexiones al mismo origen y prohíbe su inclusión en marcos. Los datos del inventario se insertan con `textContent` o valores de formulario, sin interpretarlos como HTML. `sessionStorage` es accesible para JavaScript del mismo origen: estas medidas reducen la exposición, pero no equivalen a una cookie HttpOnly.

El formulario envía exclusivamente los siete campos editables del libro. Los importes calculados se muestran respetando las cadenas decimales de la API; el navegador no vuelve a calcular el precio. Se conservan los límites, validaciones y mensajes personalizados del servidor.

## Alcance de esta ampliación

Se incluyen login, inventario, stock visual, búsqueda, filtros, creación, edición, cálculo y eliminación. La administración de cuentas y los cambios de contraseña siguen disponibles en la API y Swagger. No hay carga masiva, subida de portadas ni edición simultánea con notificaciones. La demo mantiene las condiciones de alojamiento y disponibilidad descritas en [NOTA-DE-ENTREGA.md](NOTA-DE-ENTREGA.md).
