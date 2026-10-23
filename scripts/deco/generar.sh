#!/bin/zsh
# Uso: scripts/deco/generar.sh && python3 scripts/deco/procesar.py static/img/deco
# Los originales quedan en scripts/deco/raw/ (no se versionan).
# Genera cada fila de prompts.tsv: nombre, ancho, alto, semilla, prompt.
cd "${0:A:h}"; mkdir -p raw
while IFS=$'\t' read -r nombre w h seed prompt; do
  out="raw/${nombre}-${seed}.png"
  [[ -f $out ]] && continue
  echo "== $out"
  mflux-generate-z-image-turbo --quantize 8 --low-ram --steps 9 \
    --width $w --height $h --seed $seed --prompt "$prompt" --output "$out" 2>&1 | grep -E "saved|Error|error"
done < prompts.tsv
