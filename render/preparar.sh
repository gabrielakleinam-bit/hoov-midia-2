#!/usr/bin/env bash
# Prepara o ambiente do renderizador numa chamada só (idempotente, saída de 1 linha).
# Uso: bash render/preparar.sh
set -u
falta=""
python3 -c "import numpy, scipy, playwright" 2>/dev/null || pip install -q --break-system-packages numpy scipy playwright >/dev/null 2>&1
python3 -c "import numpy, scipy, playwright" 2>/dev/null || falta="$falta pip(numpy/scipy/playwright)"
if ! python3 - <<'PY' 2>/dev/null
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    p.chromium.launch().close()
PY
then
  timeout 400 python3 -m playwright install chromium >/dev/null 2>&1
  python3 - <<'PY' 2>/dev/null || falta="$falta chromium"
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    p.chromium.launch().close()
PY
fi
command -v ffmpeg >/dev/null || falta="$falta ffmpeg"
command -v ffprobe >/dev/null || falta="$falta ffprobe"
whisper=sem-whisper
python3 -c "import faster_whisper" 2>/dev/null && whisper=faster-whisper
piper=sem-piper
(command -v piper >/dev/null || python3 -c "import piper" 2>/dev/null) && piper=piper
if [ -n "$falta" ]; then echo "FALTA:$falta | $whisper $piper"; exit 1; fi
echo "OK | $whisper $piper"
