#!/usr/bin/env python3
"""
hookscore.py - nota do gancho de um Reel em portugues, nas cinco coisas que
ganchos fortes tem em comum, e ranking de varias opcoes entre si.

Adaptado para PT-BR e para carro a partir de instagram-agent-skill (MIT,
Jake Schincariol). A logica de pontuacao e a mesma do original; o vocabulario,
os numeros (R$ 45.900, 14%, 38 mil km), as saudacoes e os preambulos sao
brasileiros.

O que isto e:  cinco heuristicas locais, calculadas so a partir do texto.
  TAMANHO       da para falar em menos de 3 segundos?
  CONCRETO      tem numero, preco, modelo, FIPE, cidade? algo checavel?
  TENSAO        tem algo em jogo? perda, golpe, abaixo/acima da FIPE, "nunca"?
  FRENTE        a palavra interessante esta no comeco, nao na nona posicao?
  ENDERECO      fala com alguem (voce) ou flutua no ar?

O que isto NAO e:  previsor de views. O original, testado em ingles, separou
bem gancho real de gancho ruim de proposito (AUC 0,83) e quase nao separou o
acerto do erro do mesmo criador (AUC 0,56, cara ou coroa). Esta versao em
portugues ainda nao foi validada contra dados reais do @hoovbr. Use para matar
gancho fraco antes de gravar. Quem decide qual gancho bom viaja e o grafico de
retencao, nao este script.

Uso
  python3 hookscore.py ganchos.txt           # um gancho por linha, ranqueados
  python3 hookscore.py --hook "Achei esse HB20 14% abaixo da FIPE."
  python3 hookscore.py ganchos.txt --json
"""

import argparse
import json
import os
import re
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ptbr import (EMOJI_RE, HASHTAG_RE, MONEY_RE, MONEY_WORDS, SPOKEN_NUMBERS,  # noqa: E402
                  concrete_markers, low_words, words, NUMBER_RE, CAR_TERMS,
                  MODEL_CODE_RE, ACRONYM_RE, PROPER_RE)

# Palavras que colocam algo em jogo. Sem nenhuma, o gancho e uma afirmacao;
# com uma, e um motivo para continuar assistindo.
STAKES = {
    "pare", "nunca", "errado", "errada", "erro", "erros", "erra",
    "perdi", "perder", "perdeu", "perdendo", "perda", "custa", "custou",
    "custar", "quebrou", "quebrado", "falhou", "ninguém", "ninguem", "não",
    "nao", "nem", "sem", "desisti", "golpe", "golpes", "golpista", "fraude",
    "roubado", "roubada", "sinistro", "sinistrado", "leilão", "leilao",
    "batido", "multa", "mentira", "mentiu", "verdade", "segredo", "escondido",
    "escondem", "esconde", "antes", "até", "mas", "porém", "porem", "exceto",
    "problema", "risco", "perigo", "cuidado", "atenção", "atencao",
    "arrependo", "arrependi", "deveria", "ainda", "já", "ja", "só", "apenas",
    "versus", "vs", "abaixo", "acima", "caro", "barato", "barata",
    "prejuízo", "prejuizo", "desvalorizou", "desvaloriza", "desvalorização",
    "queda", "caiu", "despencou", "subiu", "alta", "primeiro", "primeira",
    "grátis", "gratis", "pagou", "paguei", "economizei", "economizou", "vendi",
    "vendeu", "proibido", "ilegal", "pior", "piores", "odeio", "desperdício",
    "recall", "defeito", "bomba", "enganado", "enganada", "furada", "cilada",
    "mico", "encalhado", "encalha", "parado", "corre", "sumiu", "durou",
}

# Aberturas que gastam o primeiro segundo sem dizer nada.
WEAK_OPENERS = [
    "então", "entao", "bom", "ok", "oi", "olá", "ola", "e aí", "e ai", "eai",
    "fala", "galera", "pessoal", "gente", "bem-vindo", "bem-vindos", "hoje",
    "basicamente", "sinceramente", "olha", "escuta", "tipo", "né", "ne",
    "vou", "eu vou", "eu queria", "eu quero", "um dos", "uma das", "você já",
    "voce ja", "vocês já", "você sabia", "voce sabia", "vocês sabiam",
    "neste", "nesse", "no vídeo", "a questão", "muita gente", "existe",
    "existem", "tem gente", "isso é", "esse é", "essa é", "é o", "é a",
    "como um", "quando se", "se você já", "sabe", "salve", "bom dia",
    "boa tarde", "boa noite",
]

# Imperativos que merecem a primeira posicao.
IMPERATIVES = {
    "pare", "roube", "rouba", "copie", "copia", "apague", "apaga",
    "tente", "testa", "teste", "veja", "vê", "leia", "salve", "salva", "use",
    "usa", "monte", "faça", "faz", "escreva", "mande", "manda", "pegue",
    "pega", "comece", "começa", "nunca", "sempre", "não", "nao", "confira",
    "confere", "compare", "compara", "anote", "anota", "fuja", "foge",
    "corra", "corre", "desconfie", "negocie", "negocia", "cheque", "checa",
    "consulte", "busque", "evite", "esquece", "esqueça", "olhe",
}

