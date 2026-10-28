#!/usr/bin/env python3
"""
legenda.py - revisa uma legenda de Instagram em portugues e mostra exatamente
o que o feed mostra antes do "... mais".

Adaptado para PT-BR e para a Hoov a partir de instagram-agent-skill (MIT,
Jake Schincariol).

O Instagram mostra cerca de 125 caracteres da legenda no feed e esconde o
resto atras de um toque. Quase toda legenda que falha, falha ali. Este script
imprime essa janela numa caixa e roda as checagens que valem a pena, mais tres
da Hoov:

  FIPE COM MES     legenda que fala em FIPE com preco ou % precisa dizer o mes
                   de referencia. Sem isso, o primeiro comentario derruba o post.
  AVISO CONFIRA    desvio de 30% ou mais abaixo da FIPE precisa de aviso de
                   seguranca (golpe e sinistro tambem parecem otimo negocio).
  SINALEIRO        com --preco e --fipe, calcula a faixa de 4 cores do
                   business case e confere se a legenda diz a mesma coisa.

Limite de hashtags: 5 por post, desde 18/dez/2025.

Uso
  python3 legenda.py legenda.txt
  python3 legenda.py legenda.txt --keywords "hb20 usado,carro abaixo da fipe"
  python3 legenda.py legenda.txt --preco 45100 --fipe 52400
  python3 legenda.py legenda.txt --json
"""

import argparse
import json
import os
import re
import sys
import textwrap

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ptbr import HASHTAG_RE, concrete_markers  # noqa: E402

LIMIT = 2200
TRUNCATE = 125
HASHTAG_LIMIT = 5
CONFIRA_THRESHOLD = 0.30

MENTION_RE = re.compile(r"(?:^|\s)(@[A-Za-z0-9_.]+)")
LINK_RE = re.compile(r"https?://\S+|\bwww\.\S+|\b[a-z0-9-]+\.(?:com|com\.br|br|co|io|net|org|ai|app)/\S*",
                     re.IGNORECASE)
EMOJI_RE = re.compile(r"[\U0001F300-\U0001FAFF☀-➿←-⇿️]")

ASKS = [
    (re.compile(r"(?i)\bcoment(?:a|e|em)\s+(?:a palavra\s+|\")?[A-ZÀ-Ý0-9]{2,}\b"), "comentar palavra-chave"),
    (re.compile(r"(?i)\b(?:me chama|chama|manda (?:um )?(?:direct|dm|mensagem)|me manda)\b[^.!?\n]{0,15}\b(?:direct|dm|inbox|mensagem)?\b"), "direct"),
    (re.compile(r"(?i)\bsalv(?:a|e)\s+(?:esse|este|isso|o post|pra depois|para depois)\b"), "salvar"),
    (re.compile(r"(?i)\b(?:compartilh(?:a|e)|manda (?:pra|para) (?:quem|aquele|aquela|um amigo))\b"), "compartilhar"),
    (re.compile(r"(?i)\bmarc(?:a|ue)\s+(?:algu[ée]m|aquele|aquela|um amigo|uma amiga|quem)\b"), "marcar alguém"),
    (re.compile(r"(?i)\b(?:me segue|siga|segue (?:a|o) @|segue (?:pra|para) mais)\b"), "seguir"),
    (re.compile(r"(?i)\blink na bio\b"), "link na bio"),
    (re.compile(r"(?i)\b(?:arrasta|desliza|passa) (?:pro lado|para o lado|pra ver)\b"), "arrastar"),
    (re.compile(r"(?i)\b(?:me conta|me diz|qual (?:voc[êe]|vc) (?:escolheria|levaria|compraria)|comenta qual)\b"), "responder pergunta"),
    (re.compile(r"(?i)\bcri(?:a|e)\s+(?:o |seu |um )?alerta\b|\bmonitor(?:a|e)\s+(?:esse|o seu|seu)\b"), "criar alerta na Hoov"),
]

