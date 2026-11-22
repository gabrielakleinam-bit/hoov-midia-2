#!/usr/bin/env python3
"""Teste de equivalência: compara slides renderizados com os aprovados.
Uso: python3 compare.py dir_novo dir_aprovado [limite_ssim=0.92]"""
import sys, pathlib, numpy as np
from PIL import Image
try:
    from skimage.metrics import structural_similarity as ssim
except ImportError:
    ssim = None
new, ref = map(pathlib.Path, sys.argv[1:3]); lim = float(sys.argv[3]) if len(sys.argv) > 3 else 0.92
ok = True
for r in sorted(ref.glob("slide-*.png"), key=lambda p: int(p.stem.split("-")[1])):
    n = new / r.name
    if not n.exists(): print(r.name, "FALTA"); ok = False; continue
    a = np.array(Image.open(n).convert("L")); b = np.array(Image.open(r).convert("L"))
    if a.shape != b.shape: print(r.name, "TAMANHO", a.shape, b.shape); ok = False; continue
    s = ssim(a, b) if ssim else 1 - np.abs(a.astype(float) - b).mean() / 255
    print(f"{r.name}: {'OK' if s >= lim else 'FALHA'} ssim={s:.4f}"); ok &= s >= lim
sys.exit(0 if ok else 1)
