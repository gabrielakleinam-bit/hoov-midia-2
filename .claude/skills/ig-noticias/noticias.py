#!/usr/bin/env python3
"""
noticias.py - as notícias automotivas da semana que mexem no mercado
brasileiro de carro, ranqueadas pelo impacto em quem compra e revende usado,
com uma pauta de conteúdo para cada uma.

Duas entradas, que podem ser usadas juntas:
  --fetch           lê os feeds RSS de fontes.json (precisa de internet liberada
                    para esses sites onde o script roda)
  --input ARQ       lê itens coletados por busca, em JSON (lista de objetos com
                    titulo, url, fonte, data e, opcional, resumo) ou TSV com as
                    mesmas colunas

O que faz:
  1. junta os itens, descarta os mais velhos que --dias
  2. agrupa a mesma notícia publicada por sites diferentes (mais fontes =
     mais relevância)
  3. classifica por tema de impacto: crédito e juros, tributos, FIPE e usados,
     preço de carro novo, vendas, importação, marcas chinesas, saída de
     linha, recall, combustível, regras
  4. pesa a relevância para o Brasil e a recência
  5. imprime o briefing: tema, por que importa para a Hoov e a pauta sugerida
     com a fórmula de gancho de /ig-reel

O que NÃO faz: copiar texto de reportagem. Do item guarda só título, link,
fonte, data e um trecho curto do resumo para classificar. O briefing mostra
título e link; a pauta é escrita com as palavras da Hoov.

Uso
  python3 noticias.py --fetch
  python3 noticias.py --input itens.json --dias 7 --top 10
  python3 noticias.py --fetch --input itens.json --out noticias.md
  python3 noticias.py --input itens.json --json
"""

import argparse
import csv
import datetime as dt
import email.utils
import html
import json
import os
import re
import sys
import unicodedata
import urllib.request
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
FONTES = os.path.join(HERE, "fontes.json")
MAX_BYTES = 3_000_000
TZ = dt.timezone(dt.timedelta(hours=-3))  # Brasília

