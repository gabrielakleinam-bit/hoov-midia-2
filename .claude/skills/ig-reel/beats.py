#!/usr/bin/env python3
"""
beats.py - transforma o roteiro de um Reel em mapa de tempos antes de gravar.

Adaptado para PT-BR a partir de instagram-agent-skill (MIT, Jake Schincariol).

Estima quanto tempo cada linha leva para ser falada, empilha em minutagem e
aponta as quatro coisas que matam um Reel na edicao: gancho que passa dos 3
segundos, trecho longo o bastante para a pessoa sair, sequencia de linhas sem
nada concreto e duracao diferente da que voce disse que queria.

O tempo e estimado por contagem de palavras. Portugues falado fica perto de
150 palavras por minuto, com numero por extenso contando mais (R$ 45.900 se
fala "quarenta e cinco mil e novecentos"). Cronometre voce lendo um roteiro e
ajuste com --wpm.

Uso
  python3 beats.py roteiro.txt
  python3 beats.py roteiro.txt --target 15
  python3 beats.py roteiro.txt --wpm 165 --target 30
  python3 beats.py roteiro.txt --json
"""

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ptbr import concrete_markers, words  # noqa: E402

SENT_RE = re.compile(r"[^.!?]+[.!?]*")
STOPWORDS = {
    "o", "a", "os", "as", "um", "uma", "uns", "umas", "e", "ou", "mas", "se",
    "de", "do", "da", "dos", "das", "em", "no", "na", "nos", "nas", "por",
    "pra", "para", "pro", "com", "que", "isso", "esse", "essa", "este", "esta",
    "aqui", "ele", "ela", "é", "são", "foi", "era", "ser", "estar", "está",
    "tá", "você", "voce", "vc", "seu", "sua", "eu", "meu", "minha", "me",
    "nós", "a gente", "eles", "elas", "só", "não", "nao", "já", "tem", "ter",
    "vai", "vou", "faz", "fez", "como", "mais", "menos", "muito", "quando",
    "também", "então", "aí", "lá", "ao", "à", "pelo", "pela", "sem", "até",
}

HOOK_WINDOW = 3.0        # segundos. Depois disso o dedo ja decidiu.
MAX_BEAT = 4.0           # segundos numa ideia sem mudar nada na tela.
ABSTRACT_RUN = 3         # trechos seguidos sem nada checavel.


def tc(seconds):
    m, s = divmod(seconds, 60)
    return f"{int(m)}:{s:04.1f}".replace(".", ",")


def split_beats(raw, wps):
    """Uma linha e um trecho, a nao ser que seja longa demais para isso."""
    beats = []
    for line in [l.strip() for l in raw.splitlines()]:
        if not line:
            continue
        if len(words(line)) / wps <= MAX_BEAT * 1.5:
            beats.append(line)
            continue
        parts = [p.strip() for p in SENT_RE.findall(line) if p.strip()]
        buf = ""
        for part in parts:
            candidate = (buf + " " + part).strip()
            if buf and len(words(candidate)) / wps > MAX_BEAT:
                beats.append(buf)
                buf = part
            else:
                buf = candidate
        if buf:
            beats.append(buf)
    return beats


