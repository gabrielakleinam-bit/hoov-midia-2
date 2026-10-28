#!/usr/bin/env python3
"""
humanize.py - tira a digital de maquina de um rascunho em portugues.

Adaptado para PT-BR a partir de instagram-agent-skill (MIT, Jake Schincariol).

Tres passadas, nesta ordem:

  1. INVISIVEIS   apaga ou normaliza caracteres que teclado de gente nao
                  produz: espaco de largura zero, juntores, hifen suave, BOM,
                  caracteres de tag Unicode, espacos nao separaveis. Eles
                  sobrevivem ao copiar e colar e sao a marca mais mecanica de
                  texto gerado.
  2. TIPOGRAFIA   travessao vira virgula, meia-risca vira hifen, aspas curvas
                  viram retas, reticencias de um caractere viram tres pontos.
  3. LEXICO       troca o vocabulario de vicios.json por portugues simples,
                  preservando maiusculas e sem mexer em links.

Estruturas (triade, "nao e so X, e Y", parede de hashtag, urgencia falsa) sao
APONTADAS, nunca reescritas: mudar o formato de uma frase pede julgamento,
entao isso e trabalho do modelo, nao de um regex.

Uso
  python3 humanize.py rascunho.txt
  python3 humanize.py rascunho.txt --report
  python3 humanize.py rascunho.txt -o limpo.txt
  python3 humanize.py rascunho.txt --json
"""

import argparse
import json
import os
import re
import sys
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
LEX = os.path.join(HERE, "vicios.json")

URL_RE = re.compile(r"https?://\S+|www\.\S+|\S+@\S+\.\S+|@[\w.]+|#\w+")
SENT_RE = re.compile(r"[^.!?\n]+[.!?]*")
LETTER = "A-Za-zÀ-ÖØ-öø-ÿ"


def load_lexicon(path=LEX):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _cp(spec):
    if "-" in spec:
        a, b = spec.split("-")
        return (int(a[2:], 16), int(b[2:], 16))
    return int(spec[2:], 16)


def protect(text):
    """Troca links, @menções e #hashtags por marcadores para nenhuma passada mexer neles."""
    found = []

    def stash(m):
        found.append(m.group(0))
        return f"\x00URL{len(found) - 1}\x00"

    return URL_RE.sub(stash, text), found


def restore(text, found):
    for i, url in enumerate(found):
        text = text.replace(f"\x00URL{i}\x00", url)
    return text


def pass_invisible(text, lex):
    hits = []
    for entry in lex["invisible"]:
        cp = _cp(entry["cp"])
        if isinstance(cp, tuple):
            pattern = "[" + re.escape(chr(cp[0])) + "-" + re.escape(chr(cp[1])) + "]"
        else:
            pattern = re.escape(chr(cp))
        n = len(re.findall(pattern, text))
        if n:
            hits.append({"name": entry["cp"] + " " + entry["name"], "count": n,
                         "action": "apagar" if entry["action"] == "delete" else "virar espaço"})
            text = re.sub(pattern, "" if entry["action"] == "delete" else " ", text)
    stray = [c for c in text if unicodedata.category(c) == "Cf" and c != "\x00"]
    if stray:
        hits.append({"name": "outros caracteres invisíveis de formatação", "count": len(stray),
                     "action": "apagar"})
        text = "".join(c for c in text if unicodedata.category(c) != "Cf" or c == "\x00")
    return text, hits


def pass_typographic(text, lex):
    hits = []
    for entry in lex["typographic"]:
        ch = entry["from"]
        n = text.count(ch)
        if not n:
            continue
        hits.append({"name": f"{ch} {entry['name']}", "count": n, "to": entry["to"].strip() or "(espaço)"})
        if ch == "—":
            text = re.sub(r"\s*—\s*", ", ", text)
        elif ch == "–":
            text = re.sub(r"\s*–\s*(?=\d)", "-", text)
            text = re.sub(r"\s+–\s+", ", ", text)
            text = text.replace("–", "-")
        else:
            text = text.replace(ch, entry["to"])
    text = re.sub(r",\s*([,.;:!?])", r"\1", text)
    text = re.sub(r",\s*\n", "\n", text)
    text = re.sub(r"(?m)^\s*,\s*", "", text)
    return text, hits


def _match_case(src, repl):
    if not repl:
        return repl
    if src.isupper() and len(src) > 1:
        return repl.upper()
    if src[0].isupper():
        return repl[0].upper() + repl[1:]
    return repl