FILLER_TAGS = {"#viral", "#fyp", "#explore", "#explorar", "#explorepage", "#foryou",
               "#foryoupage", "#paravoce", "#pravoce", "#paravocê", "#trending", "#trend",
               "#instagood", "#love", "#follow", "#seguidores", "#segueeu", "#sdv",
               "#reels", "#reelsinstagram", "#reelsbrasil", "#viralreels", "#instadaily",
               "#brasil", "#carros", "#carro", "#auto"}

FIPE_RE = re.compile(r"(?i)\bfipe\b")
MONTHS = r"(?:jan(?:eiro)?|fev(?:ereiro)?|mar(?:[çc]o)?|abr(?:il)?|mai(?:o)?|jun(?:ho)?|jul(?:ho)?|ago(?:sto)?|set(?:embro)?|out(?:ubro)?|nov(?:embro)?|dez(?:embro)?)"
FIPE_MONTH_RE = re.compile(
    rf"(?i)\bfipe\b[^.\n]{{0,25}}?\b(?:de\s+|ref\.?\s*|refer[êe]ncia\s+)?{MONTHS}\b"
    rf"|\b{MONTHS}\s*/?\s*\d{{2,4}}\b[^.\n]{{0,25}}\bfipe\b"
    rf"|\bfipe\b[^.\n]{{0,25}}\b\d{{2}}/\d{{2,4}}\b")
DEVIATION_RE = re.compile(r"(?i)(\d{1,2}(?:[,.]\d+)?)\s?%\s*(abaixo|acima)\s*d[ae]\s*(?:tabela\s*)?fipe")
PRICE_RE = re.compile(r"R\$\s?\d")
CONFIRA_RE = re.compile(r"(?i)\b(?:confira|confere|desconfie|desconfia|cuidado|golpe|sinistro|vistoria|hist[óo]rico|laudo|cautelar|nunca (?:pague|fa[çc]a) pix)\b")

BANDS = [  # (limite superior do desvio, nome, palavras que a legenda pode usar)
    (-0.15, "ÓTIMO NEGÓCIO", ("ótimo negócio", "otimo negocio", "garimpo")),
    (-0.05, "BOM NEGÓCIO", ("bom negócio", "bom negocio")),
    (0.05, "PREÇO DE MERCADO", ("preço de mercado", "preco de mercado", "na fipe", "no preço")),
    (float("inf"), "ACIMA DO MERCADO", ("acima do mercado", "acima da fipe")),
]


def band_for(deviation):
    for upper, name, _ in BANDS:
        if deviation <= upper:
            return name
    return BANDS[-1][1]


def visible_window(text, cut):
    flat = text.strip()
    return flat if len(flat) <= cut else flat[:cut]


def render_box(window, truncated, out=sys.stdout, width=52):
    print("\n  O QUE O FEED MOSTRA", file=out)
    print("  +" + "-" * (width + 2) + "+", file=out)
    lines = []
    for raw in window.split("\n"):
        lines.extend(textwrap.wrap(raw, width) or [""])
    for line in lines[:8]:
        print(f"  | {line:<{width}} |", file=out)
    tail = "... mais" if truncated else "(legenda inteira cabe)"
    print("  +" + "-" * (width + 2 - len(tail) - 2) + f" {tail} " + "+", file=out)


