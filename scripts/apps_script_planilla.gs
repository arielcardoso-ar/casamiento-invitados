/**
 * Recibe las confirmaciones, canciones y fotos del sitio y las escribe en esta
 * misma planilla.
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
