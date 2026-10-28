"""
ptbr.py - vocabulario compartilhado pelos scripts do pacote, em portugues do
Brasil e com o universo de carros dentro.

O que conta como "concreto" num gancho ou numa legenda de carro:
  - dinheiro em real:        R$ 45.900, R$ 45 mil, 45 mil reais
  - numero com unidade:      14%, 2020, 38 mil km, 4 minutos, 60 dias
  - referencia checavel:     FIPE, IPVA, IPI, Selic
  - marca ou modelo:         HB20, T-Cross, Onix, Corolla, BYD, Strada
  - nome proprio:            Curitiba, Webmotors, Fenabrave
  - numero falado:           "catorze por cento", "vinte mil"

Os outros arquivos copiam este modulo para dentro da propria pasta, para cada
skill continuar funcionando sozinha.
"""

import re

LETTERS = "A-Za-zÀ-ÖØ-öø-ÿ"
WORD_RE = re.compile(rf"R\$|[{LETTERS}0-9$%'’-]+")

# Dinheiro: "R$ 45.900", "R$45,9 mil", "R$ 1,2 milhão"
MONEY_RE = re.compile(r"R\$\s?\d+(?:\.\d{3})*(?:,\d+)?(?:\s?(?:mil|milh(?:ão|ões|ao|oes)))?", re.I)
NUMBER_RE = re.compile(
    r"R\$\s?\d+(?:\.\d{3})*(?:,\d+)?(?:\s?(?:mil|milh(?:ão|ões|ao|oes)))?"
    r"|\b\d+(?:\.\d{3})*(?:,\d+)?\s?"
    r"(?:%|mil\b|k\b|km\b|x\b|cv\b|min\b|minutos?\b|segundos?\b|horas?\b|h\b"
    r"|dias?\b|semanas?\b|m[eê]s\b|meses\b|anos?\b|parcelas?\b|vezes\b)?",
    re.IGNORECASE)

# Maiuscula no meio da frase: nome de cidade, empresa, pessoa.
PROPER_RE = re.compile(r"\b[A-ZÀ-Ý][a-zà-ÿ]{2,}\b")
ACRONYM_RE = re.compile(r"\b(?:FIPE|Fipe|IPVA|IPI|ICMS|Selic|SELIC|CNH|CRLV|DPVAT|Detran|DETRAN|Fenabrave|Fenauto|Inmetro)\b")
# Modelo com numero: HB20, C3, 208, 2008, X1, CR-V, HR-V, T-Cross, S10, SW4
MODEL_CODE_RE = re.compile(r"\b(?:[A-Z]{1,3}-?\d{1,3}[A-Z]?|[A-Z]{2}-[A-Z]|T-Cross)\b")

CAR_TERMS = {
    # marcas
    "fiat", "chevrolet", "volkswagen", "vw", "toyota", "honda", "hyundai",
    "renault", "jeep", "nissan", "ford", "peugeot", "citroën", "citroen",
    "byd", "gwm", "chery", "caoa", "kia", "mitsubishi", "bmw", "audi",
    "mercedes", "volvo", "ram", "suzuki", "subaru", "porsche", "land rover",
    "geely", "omoda", "jaecoo", "leapmotor", "gac", "zeekr", "neta", "jac",
    # modelos que mais aparecem no usado
    "onix", "gol", "polo", "virtus", "nivus", "t-cross", "taos", "saveiro",
    "argo", "mobi", "uno", "cronos", "strada", "toro", "pulse", "fastback",
    "kwid", "sandero", "logan", "duster", "kardian", "oroch", "captur",
    "compass", "renegade", "commander", "corolla", "yaris", "etios", "hilux",
    "sw4", "rav4", "civic", "city", "fit", "hr-v", "cr-v", "wr-v", "creta",
    "hb20", "hb20s", "tucson", "tracker", "spin", "cruze", "montana",
    "s10", "kicks", "versa", "sentra", "frontier", "ranger", "ka", "ecosport",
    "208", "2008", "3008", "c3", "c4", "aircross", "tiggo", "dolphin", "song",
    "seal", "king", "haval", "h6", "tera", "basalt", "kait", "boreal",
}

SPOKEN_NUMBERS = {
    "zero", "dois", "duas", "três", "tres", "quatro", "cinco", "seis", "sete",
    "oito", "nove", "dez", "onze", "doze", "treze", "catorze", "quatorze",
    "quinze", "vinte", "trinta", "quarenta", "cinquenta", "sessenta",
    "setenta", "oitenta", "noventa", "cem", "cento", "duzentos", "trezentos",
    "quinhentos", "mil", "milhão", "milhao", "milhões", "milhoes", "dúzia",
    "metade", "dobro", "triplo",
}
MONEY_WORDS = {
    "reais", "real", "conto", "contos", "pila", "paus", "centavos", "lucro",
    "prejuízo", "prejuizo", "salário", "salario", "parcela", "parcelas",
    "juros", "entrada", "desconto", "margem", "fipe", "ipva", "financiamento",
    "seguro", "troco", "ágio", "agio",
}

HASHTAG_RE = re.compile(r"(?:^|\s)(#\w+)")
EMOJI_RE = re.compile(r"[\U0001F300-\U0001FAFF☀-➿]")


def normalize(text):
    """'R$ 45.900' e falado como uma palavra, entao vira uma palavra aqui."""
    text = re.sub(r"(?<=\d)\.(?=\d{3}\b)", "", text)
    text = re.sub(r"R\$\s+(?=\d)", "R$", text)
    return text


def words(text):
    return WORD_RE.findall(normalize(text))


def low_words(text):
    return [w.lower().strip("'’") for w in words(text)]


def concrete_markers(text):
    """Lista do que e checavel no texto. Sem repeticao."""
    found = []
    for n in NUMBER_RE.findall(text):
        n = n.strip()
        if n and re.search(r"\d", n):
            found.append(n)
    found += ACRONYM_RE.findall(text)
    found += MODEL_CODE_RE.findall(text)
    for m in PROPER_RE.finditer(text):
        raw_before = text[:m.start()]
        before = raw_before.rstrip()
        # Maiuscula no comeco de frase ou de linha nao e nome proprio.
        if (not before or "\n" in raw_before[len(before):]
                or not (before[-1].isalnum() or before[-1] in ",;:")):
            continue
        if m.group(0).lower() not in COMMON_CAPS:
            found.append(m.group(0))
    low = text.lower()
    for term in CAR_TERMS:
        if re.search(r"(?<![\w-])" + re.escape(term) + r"(?![\w-])", low):
            found.append(term)
    found += [w for w in low_words(text) if w in SPOKEN_NUMBERS or w in MONEY_WORDS]
    seen, out = set(), []
    for f in found:
        key = f.lower().replace(" ", "")
        if key not in seen:
            seen.add(key)
            out.append(f)
    return out


# Palavras que aparecem com maiuscula no meio da frase sem serem nome proprio.
COMMON_CAPS = {"eu", "você", "voce", "ele", "ela", "isso", "esse", "essa"}