def analyse(text, cut=TRUNCATE, keywords=None, preco=None, fipe=None):
    stripped = text.strip()
    chars = len(stripped)
    first_line = stripped.split("\n")[0].strip() if stripped else ""
    tags = HASHTAG_RE.findall(stripped)
    links = LINK_RE.findall(stripped)
    emoji = EMOJI_RE.findall(stripped)
    window = visible_window(stripped, cut)
    truncated = chars > cut
    asks = [name for pattern, name in ASKS if pattern.search(stripped)]
    filler = [t for t in tags if t.lower() in FILLER_TAGS]
    keywords = [k.strip() for k in (keywords or []) if k.strip()]
    checks = []

    def add(name, status, detail):
        checks.append({"check": name, "status": status, "detail": detail})

    add("TAMANHO", "FALHA" if chars > LIMIT else "OK",
        f"{chars} / {LIMIT} caracteres" + (f", {chars - LIMIT} acima do limite" if chars > LIMIT else ""))

    if not first_line:
        add("PRIMEIRA LINHA", "FALHA", "a legenda abre numa linha em branco")
    elif first_line[0] in "#@":
        add("PRIMEIRA LINHA", "FALHA", "abre em hashtag ou menção, na única posição que vale uma frase")
    elif re.match(r"(?i)^(?:oi|ol[áa]|e a[íi]|fala|bom dia|boa tarde|boa noite)\b", first_line):
        add("PRIMEIRA LINHA", "FALHA", "abre em saudação. A janela visível é curta demais para isso")
    elif len(first_line) > cut:
        add("PRIMEIRA LINHA", "AVISO", f"{len(first_line)} caracteres, então é cortada em {cut} no meio "
            "da ideia. Tudo bem se o corte for um suspense; ruim se for no meio de uma oração")
    else:
        add("PRIMEIRA LINHA", "OK", f"{len(first_line)} caracteres, aparece inteira")

    found = concrete_markers(window)
    add("GANCHO CONCRETO", "OK" if found else "AVISO",
        f"{len(found)} marcador(es) concreto(s) na janela visível"
        + (f": {', '.join(found[:4])}" if found else " - nada checável antes do toque"))

    if len(tags) > HASHTAG_LIMIT:
        add("HASHTAGS", "FALHA", f"{len(tags)} hashtags, acima do limite de {HASHTAG_LIMIT} do Instagram")
    elif filler:
        add("HASHTAGS", "AVISO", f"{len(tags)} hashtags, {len(filler)} genérica(s) "
            f"({', '.join(filler[:3])}). Não descrevem nada; troque por modelo e cidade")
    else:
        add("HASHTAGS", "OK", f"{len(tags)} hashtag(s)" + (f": {' '.join(tags)}" if tags else ""))

    if tags and any(re.search(r"(?:^|\s)" + re.escape(t) + r"\b", window) for t in tags):
        add("LUGAR DAS TAGS", "AVISO", "hashtag dentro da janela visível, gastando espaço do feed com rótulo")
    else:
        add("LUGAR DAS TAGS", "OK", "tags abaixo da dobra" if tags else "sem tags para posicionar")

    add("LINKS", "AVISO" if links else "OK",
        f"{len(links)} link(s) na legenda, e legenda não é clicável. Mande para a bio ou o direct"
        if links else "sem link morto no texto")

    if len(asks) == 1:
        add("UM PEDIDO", "OK", f"um pedido: {asks[0]}")
    elif not asks:
        add("UM PEDIDO", "AVISO", "nenhum pedido. Decida para que serve este post")
    else:
        add("UM PEDIDO", "AVISO", f"{len(asks)} pedidos ({', '.join(asks)}). Dois pedidos valem zero")

    density = len(emoji) * 100 / max(chars, 1)
    add("EMOJI", "AVISO" if density > 4 else "OK",
        f"{len(emoji)} emoji, {density:.1f} a cada 100 caracteres".replace(".", ",") + (" - virou enfeite" if density > 4 else ""))

    # --- checagens da Hoov -------------------------------------------------
    mentions_fipe = bool(FIPE_RE.search(stripped))
    quantified = bool(DEVIATION_RE.search(stripped) or PRICE_RE.search(stripped))
    if mentions_fipe and quantified:
        ok = bool(FIPE_MONTH_RE.search(stripped))
        add("FIPE COM MÊS", "OK" if ok else "FALHA",
            "mês de referência da FIPE presente" if ok else
            "fala em FIPE com preço ou % mas não diz o mês de referência (ex.: \"FIPE de outubro\")")

    deviations = [(-1 if m.group(2).lower() == "abaixo" else 1) * float(m.group(1).replace(",", ".")) / 100
                  for m in DEVIATION_RE.finditer(stripped)]
    deviation = None
    if preco and fipe:
        deviation = preco / fipe - 1
    elif deviations:
        deviation = deviations[0]
    if deviation is not None and deviation <= -CONFIRA_THRESHOLD:
        ok = bool(CONFIRA_RE.search(stripped))
        add("AVISO CONFIRA", "OK" if ok else "FALHA",
            f"desvio de {deviation:.0%} pede aviso de segurança" + (" e ele está lá" if ok else
            ". Inclua: confira histórico e vistoria, nunca Pix antes de ver o carro"))

    sinal = None
    if preco and fipe:
        sinal = band_for(deviation)
        stated = [d for d in deviations]
        detail = (f"preço R$ {preco:,.0f} / FIPE R$ {fipe:,.0f}".replace(",", ".")
                  + f" = {deviation:+.1%} -> {sinal}".replace(".", ","))
        status = "OK"
        if stated and abs(stated[0] - deviation) > 0.01:
            status = "FALHA"
            detail += f". A legenda diz {stated[0]:+.0%}; corrija para {deviation:+.0%}"
        for _, name, words_ in BANDS:
            if name != sinal and any(w in stripped.lower() for w in words_):
                status = "FALHA"
                detail += f". A legenda chama de \"{name.lower()}\", mas a faixa é {sinal}"
                break
        add("SINALEIRO", status, detail)

    if keywords:
        low = stripped.lower()
        found_k = [k for k in keywords if k.lower() in low]
        missing = [k for k in keywords if k.lower() not in low]
        in_window = [k for k in found_k if k.lower() in window.lower()]
        add("TERMOS DE BUSCA", "OK" if not missing else ("AVISO" if found_k else "FALHA"),
            f"{len(found_k)}/{len(keywords)} presentes"
            + (f", {len(in_window)} na janela visível" if found_k else "")
            + (f". Faltando: {', '.join(missing)}" if missing else ""))

    fails = sum(1 for c in checks if c["status"] == "FALHA")
    warns = sum(1 for c in checks if c["status"] == "AVISO")
    verdict = "CORRIGIR" if fails else ("REVISAR" if warns else "PRONTA")
    return {"characters": chars, "limit": LIMIT, "truncate_at": cut, "visible": window,
            "truncated": truncated, "hashtags": tags, "links": links, "emoji": len(emoji),
            "asks": asks, "deviation": deviation, "sinaleiro": sinal, "checks": checks,
            "verdict": verdict}


