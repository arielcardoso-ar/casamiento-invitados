# Katherine & Ariel — sitio de invitados

**16 de Enero de 2027 · Basílica de Lourdes, Flores**

Sitio público del casamiento. Cuatro cosas, ninguna más:

| Ruta | Qué hace |
|---|---|
| `/` | La invitación: cuenta regresiva, lugares, cómo llegar y RSVP por WhatsApp. |
| `/fotos` | Los invitados suben fotos desde el celular. **Cerrado hasta el evento.** |
| `/galeria` | Álbum compartido con todo lo que suben. **Cerrado hasta el evento.** |
| `/regalo` | Alias de Mercado Pago con copiado en un toque. |

Y dentro de la invitación, dos bloques abiertos desde ahora (no esperan al
evento): **confirmar asistencia** y **sugerir una canción** para la playlist.

Todo lo que dejan los invitados —fotos, canciones y confirmaciones— se replica
en tu Google Drive. Ver *La réplica en Drive*, más abajo.

Extras para los novios, todos detrás de `?secret=<ADMIN_SECRET>`:

- `/admin/confirmaciones` — quiénes vienen, cuántos son en total y qué comen.
- `/admin/canciones` — la playlist que van sugiriendo, agrupada por tema y
  ordenada por cuántas veces la pidieron, con un botón que copia la lista
  entera en formato `tema - artista` para pegarla en el buscador de Spotify.
- `/admin/google` — estado de la réplica en Drive y qué quedó pendiente.
  Con `&reintentar=1` reencola todo lo que todavía no llegó.
- `/admin/sync-from-cloudinary` — reconstruye el índice de fotos.
- `/qr-page` — QR imprimible para los carteles del salón (sin secreto).

---

## Cómo se ve

Paleta: **verde salvia, blancos cálidos y rosas empolvados**. Todos los tokens
viven en [`static/css/wedding.css`](static/css/wedding.css) — cambiás un color
ahí y cambia el sitio entero.

La invitación (`templates/invitacion.html`) es una landing propia, a pantalla
completa. El resto de las páginas comparten el cascarón `templates/base.html`.

### Las polaroids

Las 32 fotos de los novios cuelgan de una pinza **detrás del contenido**, dos a
seis por sección, alternando izquierda y derecha y cada una con su inclinación.
Van apagadas (`opacity: .38`) porque son fondo, no protagonistas, y **se revelan
cuando entran en pantalla**: aparecen lavadas y sin color, y van tomando cuerpo
como una foto saliendo de la cámara. El filtro tarda más que la opacidad a
propósito — así se las ve *aparecer* en vez de simplemente encenderse.

Están en posición absoluta dentro de cada sección: **no le suman un solo píxel
de alto a la invitación** (medido: la página mide exactamente lo mismo con las
fotos que sin ellas). En el celular se meten un poco fuera de la pantalla para
no pararse encima del texto; en pantallas anchas, donde sobra margen, se
despegan del borde.

Se configuran en dos listas, en [`config.py`](config.py):

- **`POLAROIDS`** — las fotos, en el orden en que aparecen al bajar. Cada una
  lleva `base` (el prefijo de los archivos) y `foco`, que es el
  `object-position`: la polaroid recorta un cuadrado y esto decide qué parte
  del original sobrevive. Subí el segundo número para bajar el encuadre.
- **`RANURAS`** — dónde puede colgar una foto en cada sección: lado, borde
  desde el que se mide y distancia.

Cuántas entran por sección no lo decide el gusto sino la aritmética. Una
polaroid mide ~120 px de alto en un celular y ~197 px en escritorio, y las
secciones cambian de alto entre los dos: en el celular el texto envuelve más,
así que *detalles* es alta en el celular y baja en la compu. Las ranuras están
calculadas para que **dos del mismo lado no se toquen en ninguno de los dos
anchos** — dos polaroids superpuestas al 38% se transparentan entre sí y quedan
como una doble exposición sucia. Si agregás fotos, revisá eso.

El giro y el tamaño se turnan solos (`GIROS` y `ESCALAS`, de largo primo entre
sí para que la combinación tarde en repetirse). Sobran ranuras: si sumás fotos,
se cuelgan solas en las que quedan libres.

Para cambiar las fotos:

```bash
cd scripts && ../.venv/bin/python preparar_fotos.py ~/Downloads/*.jpg
```

El orden de los argumentos numera los archivos (`foto-1`, `foto-2`…). Acepta
HEIC de iPhone. Genera dos anchos por foto (240 y 480 px) encajados en un
cuadrado: como la polaroid recorta un cuadrado, de una foto vertical bajar el
ancho completo sería traer el triple de píxeles de los que se ven. Las 32 juntas
ocupan 1,5 MB en el repo y un celular baja menos de la mitad, de a poco, porque
van con `loading="lazy"`.

Si borrás fotos, la invitación sigue andando con las que queden: no cuelga
marcos vacíos.