DEALBREAKERS = [
    (re.compile(r"(?i)^\s*(?:para de rolar|pare de rolar|n[ãa]o passa|n[ãa]o pula|espera a[íi]|calma a[íi])"),
     "Abre pedindo atenção (\"para de rolar\"). Pedir atenção prova que você ainda não ganhou."),
    (re.compile(r"(?i)\b(?:(?:neste|nesse|no) (?:v[íi]deo|reel|post)(?: de hoje)?|hoje (?:eu )?vou (?:te |lhes |pra voc[êe]s? )?(?:mostrar|falar|ensinar|contar)|vou (?:te )?mostrar (?:pra voc[êe]s? )?como|vem comigo)\b"),
     "Preâmbulo de vídeo. Apague e abra no resultado."),
    (re.compile(r"(?i)^\s*(?:oi|ol[áa]|e a[íi]|eai|fala(?: galera| pessoal| a[íi])?|salve|bom dia|boa tarde|boa noite|bem[- ]vind[oa]s?)\b"),
     "Saudação. Ninguém abriu o feed para ser cumprimentado."),
    (HASHTAG_RE,
     "Hashtag no gancho. Hashtag vai no pé da legenda, se for."),
    (EMOJI_RE,
     "Emoji no gancho. Texto de gancho na tela tem espaço para palavra ou para emoji, não os dois."),
]

FIPE_DEVIATION_RE = re.compile(r"(?i)\d[\d,.]*\s?%\s*(?:abaixo|acima)\s*d[ae]\s*(?:tabela\s*)?fipe")
FIRST_PERSON_RE = re.compile(
    r"(?i)\b(?:eu|meu|minha|meus|minhas|me|mim|comigo|n[óo]s|nosso|nossa|a gente)\b"
    r"|\b[a-zà-ú]{3,}ei\b")
SECOND_PERSON_RE = re.compile(r"(?i)\b(?:voc[êe]s?|vc|vcs|seu|sua|seus|suas|te|teu|tua|contigo|tu)\b")


def clamp(n):
    return max(0.0, min(100.0, n))


def check_length(text):
    """O gancho tem que chegar antes do dedo mexer. Uns dois segundos."""
    n = len(words(text))
    secs = n / 2.5                       # ~150 palavras por minuto, falado
    chars = len(text.strip())
    if 5 <= n <= 10:
        score = 100.0
    elif n < 5:
        score = clamp(100 - (5 - n) * 20)
    else:
        score = clamp(100 - (n - 10) * 11)
    if chars > 65:                       # duas linhas de texto grande na tela
        score -= 12
    return clamp(score), f"{n} palavras, {chars} caracteres, ~{secs:.1f}s falado (ideal 5-10 palavras)"


def check_specificity(text):
    """Uma coisa concreta vale mais que tres abstratas."""
    found = concrete_markers(text)
    hits = len(found)
    score = 15.0 if hits == 0 else clamp(45 + hits * 30)
    return score, (f"{hits} marcador(es) concreto(s)" + (f": {', '.join(found[:4])}" if found else
                   " - sem número, sem modelo, sem nada checável"))


def check_stakes(text):
    """Tensao, custo, negacao. Algo que quem assiste pode perder."""
    hits = [x for x in low_words(text) if x in STAKES]
    markers = sorted(set(hits))
    if MONEY_RE.search(text):
        markers.append("um preço")
    if FIPE_DEVIATION_RE.search(text):
        markers.append("desvio da FIPE")
    n = len(markers)
    score = {0: 20.0, 1: 70.0}.get(n, 100.0)
    detail = f"{n} marcador(es) de tensão" + (f": {', '.join(markers[:4])}" if markers else
                                              " - nada está em jogo nesta frase")
    return clamp(score), detail


def _is_payload(i, raw, low):
    return (low in STAKES or low in SPOKEN_NUMBERS or low in MONEY_WORDS or low in CAR_TERMS
            or bool(re.search(r"\d", raw)) or bool(ACRONYM_RE.fullmatch(raw))
            or bool(MODEL_CODE_RE.fullmatch(raw)) or (i and PROPER_RE.fullmatch(raw)))


def check_frontload(text):
    """A palavra interessante nao pode estar na nona posicao."""
    w = words(text)
    if not w:
        return 0.0, "vazio"
    low = [x.lower().strip("'’") for x in w]
    opener = " ".join(low[:3])
    penalty, hit_opener = 0, None
    for weak in WEAK_OPENERS:
        if opener == weak or opener.startswith(weak + " ") or low[0] == weak:
            penalty, hit_opener = 30, weak
            break
    payload = next((i for i, raw in enumerate(w) if _is_payload(i, raw, low[i])), None)
    if payload is None:
        base, where = 30.0, "nenhuma palavra de impacto na frase inteira"
    elif payload <= 3:
        base, where = 100.0, f"impacto na palavra {payload + 1}"
    elif payload <= 6:
        base, where = 70.0, f"impacto na palavra {payload + 1}, dá para trazer para frente"
    else:
        base, where = 40.0, f"impacto na palavra {payload + 1}, tarde demais"
    detail = where + (f"; abertura fraca \"{hit_opener}\"" if hit_opener else "")
    return clamp(base - penalty), detail


