#!/usr/bin/env bash
# Convert one reviewed worksheet into website data, then validate it.
# Usage: pipeline/build.sh worksheets/17SHM_v6.docx 17SHM "Oscillations: Simple Harmonic Motion"
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"; root="$(dirname "$here")"
[ -d "$here/node_modules/katex" ] || (cd "$here" && npm install --silent)
python3 -I "$here/parse_worksheet.py" "$1" "$2" "$root/site/data" "$3"
node "$here/validate.js" "$root/site/data/$2.json"