def render(a, out=sys.stdout):
    head = (f"REVISÃO DE LEGENDA  ·  {a['characters']} / {a['limit']} caracteres  ·  "
            f"{len(a['hashtags'])} hashtags  ·  {len(a['asks'])} pedido(s)")
    print("\n" + head, file=out)
    print("=" * max(len(head), 62), file=out)
    render_box(a["visible"], a["truncated"], out=out)
    print("", file=out)
    for c in a["checks"]:
        print(f"  {c['status']:<5} {c['check']:<16} {c['detail']}", file=out)
    print("-" * max(len(head), 62), file=out)
    print(f"  VEREDITO  {a['verdict']}\n", file=out)


def main():
    ap = argparse.ArgumentParser(description="Revisa uma legenda de Instagram em PT-BR.")
    ap.add_argument("input", nargs="?", default="-", help="arquivo da legenda, ou -")
    ap.add_argument("--truncate", type=int, default=TRUNCATE)
    ap.add_argument("--keywords", default="", help="termos de busca separados por vírgula")
    ap.add_argument("--preco", type=float, help="preço anunciado, em reais (ex.: 45100)")
    ap.add_argument("--fipe", type=float, help="valor FIPE, em reais (ex.: 52400)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    raw = sys.stdin.read() if args.input == "-" else open(args.input, encoding="utf-8").read()
    a = analyse(raw, cut=args.truncate, keywords=args.keywords.split(","), preco=args.preco, fipe=args.fipe)
    if args.json:
        print(json.dumps(a, indent=2, ensure_ascii=False))
    else:
        render(a)
    sys.exit(0 if a["verdict"] == "PRONTA" else 1)


if __name__ == "__main__":
    main()