def check_address(text):
    """Mirado em uma pessoa, ou solto no ar."""
    low = low_words(text)
    if SECOND_PERSON_RE.search(text):
        return 100.0, "fala com quem assiste"
    if low and low[0] in IMPERATIVES:
        return 90.0, f"abre no imperativo (\"{low[0]}\")"
    if FIRST_PERSON_RE.search(text):
        return 70.0, "primeira pessoa, sem falar com ninguém"
    return 35.0, "terceira pessoa, ninguém na sala"


CHECKS = ["TAMANHO", "CONCRETO", "TENSAO", "FRENTE", "ENDERECO"]


def run(text):
    results = {
        "TAMANHO": check_length(text),
        "CONCRETO": check_specificity(text),
        "TENSAO": check_stakes(text),
        "FRENTE": check_frontload(text),
        "ENDERECO": check_address(text),
    }
    flags = [msg for pattern, msg in DEALBREAKERS if pattern.search(text)]
    scores = [results[c][0] for c in CHECKS]
    # A propriedade mais fraca limita o gancho: basta uma ruim para o dedo
    # continuar rolando.
    overall = clamp(statistics.mean(scores) * 0.6 + min(scores) * 0.4 - len(flags) * 15)
    verdict = "FORTE" if overall >= 70 and min(scores) >= 55 and not flags else (
        "OK" if overall >= 50 else "FRACO")
    return results, overall, verdict, flags


def bar(score, width=24):
    filled = round(score / 100 * width)
    return "#" * filled + "." * (width - filled)


def render_one(text, results, overall, verdict, flags, out=sys.stdout):
    print("\nNOTA DO GANCHO", file=out)
    print("=" * 62, file=out)
    print(f"  \"{text.strip()}\"\n", file=out)
    for name in CHECKS:
        score, detail = results[name]
        print(f"  {name:<13} {bar(score)} {score:5.1f}", file=out)
        print(f"  {'':<13} {detail}", file=out)
    print("-" * 62, file=out)
    print(f"  {'NOTA':<13} {bar(overall)} {overall:5.1f}   {verdict}", file=out)
    for f in flags:
        print(f"\n  ELIMINATÓRIO  {f}", file=out)
    if verdict != "FORTE":
        weakest = min(CHECKS, key=lambda c: results[c][0])
        print(f"\n  Ponto mais fraco: {weakest}. Corrija esse e rode de novo.", file=out)
    print("", file=out)


def render_table(rows, out=sys.stdout):
    print("\nRANKING DE GANCHOS\n" + "=" * 78, file=out)
    for i, r in enumerate(rows, 1):
        mark = "->" if i == 1 else "  "
        hook = r["hook"] if len(r["hook"]) <= 62 else r["hook"][:59] + "..."
        print(f"{mark} {r['score']:5.1f} {r['verdict']:<6} {hook}", file=out)
        print(f"        mais fraco: {r['weakest']} ({r['checks'][r['weakest']]['score']:.0f})", file=out)
        for f in r["flags"]:
            print(f"        eliminatório: {f}", file=out)
    print("\nGrave o primeiro. Se o primeiro está abaixo de 50, nenhum destes é o gancho.\n",
          file=out)


def main():
    ap = argparse.ArgumentParser(description="Nota do gancho de um Reel em PT-BR.")
    ap.add_argument("input", nargs="?", default="-", help="arquivo com um gancho por linha, ou -")
    ap.add_argument("--hook", help="avalia um gancho passado na linha de comando")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.hook:
        lines = [args.hook]
    else:
        raw = sys.stdin.read() if args.input == "-" else open(args.input, encoding="utf-8").read()
        lines = [l.strip() for l in raw.splitlines() if l.strip()]
    if not lines:
        print("nada para avaliar", file=sys.stderr)
        sys.exit(2)

    payload = []
    for line in lines:
        results, overall, verdict, flags = run(line)
        payload.append({
            "hook": line,
            "checks": {k: {"score": round(v[0], 1), "detail": v[1]} for k, v in results.items()},
            "weakest": min(CHECKS, key=lambda c: results[c][0]),
            "flags": flags,
            "score": round(overall, 1),
            "verdict": verdict,
        })

    if args.json:
        print(json.dumps(payload if len(payload) > 1 else payload[0], indent=2, ensure_ascii=False))
        return
    if len(payload) == 1:
        render_one(lines[0], *run(lines[0]))
    else:
        render_table(sorted(payload, key=lambda r: -r["score"]))
    sys.exit(0 if max(p["score"] for p in payload) >= 70 else 1)


if __name__ == "__main__":
    main()