def pass_lexical(text, lex):
    """Troca vicios. Mais longo primeiro, para expressao ganhar de palavra."""
    hits = []
    entries = sorted(lex["phrases"] + lex["words"], key=lambda e: len(e["find"]), reverse=True)
    for entry in entries:
        find = entry["find"]
        pattern = re.compile(rf"(?<![{LETTER}])" + re.escape(find).replace(r"\ ", r"\s+") + rf"(?![{LETTER}])",
                             re.IGNORECASE)
        found = pattern.findall(text)
        if not found:
            continue
        hits.append({"find": find, "replace": entry["replace"] or "(apagado)",
                     "count": len(found), "family": entry["family"]})
        text = pattern.sub(lambda m: _match_case(m.group(0), entry["replace"]), text)
    # Limpeza depois de apagar: pontuacao orfa, espaco duplo, linha que
    # agora comeca em virgula.
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"(?m)^[ \t]*(?:[,.;:!?]+[ \t]*)+", "", text)
    text = re.sub(r"(?m)^[ \t](?=\S)", "", text)
    text = re.sub(r"[ \t]+([,.;:!?])", r"\1", text)
    text = re.sub(r",\s*([,.;:!?])", r"\1", text)
    text = text.replace("...", "\x01ELL\x01")
    text = re.sub(r"\.\s*\.+", ".", text)
    text = re.sub(r"([!?])\s*\.", r"\1", text)
    text = text.replace("\x01ELL\x01", "...")
    text = re.sub(r"(?m)^[ \t]+$", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Travessao que virou virgula seguido de conectivo vira ponto final.
    text = re.sub(r",\s*(também|então|ainda|basicamente|no fim)\s*,\s*",
                  lambda m: ". " + m.group(1)[0].upper() + m.group(1)[1:] + ", ", text)
    return text, hits


def scan_structures(text, lex):
    flags = []
    for s in lex["structures"]:
        try:
            pattern = re.compile(s["regex"], re.MULTILINE)
        except re.error:
            continue
        found = pattern.findall(text)
        if found:
            flags.append({"name": s["name"], "count": len(found), "fix": s["fix"]})
    lens = [len(s.split()) for s in SENT_RE.findall(text) if len(s.split()) > 2]
    if len(lens) >= 4:
        mean = sum(lens) / len(lens)
        var = sum((n - mean) ** 2 for n in lens) / len(lens)
        cv = (var ** 0.5) / mean if mean else 0
        if cv < 0.35:
            flags.append({"name": f"Frases do mesmo tamanho (variação {cv:.2f})".replace(".", ","),
                          "count": len(lens),
                          "fix": "Quebre uma frase no meio. Deixe outra correr longa. Máquina escreve por igual."})
    return flags


def restore_capitals(original, text):
    """Apagar uma abertura deixa a palavra seguinte em minuscula.

    So corrige para quem escreve com maiuscula no comeco de frase: voz toda em
    minuscula e estilo, nao defeito.
    """
    starts = re.findall(rf"(?:^|[.!?]\s+|\n)\s*([{LETTER}])", original)
    if not starts or sum(1 for c in starts if c.isupper()) * 2 < len(starts):
        return text
    return re.sub(r"(?:^|(?<=[.!?] )|(?<=[.!?]\n)|(?<=\n))\s*([a-zà-ÿ])",
                  lambda m: m.group(0)[:-1] + m.group(1).upper(), text)


def humanize(text, lex):
    raw_for_case = text
    text, urls = protect(text)
    text, inv = pass_invisible(text, lex)
    text, typo = pass_typographic(text, lex)
    text, lexi = pass_lexical(text, lex)
    text = restore_capitals(raw_for_case, text)
    text = restore(text, urls)
    return text.strip() + "\n", {"invisible": inv, "typographic": typo, "lexical": lexi,
                                 "structures": scan_structures(text, lex)}


def render_report(report, out=sys.stderr):
    def head(title):
        print(f"\n{title}\n" + "-" * len(title), file=out)

    total = sum(h["count"] for k in ("invisible", "typographic", "lexical") for h in report[k])
    head("RELATÓRIO DO HUMANIZADOR")
    print(f"{total} marcas de máquina removidas, "
          f"{len(report['structures'])} estrutura(s) apontada(s) para reescrever", file=out)
    if report["invisible"]:
        head("1. CARACTERES INVISÍVEIS")
        for h in report["invisible"]:
            print(f"  {h['count']:>3}x  {h['name']}  -> {h['action']}", file=out)
    if report["typographic"]:
        head("2. TIPOGRAFIA")
        for h in report["typographic"]:
            print(f"  {h['count']:>3}x  {h['name']}  -> {h['to']}", file=out)
    if report["lexical"]:
        head("3. VÍCIOS DE VOCABULÁRIO")
        for h in report["lexical"]:
            print(f"  {h['count']:>3}x  {h['find']}  -> {h['replace']}   [{h['family']}]", file=out)
    if report["structures"]:
        head("4. ESTRUTURAS  (não corrigidas sozinhas - reescreva você)")
        for h in report["structures"]:
            print(f"  {h['count']:>3}x  {h['name']}\n        {h['fix']}", file=out)
    if not any(report.values()):
        head("LIMPO")
        print("  Nada para tirar.", file=out)
    print("", file=out)


def main():
    ap = argparse.ArgumentParser(description="Tira a digital de máquina de um rascunho em PT-BR.")
    ap.add_argument("input", nargs="?", default="-", help="arquivo, ou -")
    ap.add_argument("-o", "--out", help="grava o texto limpo aqui")
    ap.add_argument("--report", action="store_true", help="mostra o que mudou")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--lexicon", default=LEX, help="caminho do vicios.json")
    args = ap.parse_args()

    raw = sys.stdin.read() if args.input == "-" else open(args.input, encoding="utf-8").read()
    lex = load_lexicon(args.lexicon)
    clean, report = humanize(raw, lex)
    if args.json:
        print(json.dumps({"text": clean, "report": report}, indent=2, ensure_ascii=False))
        return
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(clean)
        print(f"gravado em {args.out}", file=sys.stderr)
    else:
        sys.stdout.write(clean)
    if args.report:
        render_report(report)


if __name__ == "__main__":
    main()