---|---|
| `base` | prefijo de los archivos, sin el `-300`/`-600` |
| `zona` | en qué sección cuelga: `welcome`, `count`, `band`, `details`, `howto`, `rsvp`, `actions`, `closing` |
| `lado` | `izq` o `der`: contra qué margen se apoya |
| `y` | a qué altura de la sección arranca |
| `giro` | la inclinación. Que ninguna quede derecha ni repita a su vecina |
| `escala` | retoque de tamaño sobre el ancho base |
| `foco` | `object-position`: la polaroid recorta un cuadrado, esto decide qué parte del original sobrevive. Subí el segundo número para bajar el encuadre |
| `alt` | descripción para lectores de pantalla |

Para agregar una sección con foto alcanza con poner `{{ capa('zona') }}` como
primer hijo de la sección y sumarle la clase `tiene-fondo`.

Para cambiar las fotos:

```bash
cd scripts && ../.venv/bin/python preparar_fotos.py ~/Downloads/una.jpg ~/Downloads/otra.jpg
```

El orden de los argumentos es el que numera los archivos (`foto-1`, `foto-2`…).
Genera dos anchos por foto (300 y 600 px), encajados en un cuadrado: la polaroid
recorta un cuadrado, así que de una foto vertical bajar 600 px de ancho sería
traer el triple de píxeles de los que se ven. Las ocho juntas pesan menos de
500 KB, y un celular baja sólo la mitad.

Si borrás las fotos, la invitación sigue andando sin ellas: no cuelga marcos
vacíos.

---|---|
| `base` | prefijo de los archivos, sin el `-500`/`-900` |
| `foco` | `object-position`: la polaroid es cuadrada y la foto apaisada, así que hay que decir qué parte del original se conserva. Bajá el segundo número para mostrar más de arriba de la cabeza |
| `giro` | la inclinación con la que cuelga. Que ninguna quede derecha ni igual a otra |
| `pie` | el texto manuscrito del borde de abajo (podés dejarlo vacío) |
| `alt` | descripción para lectores de pantalla |

Van colgadas en la bienvenida y en el cierre. Si sumás una tercera foto,
aparece sola en el bloque de confirmación — el hueco ya está puesto en el
template.

Para cambiarlas:

```bash
cd scripts && ../.venv/bin/python preparar_fotos.py ~/Downloads/una.jpg ~/Downloads/otra.jpg
```

Eso genera dos anchos por foto (500 y 900 px) para que cada teléfono baje sólo
lo que necesita. Si borrás las fotos, la invitación sigue andando sin ellas: no
cuelga marcos vacíos.

---

## Correr en local

```bash
pip install -r requirements.txt && python app.py
```

Abrí <http://localhost:5001>.

Sin Cloudinary configurado las fotos se guardan en `static/uploads/` — alcanza
perfecto para probar.

### Ver la galería antes de tiempo

La galería y la subida están cerradas hasta el día del casamiento. Para
espiarlas:

```bash
open "http://localhost:5001/galeria?unlock=preview"
```

El pase queda en una cookie de sesión. Para soltarlo, entrá con `?unlock=`
(vacío). En producción el pase es el valor de `ADMIN_SECRET`.

---

## Configuración

Todo lo que se muestra —nombres, fecha, lugares, teléfono, alias— vive en
[`config.py`](config.py) y se puede sobreescribir por variable de entorno sin
tocar el código.

| Variable | Para qué | Por defecto |
|---|---|---|
| `FECHA_EVENTO` | Fecha y hora de la ceremonia (ISO, hora de Argentina). Manda la cuenta regresiva. | `2027-01-16T17:30:00` |
| `APERTURA_FOTOS` | Cuándo se habilitan galería y subida. | igual que `FECHA_EVENTO` |
| `DIAS_SUBIDA_ABIERTA` | Días que siguen abiertas después del evento (`0` = para siempre). | `0` |
| `MP_ALIAS` | Alias de Mercado Pago. | `arielcardoso.mp` |
| `MP_CVU` | CVU para transferencia bancaria, opcional. | vacío |
| `MP_LINK` | Link de cobro de Mercado Pago. **Si lo cargás, el sitio genera solo el QR de pago.** | vacío |
| `MP_QR_IMG` | QR oficial bajado de la app de MP. Archivo dentro de `static/` o URL. Tiene prioridad sobre `MP_LINK`. | vacío |
| `RSVP_WHATSAPP` | Teléfono de confirmación, sólo dígitos con país. | `541159632661` |
| `CEREMONIA_*` / `FIESTA_*` | Título, detalle y búsqueda de mapa de cada lugar. | ver `config.py` |

---

## El regalo: por qué no hay QR de pago

Se evaluó y se descartó a propósito. **No existe un QR de Mercado Pago sin
comisión.** El QR de cobro (Transferencias 3.0) le descuenta al que recibe
~0,99% + IVA, y el Link de pago cobra más todavía. Lo único gratis es la
transferencia común a alias o CVU, que no se puede meter en un QR: el código
tiene que salir de la cuenta y siempre es de cobro.

