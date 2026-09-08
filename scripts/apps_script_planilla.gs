/**
 * Recibe todo lo que dejan los invitados y lo guarda en tu cuenta:
 *
 *   confirmaciones y canciones → filas en esta misma planilla
 *   fotos de la fiesta         → archivos en una carpeta de tu Drive
 *
 * Con esto solo alcanza: no hace falta Cloudinary ni ninguna otra cuenta.
 *
 * Vive adentro de la hoja, así que no hace falta proyecto en Google Cloud, ni
 * pantalla de consentimiento, ni tokens OAuth: sólo pegar esto, publicar y
 * copiar la URL.
 *
 * ── Cómo publicarlo ──────────────────────────────────────────────────────────
 *
 *  1. Abrí la planilla → Extensiones → Apps Script.
 *  2. Borrá lo que haya y pegá TODO este archivo.
 *  3. Guardá (💾).
 *  4. Implementar → Nueva implementación → engranaje ⚙ → Aplicación web.
 *       Ejecutar como:        Yo (tu cuenta)
 *       Quién tiene acceso:   Cualquier usuario
 *     (Ese "cualquier usuario" asusta, pero abajo está el TOKEN: sin él, la
 *      función rechaza todo. Es lo que hace que el sitio pueda escribir sin
 *      tener que autenticarse con Google.)
 *  5. Google te va a pedir autorizar el script. Aceptá.
 *  6. Copiá la "URL de la aplicación web" (termina en /exec).
 *
 * ── Y en Render (Environment) ────────────────────────────────────────────────
 *
 *     SHEET_WEBHOOK_URL   = la URL que termina en /exec
 *     SHEET_WEBHOOK_TOKEN = el mismo TOKEN que pusiste acá abajo
 *
 * ── Sobre el TOKEN ───────────────────────────────────────────────────────────
 *
 * Va vacío a propósito: este repo es público, y un token publicado dejaría a
 * cualquiera escribir filas en la planilla. Generá uno con:
 *
 *     python3 -c "import secrets; print(secrets.token_urlsafe(24))"
 *
 * y pegalo en las dos puntas (acá abajo y en Render). Para rotarlo, cambialo
 * en los dos lados.
 */

const TOKEN = 'PEGA-ACA-TU-TOKEN';


function doPost(e) {
  try {
    const datos = JSON.parse(e.postData.contents);

    if (datos.token !== TOKEN) {
      return responder({ ok: false, error: 'token invalido' });
    }

    if (datos.accion === 'foto') {
      return guardarFoto(datos);
    }

    const hoja = obtenerHoja(datos.hoja, datos.cabeceras || []);

    // El sitio reintenta lo que no pudo mandar. Si la fila ya entró —porque se
    // perdió la respuesta, no el envío— no la duplicamos.
    if (datos.clave && yaExiste(hoja, datos.clave)) {
      return responder({ ok: true, duplicado: true });
    }

    hoja.appendRow(datos.valores);
    return responder({ ok: true });

  } catch (err) {
    return responder({ ok: false, error: String(err) });
  }
}


/** Para probar desde el navegador que la implementación quedó viva. */
function doGet() {
  return responder({ ok: true, servicio: 'planilla casamiento' });
}


/**
 * Guarda una foto en Drive y devuelve las URLs para mostrarla.
 *
 * La carpeta se crea al lado de esta planilla, así queda todo junto. El archivo
 * se comparte "con el link" porque si no, la galería del sitio no puede
 * mostrarlo: quien lo abre es el navegador del invitado, no el servidor.
 */
function guardarFoto(datos) {
  const carpeta = obtenerCarpetaFotos();

  // El sitio reintenta lo que no pudo mandar. Si el archivo ya está, no lo
  // duplicamos: devolvemos el que había.
  const previas = carpeta.getFilesByName(datos.nombre);
  if (previas.hasNext()) {
    return responder(urlsDe(previas.next(), true));
  }

  const blob = Utilities.newBlob(
    Utilities.base64Decode(datos.contenido),
    datos.tipo || 'image/jpeg',
    datos.nombre
  );
  const archivo = carpeta.createFile(blob);
  archivo.setSharing(DriveApp.Access.ANYONE_WITH_LINK, DriveApp.Permission.VIEW);

  return responder(urlsDe(archivo, false));
}


function urlsDe(archivo, duplicado) {
  const id = archivo.getId();
  return {
    ok: true,
    duplicado: duplicado,
    id: id,
    // Este host sirve la imagen directo y acepta un ancho, así la galería pide
    // miniaturas livianas en vez de la foto entera.
    ver: 'https://lh3.googleusercontent.com/d/' + id,
    miniatura: 'https://lh3.googleusercontent.com/d/' + id + '=w600',
    enDrive: archivo.getUrl()
  };
}


function obtenerCarpetaFotos() {
  const NOMBRE = 'Fotos del casamiento';
  const planilla = DriveApp.getFileById(SpreadsheetApp.getActiveSpreadsheet().getId());
  const padres = planilla.getParents();
  const donde = padres.hasNext() ? padres.next() : DriveApp.getRootFolder();

  const existentes = donde.getFoldersByName(NOMBRE);
  return existentes.hasNext() ? existentes.next() : donde.createFolder(NOMBRE);
}


function obtenerHoja(nombre, cabeceras) {
  const libro = SpreadsheetApp.getActiveSpreadsheet();
  let hoja = libro.getSheetByName(nombre);

  if (!hoja) {
    hoja = libro.insertSheet(nombre);
    if (cabeceras.length) {
      hoja.appendRow(cabeceras);
      hoja.getRange(1, 1, 1, cabeceras.length).setFontWeight('bold');
      hoja.setFrozenRows(1);
      // La última columna es la clave interna: no le interesa a nadie.
      hoja.hideColumns(cabeceras.length);
    }
  }
  return hoja;
}


function yaExiste(hoja, clave) {
  const filas = hoja.getLastRow();
  const columnas = hoja.getLastColumn();
  if (filas < 2 || columnas < 1) return false;

  const ultimas = hoja.getRange(1, columnas, filas, 1).getValues();
  return ultimas.some(function (fila) { return fila[0] === clave; });
}


function responder(objeto) {
  return ContentService
    .createTextOutput(JSON.stringify(objeto))
    .setMimeType(ContentService.MimeType.JSON);
}
