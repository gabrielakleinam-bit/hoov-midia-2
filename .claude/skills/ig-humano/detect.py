#!/usr/bin/env python3
"""
detect.py - painel de cinco checagens que mede o quanto um rascunho em
portugues parece escrito por maquina.

Adaptado para PT-BR a partir de instagram-agent-skill (MIT, Jake Schincariol).

O que isto e:  cinco heuristicas locais, inspiradas nos sinais que detectores
publicos medem: variacao do tamanho das frases, coisa concreta, vocabulario de
vicio, digital tipografica e voz. Tudo roda na sua maquina, nada e enviado.

O que isto NAO e:  GPTZero, Originality, Copyleaks ou Turnitin. Nao chama
nenhum deles e nao promete o veredito deles. Mede as mesmas coisas de fundo,
e por isso corrigir o que ele aponta tende a mexer nesses numeros tambem.

A checagem VOZ foi ajustada para portugues: no lugar das contracoes do ingles
(don't, it's), conta as marcas de fala brasileira (pra, tá, né, a gente, aí).

Cada checagem devolve nota HUMANA de 0 a 100. Maior e melhor.

Uso
  python3 detect.py rascunho.txt
  python3 detect.py antes.txt depois.txt      # compara dois rascunhos
  python3 detect.py rascunho.txt --json
"""

import argparse
import json
import os
import re
import statistics
import sys
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ptbr import concrete_markers  # noqa: E402

LEX = os.path.join(HERE, "vicios.json")
LETTER = "A-Za-zÀ-ÖØ-öø-ÿ"

SENT_RE = re.compile(r"[^.!?\n]+[.!?]*")
WORD_RE = re.compile(rf"[{LETTER}']+")
SPEECH = re.compile(r"(?i)\b(?:pra|pro|pros|pras|tá|tô|tão|tava|tavam|né|cê|vc|vcs|a gente|aí|daí|bora|tipo|beleza|cara|mano|tranquilo|pô)\b")
PRONOUNS = re.compile(r"(?i)\b(?:eu|me|mim|meu|minha|meus|minhas|nós|nosso|nossa|a gente|você|vocês|seu|sua|seus|suas|te|teu|tua|vc|vcs)\b")
LEX_BOUND = (rf"(?<![{LETTER}])", rf"(?![{LETTER}])")


def clamp(n):
    return max(0.0, min(100.0, n))


def scale(value, human, machine):
    if human == machine:
        return 50.0
    return clamp((value - machine) / (human - machine) * 100)


def sentences(text):
    return [s.strip() for s in SENT_RE.findall(text) if len(s.split()) > 2]


def words(text):
    return WORD_RE.findall(text)


def check_burstiness(text):
    """Gente varia muito o tamanho da frase. Modelo escreve por igual."""
    lens = [len(s.split()) for s in sentences(text)]
    if len(lens) < 4:
        return 50.0, "curto demais para julgar"
    mean = statistics.mean(lens)
    cv = statistics.pstdev(lens) / mean if mean else 0
    return scale(cv, human=0.70, machine=0.22), \
        f"variação {cv:.2f} em {len(lens)} frases (ideal 0,55+)".replace("0.", "0,")


def check_specificity(text):
    """Numero, preco, modelo, cidade. Vicio e abstrato."""
    w = words(text)
    if len(w) < 25:
        return 50.0, "curto demais para julgar"
    hits = len(concrete_markers(text))
    density = hits * 100 / len(w)
    return scale(density, human=6.0, machine=0.5), \
        f"{hits} marcadores concretos, {density:.1f} a cada 100 palavras (ideal 4+)".replace(".", ",", 1)


def check_slop(text, lex):
    w = words(text)
    if not w:
        return 50.0, "vazio"
    hits, found = 0, []
    for entry in lex["words"] + lex["phrases"]:
        pattern = re.compile(LEX_BOUND[0] + re.escape(entry["find"]).replace(r"\ ", r"\s+") + LEX_BOUND[1],
                             re.IGNORECASE)
        n = len(pattern.findall(text))
        if n:
            hits += n
            found.append(entry["find"])
    density = hits * 100 / len(w)
    detail = f"{hits} vícios, {density:.1f} a cada 100 palavras".replace(".", ",")
    if found:
        detail += " (" + ", ".join(sorted(found)[:4]) + (", ..." if len(found) > 4 else "") + ")"
    return scale(density, human=0.0, machine=4.0), detail


def check_fingerprint(text):
    """Caracteres que teclado de celular nao produz."""
    invisible = sum(1 for c in text if unicodedata.category(c) == "Cf")
    em = text.count("—")
    curly = sum(text.count(c) for c in "‘’“”")
    ellip = text.count("…")
    nbsp = sum(text.count(c) for c in "   ")
    total = invisible * 4 + em * 2 + curly + ellip + nbsp
    per1k = total * 1000 / max(len(text), 1)
    return scale(per1k, human=0.0, machine=12.0), \
        (f"{invisible} invisível(is), {em} travessão, {curly} aspa curva, "
         f"{ellip} reticências de um caractere, {nbsp} espaço rígido")