# ---------------------------------------------------------------------------
# Temas: peso de impacto no mercado de usado, regex, por que importa e pauta.
# ---------------------------------------------------------------------------
TEMAS = [
    {"id": "credito", "nome": "Crédito e juros", "peso": 5,
     "re": r"\bselic\b|\bcopom\b|\bjuros?\b|\bfinanciamento|\bfinanciad|\bcr[ée]dito\b|\binadimpl|\bcons[óo]rcio|\bcdc\b",
     "porque": "Juros mexem na parcela, e a parcela decide a compra de usado financiado (4,6 milhões em 2025). Juro caindo puxa demanda e preço; subindo, alonga o tempo de venda.",
     "pauta": "Quanto muda a parcela de um usado de R$ 50 mil com a taxa nova. Gancho #19 O Prazo ou #23 A Estatística."},
    {"id": "tributos", "nome": "Tributos", "peso": 5,
     "re": r"\bipi\b|\bipva\b|\bicms\b|reforma tribut|imposto seletivo|\bcbs\b|\bibs\b|\bmover\b|isen[çc][ãa]o|imposto (?:sobre|de|do)|al[íi]quota|\bpcd\b",
     "porque": "Imposto muda o preço do novo e, em cadeia, o do usado. IPVA é custo de dono e pesa na decisão de trocar no fim do ano.",
     "pauta": "O que muda no bolso de quem vai comprar usado nos próximos 60 dias. Gancho #19 O Prazo."},
    {"id": "fipe_usados", "nome": "FIPE e usados", "peso": 5,
     "re": r"\bfipe\b|\busados?\b|seminov|desvaloriz|deprecia|\brevenda|\brevendedor|\bleil[ãa]o|\btransfer[êe]ncias?\b|valor de mercado|carros? de segunda",
     "porque": "É o assunto da Hoov. Movimento de FIPE e de usado vira sinaleiro, score de liquidez e conteúdo direto.",
     "pauta": "Cruze com a base: quais modelos da praça estão mais abaixo da FIPE nesta semana. Gancho #27 O Garimpo ou #28 O Cronômetro."},
    {"id": "preco_novos", "nome": "Preço de carro novo", "peso": 4,
     "re": r"desconto|mais barat|fica (?:at[ée] )?R\$|reduz(?:iu|e)? (?:o )?pre[çc]o|corta pre[çc]o|baixa (?:de )?pre[çc]o|reajust|aumenta (?:o )?pre[çc]o|fica mais car|\bb[ôo]nus\b|taxa zero",
     "porque": "Desconto em novo derruba o usado do mesmo modelo e dos rivais. Quem tem o modelo para vender perde margem; quem compra ganha poder de negociação.",
     "pauta": "Se o novo ficou R$ X mais barato, quanto o usado do mesmo modelo precisa cair. Gancho #4 A Troca ou #17 Mano a Mano."},
    {"id": "vendas", "nome": "Vendas e mercado", "peso": 4,
     "re": r"fenabrave|fenauto|anfavea|emplacament|(?<!pr[ée]-)\bvendas?\b|mais vendid|ranking|licenciament|participa[çc][ãa]o de mercado|market share|produ[çc][ãa]o de ve[íi]culos",
     "porque": "Volume e ranking mostram o que gira. O que vende muito novo vira oferta grande de usado em 2 a 4 anos.",
     "pauta": "O modelo que mais vendeu e quanto tempo o usado dele dura no ar na praça. Gancho #23 A Estatística."},
    {"id": "importacao", "nome": "Importação e tarifas", "peso": 4,
     "re": r"importa[çc][ãa]o|importad|tarifa|\bcota\b|mercosul|exporta|imposto de importa|\bf[áa]brica\b|camaçari|produ[çc][ãa]o local|nacionaliza",
     "porque": "Tarifa e fábrica local decidem o preço dos importados, principalmente elétricos e chineses, e isso empurra o preço dos concorrentes usados.",
     "pauta": "O que a regra nova faz com o preço dos rivais usados. Gancho #19 O Prazo."},
    {"id": "chinesas", "nome": "Marcas chinesas e novas", "peso": 3,
     "re": r"\bbyd\b|\bgwm\b|\bchery\b|\bomoda\b|\bjaecoo\b|\bgeely\b|leapmotor|\bgac\b|\bzeekr\b|\bjac\b|chin[êe]s|chinesa",
     "porque": "Marca nova com preço agressivo derruba o valor do usado de categoria parecida e cria dúvida de revenda no próprio usado chinês.",
     "pauta": "Quanto tempo o usado da marca chinesa leva para sair do ar comparado com o rival tradicional. Gancho #28 O Cronômetro ou #17 Mano a Mano."},
    {"id": "linha", "nome": "Lançamento e saída de linha", "peso": 3,
     "re": r"sai de linha|deixa de ser (?:fabricad|produzid|vendid)|fim de (?:linha|produ[çc][ãa]o)|encerra (?:a )?produ|nova gera[çc][ãa]o|lan[çc]a(?:mento)?|reestiliza|facelift|pr[ée]-venda|estreia|chega ao brasil",
     "porque": "Geração nova ou fim de linha mexe no valor do usado da geração anterior, para baixo no curto prazo.",
     "pauta": "Vale comprar a geração antiga agora? Gancho #24 A Revelação ou #20 Permissão."},
    {"id": "recall", "nome": "Recall e segurança", "peso": 3,
     "re": r"\brecall\b|convoca[çc][ãa]o|\bdefeito|risco de (?:inc[êe]ndio|acidente)|airbag|nota (?:no )?latin ncap|latin ncap|crash test",
     "porque": "Recall pendente é pergunta obrigatória na compra de usado do modelo. Conteúdo de segurança reforça a confiança no sinaleiro.",
     "pauta": "Checklist: como saber se o usado que você vai ver tem recall pendente. Gancho #9 O Roubo."},
    {"id": "combustivel", "nome": "Combustível", "peso": 3,
     "re": r"gasolina|etanol|diesel|petrobras|combust[íi]vel|\bgnv\b|pre[çc]o (?:do|da) (?:litro|bomba)",
     "porque": "Combustível caro valoriza usado econômico e flex; pesa na escolha entre modelos.",
     "pauta": "Os usados que mais economizam com o preço atual da bomba. Gancho #11 Lista Com Favorito."},
    {"id": "regras", "nome": "Regras, Detran e fiscalização", "peso": 2,
     "re": r"\bcnh\b|detran|\bmulta|\bctb\b|contran|senatran|licenciamento|vistoria|\bplaca\b|transfer[êe]ncia de propriedade|\blei\b|\bstf\b|\bstj\b",
     "porque": "Regra de transferência, vistoria ou documento muda o processo de compra e venda de usado.",
     "pauta": "O que muda na hora de transferir o usado. Gancho #2 Comando Negativo."},
    {"id": "eletricos", "nome": "Elétricos e híbridos", "peso": 2,
     "re": r"el[ée]tric|h[íi]brid|\bplug-in\b|recarga|bateria",
     "porque": "Usado elétrico ainda tem liquidez e valor de revenda pouco conhecidos: é dado que a Hoov tem e o mercado não.",
     "pauta": "Quanto um elétrico usado desvalorizou em 12 meses na base. Gancho #23 A Estatística."},
]
for t in TEMAS:
    t["rx"] = re.compile(t["re"], re.IGNORECASE)

