#!/usr/bin/env python3
"""Renderiza um carrossel Hoov (PNG 1080x1350) a partir de um JSON.
Uso: python3 render_carousel.py spec.json saida_dir
Spec: {"slides":[{"tipo":"capa|texto|passo|lista|cta", ...}]}
Claude só escreve o JSON; o layout fica fixo aqui (padrão aprovado)."""
import json, sys, base64, pathlib, html
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).parent
B = json.loads((ROOT / "brand.json").read_text())
W, H = B["canvas"]["w"], B["canvas"]["h"]
LOGO = base64.b64encode((ROOT / B["logo"]).read_bytes()).decode()

def esc(s): return html.escape(s).replace("\n", "<br>")
def hl(s):
    """**trecho** vira destaque na cor da marca."""
    out, parts = "", html.escape(s).split("**")
    for i, p in enumerate(parts):
        out += f'<span class="r">{p}</span>' if i % 2 else p
    return out.replace("\n", "<br>")

CSS = f"""
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:{B['bg']};font-family:'{B['font']}',sans-serif;color:{B['text']}}}
.s{{position:relative;width:{W}px;height:{H}px;background:{B['bg']};overflow:hidden}}
.bar{{position:absolute;left:0;top:0;width:{W}px;height:{B['bar_h']}px;background:{B['accent']}}}
.r{{color:{B['accent']}}}
.c{{position:absolute;left:{B['margin_x']}px;right:{B['margin_x']}px}}
.h{{font-weight:800;letter-spacing:-0.02em}}
.p{{font-weight:500;color:{B['muted']};font-size:50px;line-height:1.32}}
.ft{{position:absolute;left:{B['margin_x']}px;right:{B['margin_x']}px;top:1190px;height:56px;display:flex;justify-content:space-between;align-items:center}}
.ft img{{height:56px}}
.ft span{{font-weight:500;font-size:30px;color:#9A9A9A}}
.num{{font-weight:800;font-size:300px;line-height:1;color:{B['accent']}}}
.arr{{position:absolute;right:{B['margin_x']}px;top:1096px;font-weight:800;font-size:34px;color:{B['accent']}}}
ol{{list-style:none}} li{{display:flex;gap:26px;font-weight:500;font-size:50px;padding:30px 0;border-bottom:2px solid #333;line-height:1.2}}
li b{{color:{B['accent']};font-weight:800;width:54px}}
"""

def slide(sp, i, n):
    t = sp["tipo"]
    if t == "capa":
        body = f'<div class="c" style="top:299px"><div class="h" style="font-size:132px;line-height:1.005;text-transform:uppercase">{hl(sp["titulo"])}</div>' \
               f'<div class="p" style="margin-top:56px;font-size:46px;line-height:1.28">{esc(sp.get("sub",""))}</div></div><div class="arr">arrasta →</div>'
    elif t == "texto":
        body = f'<div class="c" style="top:330px"><div class="h" style="font-size:92px;line-height:1.08">{hl(sp["titulo"])}</div>' \
               f'<div class="p" style="margin-top:68px">{esc(sp.get("corpo",""))}</div></div>'
    elif t == "passo":
        body = f'<div class="c" style="top:{sp.get("top",175)}px"><div class="num">{sp["n"]}</div>' \
               f'<div class="h" style="font-size:84px;line-height:1.08;margin-top:35px">{hl(sp["titulo"])}</div>' \
               f'<div class="p" style="margin-top:55px;line-height:1.3">{esc(sp.get("corpo",""))}</div></div>'
    elif t == "lista":
        items = "".join(f'<li><b>{k+1}</b><span>{esc(x)}</span></li>' for k, x in enumerate(sp["itens"]))
        body = f'<div class="c" style="top:210px"><div class="h" style="font-size:70px;line-height:1.1;margin-bottom:68px">{hl(sp["titulo"])}</div><ol>{items}</ol></div>'
    elif t == "cta":
        body = f'<div class="c" style="top:{sp.get("top",350)}px"><div class="h" style="font-size:104px;line-height:1.05">{hl(sp["titulo"])}</div>' \
               f'<div class="p" style="margin-top:79px;font-size:46px;line-height:1.3">{esc(sp.get("corpo",""))}</div></div>'
    else:
        raise SystemExit(f"tipo desconhecido: {t}")
    foot = f'<div class="ft"><img src="data:image/png;base64,{LOGO}"><span>{B["handle"]}&nbsp;&nbsp;&nbsp;{i}/{n}</span></div>'
    return f'<div class="s"><div class="bar"></div>{body}{foot}</div>'

def render(spec_path, out_dir):
    spec = json.loads(pathlib.Path(spec_path).read_text())
    out = pathlib.Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    sl = spec["slides"]; n = len(sl)
    page_html = f"<html><head><meta charset='utf-8'><style>{CSS}</style></head><body>" + \
        "".join(slide(s, k + 1, n) for k, s in enumerate(sl)) + "</body></html>"
    with sync_playwright() as p:
        br = p.chromium.launch(); pg = br.new_page(viewport={"width": W, "height": H})
        pg.set_content(page_html); pg.wait_for_timeout(300)
        for k, el in enumerate(pg.query_selector_all(".s")):
            el.screenshot(path=str(out / f"slide-{k+1}.png"))
        br.close()
    return n

if __name__ == "__main__":
    print(render(sys.argv[1], sys.argv[2]), "slides em", sys.argv[2])