def check_voice(text, lex):
    """Marca de fala, pessoa e os formatos que modelo prefere."""
    w = words(text)
    if len(w) < 25:
        return 50.0, "curto demais para julgar"
    per100 = 100 / len(w)
    speech = len(SPEECH.findall(text)) * per100
    person = len(PRONOUNS.findall(text)) * per100
    tells, names = 0, []
    for s in lex["structures"]:
        try:
            n = len(re.compile(s["regex"], re.MULTILINE).findall(text))
        except re.error:
            continue
        if n:
            tells += n
            names.append(s["id"])
    bullets = [len(b.split()) for b in re.findall(r"(?m)^\s*[-*•]\s+(.+)$", text)]
    uniform = len(bullets) >= 3 and statistics.pstdev(bullets) < 1.6
    score = (scale(speech, human=3.0, machine=0.0) * 0.35
             + scale(person, human=8.0, machine=1.0) * 0.35
             + clamp(100 - tells * 22) * 0.30)
    if uniform:
        score -= 12
        names.append("lista-uniforme")
    detail = (f"{speech:.1f} marcas de fala, {person:.1f} pronomes pessoais a cada 100 palavras, "
              f"{tells} estrutura(s)").replace(".", ",")
    if names:
        detail += " [" + ", ".join(names[:4]) + "]"
    return clamp(score), detail


CHECKS = ["RITMO", "CONCRETO", "VÍCIOS", "DIGITAL", "VOZ"]


def run(text, lex):
    results = {"RITMO": check_burstiness(text), "CONCRETO": check_specificity(text),
               "VÍCIOS": check_slop(text, lex), "DIGITAL": check_fingerprint(text),
               "VOZ": check_voice(text, lex)}
    scores = [results[c][0] for c in CHECKS]
    overall = statistics.mean(scores) * 0.6 + min(scores) * 0.4
    verdict = "APROVADO" if overall >= 70 and min(scores) >= 55 else (
        "REVISAR" if overall >= 50 else "REPROVADO")
    return results, overall, verdict


def bar(score, width=24):
    filled = round(score / 100 * width)
    return "#" * filled + "." * (width - filled)


def render(results, overall, verdict, label=None, out=sys.stdout):
    title = "PAINEL DE TEXTO DE MÁQUINA" + (f"  -  {label}" if label else "")
    print("\n" + title, file=out)
    print("=" * max(len(title), 62), file=out)
    for name in CHECKS:
        score, detail = results[name]
        print(f"  {name:<13} {bar(score)} {score:5.1f}", file=out)
        print(f"  {'':<13} {detail}", file=out)
    print("-" * 62, file=out)
    print(f"  {'NOTA HUMANA':<13} {bar(overall)} {overall:5.1f}   {verdict}", file=out)
    if verdict != "APROVADO":
        weakest = min(CHECKS, key=lambda c: results[c][0])
        print(f"\n  Sinal mais fraco: {weakest}. Corrija esse primeiro.", file=out)
    print("", file=out)


def main():
    ap = argparse.ArgumentParser(description="Mede o quanto um rascunho em PT-BR parece de máquina.")
    ap.add_argument("input", nargs="?", default="-", help="arquivo, ou -")
    ap.add_argument("compare", nargs="?", help="segundo arquivo, para antes/depois")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--lexicon", default=LEX)
    args = ap.parse_args()

    lex = json.load(open(args.lexicon, encoding="utf-8"))
    read = lambda p: sys.stdin.read() if p == "-" else open(p, encoding="utf-8").read()  # noqa: E731
    targets = [(args.input, read(args.input))]
    if args.compare:
        targets.append((args.compare, read(args.compare)))

    payload = []
    for name, text in targets:
        results, overall, verdict = run(text, lex)
        payload.append({"source": name,
                        "checks": {k: {"score": round(v[0], 1), "detail": v[1]} for k, v in results.items()},
                        "human_score": round(overall, 1), "verdict": verdict})
    if args.json:
        print(json.dumps(payload if args.compare else payload[0], indent=2, ensure_ascii=False))
        return
    for (name, text), p in zip(targets, payload):
        render(*run(text, lex), label=os.path.basename(name) if args.compare else None)
    if args.compare:
        a, b = payload
        print(f"  {a['human_score']:.1f} {a['verdict']}  ->  {b['human_score']:.1f} {b['verdict']}"
              f"   ({b['human_score'] - a['human_score']:+.1f})\n")
    sys.exit(0 if payload[-1]["verdict"] == "APROVADO" else 1)


if __name__ == "__main__":
    main()