BRASIL_RE = re.compile(
    r"\bbrasil|\bbrasileir|\bnacional\b|\bR\$|\breais\b|s[ãa]o paulo|\brio de janeiro|curitiba|paran[áa]|minas gerais"
    r"|bahia|camaçari|anápolis|anapolis|betim|s[ãa]o bernardo|sorocaba|piracicaba|taubat[ée]|resende|jacare[íi]"
    r"|fenabrave|fenauto|anfavea|detran|contran|ipva|\bfipe\b|selic|\bcopom\b|governo federal|receita federal",
    re.IGNORECASE)
EXTERIOR_RE = re.compile(
    r"\bnos eua\b|\bestados unidos\b|\bna europa\b|\beuropeu|\bna china\b|\bno jap[ãa]o\b|\bna alemanha\b"
    r"|\bno m[ée]xico\b|\bna argentina\b|\bna [íi]ndia\b|\bopel\b|\bvauxhall\b|\bcupra\b|\bdacia\b|\bseat\b",
    re.IGNORECASE)

POPULARES_RE = re.compile(
    r"\b(?:onix|hb20|gol|polo|t-cross|nivus|virtus|argo|mobi|strada|toro|pulse|fastback|kwid|duster"
    r"|kardian|compass|renegade|corolla|corolla cross|yaris|hilux|sw4|civic|city|hr-v|creta|tracker"
    r"|kicks|ranger|s10|208|2008|c3|tiggo|dolphin|song|haval|tera|basalt|kait|saveiro|montana|spin)\b",
    re.IGNORECASE)
PRECO_RE = re.compile(r"R\$\s?(\d+(?:[.,]\d+)?)\s?(mil|milh)", re.IGNORECASE)

STOP = {"de", "do", "da", "dos", "das", "e", "o", "a", "os", "as", "em", "no", "na", "nos", "nas",
        "um", "uma", "para", "pra", "por", "com", "que", "se", "mais", "ao", "à", "é", "tem", "sem"}


# ---------------------------------------------------------------------------
# Coleta
# ---------------------------------------------------------------------------
def strip_html(s):
    s = re.sub(r"<[^>]+>", " ", s or "")
    s = html.unescape(s)
    return re.sub(r"\s+", " ", s).strip()


def parse_date(s):
    if not s:
        return None
    s = s.strip()
    try:
        d = email.utils.parsedate_to_datetime(s)
    except (TypeError, ValueError, IndexError):
        d = None
    if d is None:
        for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d",
                    "%d/%m/%Y %H:%M", "%d/%m/%Y"):
            try:
                d = dt.datetime.strptime(s.replace("Z", "+0000") if fmt.endswith("%z") else s, fmt)
                break
            except ValueError:
                continue
    if d is None:
        return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=TZ)
    return d


def parse_feed(xml_bytes, fonte):
    """RSS 2.0 e Atom. Guarda só o necessário para classificar e linkar."""
    items = []
    root = ET.fromstring(xml_bytes)
    ns_atom = "{http://www.w3.org/2005/Atom}"
    for it in root.iter("item"):
        items.append({
            "titulo": strip_html(it.findtext("title")),
            "url": (it.findtext("link") or "").strip(),
            "fonte": fonte,
            "data": it.findtext("pubDate") or it.findtext("{http://purl.org/dc/elements/1.1/}date"),
            "resumo": strip_html(it.findtext("description"))[:280],
            "categorias": " ".join(c.text or "" for c in it.findall("category")),
        })
    for it in root.iter(ns_atom + "entry"):
        link = it.find(ns_atom + "link")
        items.append({
            "titulo": strip_html(it.findtext(ns_atom + "title")),
            "url": link.get("href") if link is not None else "",
            "fonte": fonte,
            "data": it.findtext(ns_atom + "updated") or it.findtext(ns_atom + "published"),
            "resumo": strip_html(it.findtext(ns_atom + "summary"))[:280],
            "categorias": "",
        })
    return items


