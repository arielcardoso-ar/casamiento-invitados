#!/bin/bash
# Pinguea el sitio para que Render (free tier) no lo escale a cero.
#
# Sin esto, el servicio se duerme a los 15 minutos sin tráfico y la próxima
# visita —un invitado abriendo el link— tarda ~45s en levantar. Este script
# no reemplaza eso del todo (si el Mac está apagado, el sitio igual duerme),
# pero mientras corre en esta máquina lo mantiene despierto.
#
# Se invoca desde launchd (ver com.casamiento.keepalive.plist), no a mano.

set -u
URL="https://casamiento-katherine-ariel.onrender.com/healthz"
LOG="$HOME/Library/Logs/casamiento-keepalive.log"

marca="$(date '+%Y-%m-%d %H:%M:%S')"
codigo="$(curl -s -o /dev/null -w '%{http_code}' -m 60 "$URL")"
echo "$marca  $codigo" >> "$LOG"

# El log es de una sola línea por ping: no hace falta que crezca sin límite.
tail -n 500 "$LOG" > "$LOG.tmp" && mv "$LOG.tmp" "$LOG"
