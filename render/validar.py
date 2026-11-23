#!/usr/bin/env python3
"""Validação única de vídeo Hoov (story ou reel): uma chamada no lugar de ffprobe + ffmpeg + contagem manual.

Uso:
  python3 -I render/validar.py VIDEO.mp4 --tipo story|reel [--folha folha.png] [--narracao "texto falado"]

Saída: UMA linha JSON {"ok": bool, "erros": [...], "info": {...}, "folha": "caminho"}.
Gera UMA folha de contato (miniaturas) para o Claude abrir com Read, em vez de vários quadros.
Exit code 0 = ok, 1 = erro de checagem. Não altera o vídeo.
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

LIMITES = {"story": (6.0, 15.5), "reel": (15.0, 60.0)}  # segundos
PALAVRAS_MAX = {"story": 20, "reel": 90}


def sh(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def probe(video):
    r = sh(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", video])
    if r.returncode != 0:
        raise SystemExit(json.dumps({"ok": False, "erros": ["ffprobe falhou: " + r.stderr[-200:]]}))
    return json.loads(r.stdout)


def lufs(video):
    r = sh(["ffmpeg", "-nostats", "-hide_banner", "-i", video, "-af", "ebur128=peak=true", "-f", "null", "-"])
    m = re.findall(r"I:\s+(-?\d+(?:\.\d+)?)\s+LUFS", r.stderr)
    return float(m[-1]) if m else None


def folha(video, dur, tipo, saida):
    n = 6 if tipo == "story" else 12
    if tipo == "story":
        tempos = [0.5, dur / 2, max(dur - 1.0, 0.6)]
        tempos = sorted({round(t, 2) for t in tempos})
    else:
        tempos = [round(dur * (i + 0.5) / n, 2) for i in range(n)]
    tmp = Path(saida).with_suffix("")
    imgs = []
    for i, t in enumerate(tempos):
        p = f"{tmp}_{i}.png"
        r = sh(["ffmpeg", "-y", "-v", "error", "-ss", str(t), "-i", video, "-frames:v", "1",
                "-vf", "scale=270:480", p])
        if r.returncode == 0 and Path(p).exists():
            imgs.append(p)
    if not imgs:
        return None
    cols = min(len(imgs), 6)
    rows = (len(imgs) + cols - 1) // cols
    cmd = ["ffmpeg", "-y", "-v", "error"]
    for p in imgs:
        cmd += ["-i", p]
    entradas = "".join(f"[{i}:v]" for i in range(len(imgs)))
    if len(imgs) == 1:
        cmd += ["-frames:v", "1", saida]
    else:
        layout = "|".join(f"{(i % cols) * 270}_{(i // cols) * 480}" for i in range(len(imgs)))
        cmd += ["-filter_complex", f"{entradas}xstack=inputs={len(imgs)}:layout={layout}", "-frames:v", "1", saida]
    sh(cmd)
    for p in imgs:
        Path(p).unlink(missing_ok=True)
    return saida if Path(saida).exists() else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--tipo", choices=["story", "reel"], required=True)
    ap.add_argument("--folha", default="folha.png")
    ap.add_argument("--narracao", default=None, help="texto falado, para contar palavras")
    a = ap.parse_args()

    erros = []
    info = probe(a.video)
    v = next((s for s in info["streams"] if s["codec_type"] == "video"), None)
    au = next((s for s in info["streams"] if s["codec_type"] == "audio"), None)
    dur = float(info["format"].get("duration", 0))
    out = {"duracao_s": round(dur, 2)}

    if not v:
        erros.append("sem trilha de vídeo")
    else:
        out["res"] = f'{v["width"]}x{v["height"]}'
        out["codec"] = v["codec_name"]
        num, _, den = v.get("r_frame_rate", "0/1").partition("/")
        fps = float(num) / float(den or 1) if float(den or 1) else 0
        out["fps"] = round(fps, 2)
        if (v["width"], v["height"]) != (1080, 1920):
            erros.append(f'resolução {out["res"]} (esperado 1080x1920)')
        if v["codec_name"] != "h264":
            erros.append(f'codec {v["codec_name"]} (esperado h264)')
        if not 29 <= fps <= 31:
            erros.append(f"fps {fps:.1f} (esperado 30)")
    if not au:
        erros.append("SEM trilha de áudio")
    else:
        out["audio"] = f'{au["codec_name"]} {au.get("sample_rate", "?")}Hz'
        l = lufs(a.video)
        out["lufs"] = l
        if l is None or not -17.0 <= l <= -11.0:
            erros.append(f"loudness {l} LUFS fora de -17..-11 (alvo -14)")
    lo, hi = LIMITES[a.tipo]
    if not lo <= dur <= hi:
        erros.append(f"duração {dur:.1f}s fora de {lo:.0f}-{hi:.0f}s para {a.tipo}")
    if a.narracao is not None:
        n = len(re.findall(r"\w+", a.narracao, flags=re.UNICODE))
        out["palavras_narracao"] = n
        if n > PALAVRAS_MAX[a.tipo]:
            erros.append(f"narração com {n} palavras (máx. {PALAVRAS_MAX[a.tipo]})")

    f = folha(a.video, dur, a.tipo, a.folha) if dur > 0 else None
    res = {"ok": not erros, "erros": erros, "info": out, "folha": f}
    print(json.dumps(res, ensure_ascii=False))
    sys.exit(0 if not erros else 1)


if __name__ == "__main__":
    main()