Así que `/regalo` está armado para que el camino gratis cueste lo mínimo posible:

1. El invitado escanea el QR del cartel (destino **Regalo** en `/qr-page`).
2. Toca **un botón**: copia el alias y abre Mercado Pago en el mismo gesto.
3. En la app: *Transferir dinero* → pegar → monto → confirmar.

Son dos toques más que un QR de cobro, y llega el 100%. Sobre $50.000 de regalo
la diferencia es ~$600 por invitado.

En computadora el botón sólo copia, porque abrir la app ahí no le sirve a nadie.
Si cargás `MP_CVU` aparece además el CVU para quien transfiera desde el banco.

### Si algún día lo querés igual

El soporte quedó hecho, apagado por defecto. Cargá `MP_LINK` (app: *Cobrar →
Tu Link*) o `MP_QR_IMG` (app: *Cobrar → QR*, imagen dentro de `static/`) y el QR
aparece solo en `/regalo` y en `/qr-page`. El alias sigue estando abajo.

## La réplica en Drive

Cada foto, canción y confirmación se copia a tu Google Drive:

| Qué | A dónde |
|---|---|
| Fotos | un archivo en la carpeta de Drive, más una fila en la planilla con quién la subió y el link |
| Canciones | pestaña `Canciones` de la planilla |
| Confirmaciones | pestaña `Confirmaciones` de la planilla |

Las pestañas se crean solas con sus cabeceras la primera vez.

**Es un espejo, no una dependencia.** Todo se encola en un hilo aparte: si Drive
está caído o el token venció, el invitado igual sube la foto y no ve ningún
error. Lo que falla queda sin marcar en SQLite y se reintenta desde
`/admin/google?secret=...&reintentar=1`. Sin credenciales cargadas, el sitio
funciona exactamente igual y no espeja nada.

### Por qué no va a Google Photos

No se puede. Desde 2025 la API de Google Photos sólo deja tocar lo que creó la
propia app: no hay forma de agregar fotos a un álbum que hiciste vos a mano, ni
de escribir en uno del que sólo tenés el link para compartir. Si querés que
terminen en Photos, lo práctico es subir la carpeta de Drive a mano después de
la fiesta.

### Por qué OAuth y no una cuenta de servicio

Una cuenta de servicio escribe bien en una planilla que ya existe, pero **no
puede subir archivos a un Drive personal**: no tiene cuota propia y Google
rechaza la subida con *"Service Accounts do not have storage quota"*. Con OAuth
los archivos quedan a tu nombre, en tu Drive y contra tu cuota.

### Cómo se configura

```bash
pip install google-auth-oauthlib
python scripts/autorizar_google.py
```

El script explica los cuatro pasos en Google Cloud (habilitar Drive API y
Sheets API, crear un cliente OAuth de escritorio), abre el navegador e imprime
las variables listas para pegar en Render:

| Variable | De dónde sale |
|---|---|
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | el cliente OAuth que creaste |
| `GOOGLE_REFRESH_TOKEN` | lo imprime el script |
| `DRIVE_FOLDER_ID` | `drive.google.com/drive/folders/<ESTO>` |
| `SHEET_ID` | `docs.google.com/spreadsheets/d/<ESTO>/edit` |

El sitio pide el permiso mínimo (`drive.file`): sólo ve los archivos que crea
él, no el resto de tu Drive. El refresh token es una llave a tu cuenta — va en
las variables de entorno de Render, nunca en el repo.

---

## Deploy en Render

Ya está descripto en [`render.yaml`](render.yaml). Variables a cargar a mano:

- `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET` —
  **obligatorias**: sin ellas las fotos se pierden cuando Render recicla el
  contenedor.
- `ADMIN_SECRET` — habilita el sync manual y la vista previa.
- `SECRET_KEY` — firma la cookie de vista previa. Sin ella se pierde en cada
  reinicio.

### Qué pasa si Render reinicia en plena fiesta

El SQLite es sólo un índice y es descartable. Si el contenedor se recicla y la
galería queda vacía, la app **se reconstruye sola** desde Cloudinary la primera
vez que alguien entra a `/galeria`. Si hiciera falta forzarlo:

```
https://TU-DOMINIO/admin/sync-from-cloudinary?secret=TU_ADMIN_SECRET
```

---

## Checklist para el día del casamiento

1. Confirmar que `FECHA_EVENTO` y `APERTURA_FOTOS` estén en la hora correcta.
2. Entrar a `/qr-page`, elegir destino **Subir fotos** e imprimir los carteles.
3. Probar el QR con un celular ajeno (no sólo el tuyo).
4. Verificar que `/regalo` muestre el alias correcto y que el botón copie y abra Mercado Pago desde un celular real.
5. Subir una foto de prueba con `?unlock=<ADMIN_SECRET>` y después borrarla
   desde Cloudinary.