def fetch_feeds(fontes, timeout=15):
    items, erros = [], []
    for f in fontes.get("feeds", []):
        try:
            req = urllib.request.Request(f["url"], headers={
                "User-Agent": "Mozilla/5.0 (compatible; hoov-noticias/1.0; leitura de RSS)"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                data = r.read(MAX_BYTES)
            got = parse_feed(data, f["nome"])
            for g in got:
                g["peso_fonte"] = f.get("peso", 1)
            items += got
        except Exception as e:  # noqa: BLE001 - um feed ruim não derruba os outros
            erros.append(f"{f['nome']}: {type(e).__name__} {str(e)[:80]}")
    return items, erros


def load_input(path):
    raw = sys.stdin.read() if path == "-" else open(path, encoding="utf-8").read()
    raw_s = raw.strip()
    if raw_s.startswith("[") or raw_s.startswith("{"):
        data = json.loads(raw_s)
        data = data.get("itens", data) if isinstance(data, dict) else data
    else:
        data = list(csv.DictReader(raw.splitlines(), delimiter="\t"))
    out = []
    for d in data:
        out.append({
            "titulo": strip_html(d.get("titulo") or d.get("title") or ""),
            "url": (d.get("url") or d.get("link") or "").strip(),
            "fonte": d.get("fonte") or d.get("source") or "busca",
            "data": d.get("data") or d.get("date") or "",
            "resumo": strip_html(d.get("resumo") or d.get("snippet") or "")[:280],
            "categorias": "",
            "peso_fonte": float(d.get("peso_fonte") or 2),
        })
    return out


# ---------------------------------------------------------------------------
# Análise
# ---------------------------------------------------------------------------
def tokens(s):
    s = unicodedata.normalize("NFKD", s.lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return {w for w in re.findall(r"[a-z0-9]+", s) if w not in STOP and len(w) > 2}


def jaccard(a, b):
    return len(a & b) / len(a | b) if a and b else 0.0


def group(items, threshold=0.5):
    grupos = []
    for it in items:
        tk = tokens(it["titulo"])
        for g in grupos:
            if jaccard(tk, g["tk"]) >= threshold:
                g["itens"].append(it)
                g["tk"] |= tk
                break
        else:
            grupos.append({"tk": tk, "itens": [it]})
    return grupos


def classify(text):
    hits = []
    for t in TEMAS:
        m = t["rx"].findall(text)
        if m:
            hits.append((t, len(m)))
    hits.sort(key=lambda x: (-x[0]["peso"], -x[1]))
    return hits


def analyse(items, dias=7, agora=None):
    agora = agora or dt.datetime.now(TZ)
    corte = agora - dt.timedelta(days=dias)
    vistos, validos, sem_data = set(), [], 0
    for it in items:
        if not it["titulo"]:
            continue
        key = it["url"] or it["titulo"].lower()
        if key in vistos:
            continue
        vistos.add(key)
        it["dt"] = parse_date(it.get("data") or "")
        if it["dt"] is None:
            sem_data += 1
        elif it["dt"] < corte:
            continue
        validos.append(it)

    rows = []
    for g in group(validos):
        principal = max(g["itens"], key=lambda i: (i.get("peso_fonte", 1), len(i["resumo"])))
        texto = " ".join(f"{i['titulo']} {i['resumo']} {i.get('categorias', '')}" for i in g["itens"])
        temas = classify(texto)
        if not temas:
            continue
        base = temas[0][0]["peso"] + 0.5 * sum(t["peso"] for t, _ in temas[1:3]) / 5
        brasil = 1.0
        if EXTERIOR_RE.search(texto) and not BRASIL_RE.search(texto):
            brasil = 0.4
        elif BRASIL_RE.search(texto):
            brasil = 1.2
        fontes = sorted({i["fonte"] for i in g["itens"]})
        cobertura = 1 + 0.25 * (len(fontes) - 1)
        datas = [i["dt"] for i in g["itens"] if i["dt"]]
        idade = (agora - max(datas)).total_seconds() / 86400 if datas else dias / 2
        recencia = max(0.5, 1 - idade / (dias * 2))
        # Carro de nicho (acima de R$ 300 mil) mexe pouco no usado de volume;
        # modelo popular mexe muito.
        precos = [float(v.replace(",", ".")) * (1000 if u.lower() == "milh" else 1)
                  for v, u in PRECO_RE.findall(texto)]
        nicho = 0.6 if precos and max(precos) >= 300 and not POPULARES_RE.search(texto) else 1.0
        popular = 1.15 if POPULARES_RE.search(texto) else 1.0
        peso_fonte = 1 + 0.1 * (max(i.get("peso_fonte", 1) for i in g["itens"]) - 1)
        score = round(base * brasil * cobertura * recencia * peso_fonte * nicho * popular, 2)
        t0 = temas[0][0]
        rows.append({
            "score": score,
            "tema": t0["nome"],
            "temas": [t["nome"] for t, _ in temas[:3]],
            "titulo": principal["titulo"],
            "url": principal["url"],
            "fontes": fontes,
            "data": max(datas).astimezone(TZ).strftime("%d/%m %H:%M") if datas else "sem data",
            "brasil": brasil,
            "porque": t0["porque"],
            "pauta": t0["pauta"],
        })
    rows.sort(key=lambda r: -r["score"])
    resumo = {}
    for r in rows:
        resumo[r["tema"]] = resumo.get(r["tema"], 0) + 1
    return {"gerado_em": agora.strftime("%d/%m/%Y %H:%M"), "janela_dias": dias,
            "itens_lidos": len(items), "itens_na_janela": len(validos), "sem_data": sem_data,
            "noticias": rows, "por_tema": resumo}


def render(a, top=10, erros=None, out=sys.stdout):
    p = lambda s="": print(s, file=out)  # noqa: E731
    p(f"# Notícias automotivas · {a['gerado_em']}")
    p()
    p(f"Janela de {a['janela_dias']} dias · {a['itens_lidos']} itens lidos · "
      f"{len(a['noticias'])} notícias com impacto no mercado")
    if a["por_tema"]:
        p("Por tema: " + " · ".join(f"{k} {v}" for k, v in
                                   sorted(a["por_tema"].items(), key=lambda x: -x[1])))
    if erros:
        p()
        p("Feeds que falharam: " + "; ".join(erros))
    p()
    for i, r in enumerate(a["noticias"][:top], 1):
        fora = "  (exterior: impacto indireto)" if r["brasil"] < 1 else ""
        p(f"## {i}. [{r['tema']}] {r['titulo']}{fora}")
        p(f"{', '.join(r['fontes'])} · {r['data']} · impacto {r['score']:.1f}".replace(".", ",", 1)
          + (f" · também: {', '.join(r['temas'][1:])}" if len(r["temas"]) > 1 else ""))
        p(f"Link: {r['url']}" if r["url"] else "Link: (sem link)")
        p(f"Por que importa: {r['porque']}")
        p(f"Pauta: {r['pauta']}")
        p()
    if not a["noticias"]:
        p("Nada com impacto no mercado nesta janela.")


def main():
    ap = argparse.ArgumentParser(description="Briefing de notícias automotivas com impacto no Brasil.")
    ap.add_argument("--fetch", action="store_true", help="lê os feeds de fontes.json")
    ap.add_argument("--input", help="itens coletados por busca (JSON ou TSV), ou -")
    ap.add_argument("--fontes", default=FONTES)
    ap.add_argument("--dias", type=int, default=7)
    ap.add_argument("--top", type=int, default=10)
    ap.add_argument("--out", help="grava o briefing em Markdown")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if not args.fetch and not args.input:
        ap.error("use --fetch, --input ou os dois")
    items, erros = [], []
    if args.fetch:
        fontes = json.load(open(args.fontes, encoding="utf-8"))
        got, erros = fetch_feeds(fontes)
        items += got
    if args.input:
        items += load_input(args.input)

    a = analyse(items, dias=args.dias)
    if args.json:
        print(json.dumps({**a, "erros": erros}, indent=2, ensure_ascii=False, default=str))
        return
    if args.out:
        with open(os.path.expanduser(args.out), "w", encoding="utf-8") as fh:
            render(a, top=args.top, erros=erros, out=fh)
        print(f"gravado em {args.out}", file=sys.stderr)
    render(a, top=args.top, erros=erros)
    if args.fetch and not items:
        print("Nenhum feed respondeu. Se a rede deste ambiente bloqueia esses sites, colete pela "
              "busca e passe com --input.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