def analyse(raw, wpm=150, target=None):
    wps = wpm / 60.0
    beats = split_beats(raw, wps)
    if not beats:
        return None

    rows, clock = [], 0.0
    for i, text in enumerate(beats):
        n = len(words(text))
        dur = n / wps
        rows.append({"n": i + 1, "start": round(clock, 2), "dur": round(dur, 2), "words": n,
                     "text": text, "concrete": len(concrete_markers(text)), "label": "",
                     "flags": []})
        clock += dur
    total = clock

    for r in rows:
        if r["n"] == 1 or r["start"] + r["dur"] <= HOOK_WINDOW:
            r["label"] = "GANCHO"
    rows[-1]["label"] = "CTA" if rows[-1]["label"] != "GANCHO" else "GANCHO/CTA"
    half = total / 2
    for r in rows:
        if not r["label"] and r["start"] <= half < r["start"] + r["dur"]:
            r["label"] = "MEIO"

    notes = []
    if rows[0]["dur"] > HOOK_WINDOW:
        rows[0]["flags"].append(f"gancho leva {rows[0]['dur']:.1f}s, passou dos {HOOK_WINDOW:.0f}s")
        notes.append(f"O trecho 1 leva {rows[0]['dur']:.1f}s para ser falado. Corte para "
                     f"{int(HOOK_WINDOW * wps)} palavras ou menos, ou o gancho chega depois "
                     "que a decisão já foi tomada.")
    if rows[0]["concrete"] == 0:
        notes.append("O trecho 1 não tem número, modelo nem nome. Gancho sem nada checável "
                     "é o que mais passa batido.")

    for r in rows:
        if r["dur"] > MAX_BEAT:
            r["flags"].append(f"{r['dur']:.1f}s num trecho só")
    long_beats = [r["n"] for r in rows if r["dur"] > MAX_BEAT]
    if long_beats:
        notes.append(f"Trecho(s) {', '.join(map(str, long_beats))} passam de {MAX_BEAT:.0f}s. "
                     "Quebre a frase ou mude o que está na tela dentro dele. "
                     "Quadro parado é onde as pessoas saem.")

    run, start = 0, None
    for r in rows:
        if r["concrete"] == 0:
            run += 1
            start = start if start is not None else r["n"]
            if run == ABSTRACT_RUN:
                notes.append(f"Trechos {start}-{r['n']} não têm nada concreto. Coloque um "
                             "preço, um modelo, um km ou um tempo no ar em um deles.")
        else:
            run, start = 0, None

    first = {w.lower() for w in words(rows[0]["text"]) if w.lower() not in STOPWORDS}
    last = {w.lower() for w in words(rows[-1]["text"]) if w.lower() not in STOPWORDS}
    loop = sorted(first & last)
    if loop:
        notes.append(f"Loop: o último trecho repete \"{', '.join(loop[:3])}\" do gancho. "
                     "A segunda visualização é alcance de graça.")
    else:
        notes.append("Sem loop. O último trecho não repete nenhuma palavra do gancho, então o "
                     "vídeo termina chapado. Ecoar uma palavra do trecho 1 é o replay mais barato.")

    if target:
        delta = total - target
        if abs(delta) <= target * 0.1:
            notes.append(f"Duração no alvo ({total:.1f}s para {target:.0f}s).")
        elif delta > 0:
            notes.append(f"{delta:.1f}s acima do alvo. Corte umas {int(delta * wps)} palavras.")
        else:
            notes.append(f"{-delta:.1f}s abaixo do alvo. Acrescente {int(-delta * wps)} palavras "
                         "ou grave curto. Curto costuma ser o certo.")

    return {"wpm": wpm, "target": target, "total_seconds": round(total, 2),
            "total_words": sum(r["words"] for r in rows), "beats": rows, "notes": notes}


def render(a, out=sys.stdout):
    head = (f"MAPA DE TEMPOS  ·  {a['total_words']} palavras  ·  ~{a['total_seconds']:.1f}s "
            f"a {a['wpm']:.0f} ppm" + (f"  ·  alvo {a['target']:.0f}s" if a["target"] else ""))
    print("\n" + head, file=out)
    print("=" * max(len(head), 72), file=out)
    for r in a["beats"]:
        label = f"{r['label']:<11}" if r["label"] else " " * 11
        print(f"  {tc(r['start'])}  {r['dur']:4.1f}s  {label}{r['text']}", file=out)
        for f in r["flags"]:
            print(f"  {'':>6}  {'':>5}  {'':<11}^ {f}", file=out)
    print("-" * max(len(head), 72), file=out)
    for n in a["notes"]:
        print(f"  - {n}", file=out)
    print("", file=out)


def main():
    ap = argparse.ArgumentParser(description="Mapa de tempos de um roteiro de Reel.")
    ap.add_argument("input", nargs="?", default="-", help="arquivo do roteiro, ou -")
    ap.add_argument("--wpm", type=float, default=150, help="palavras por minuto (padrão 150)")
    ap.add_argument("--target", type=float, help="duração alvo em segundos")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    raw = sys.stdin.read() if args.input == "-" else open(args.input, encoding="utf-8").read()
    a = analyse(raw, wpm=args.wpm, target=args.target)
    if not a:
        print("roteiro vazio", file=sys.stderr)
        sys.exit(2)
    if args.json:
        print(json.dumps(a, indent=2, ensure_ascii=False))
    else:
        render(a)


if __name__ == "__main__":
    main()
