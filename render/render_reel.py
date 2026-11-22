#!/usr/bin/env python3
"""Renderiza um Reel Hoov (MP4 1080x1920, 30 fps) a partir de um JSON.
Uso: python3 render_reel.py spec.json saida.mp4 [--sem-audio]

Claude escreve só o JSON (gancho, textos, cenas). Layout, mixagem e exportação ficam fixos aqui.

Cenas ("tipo"):
  card   {estados:[{t, titulo, sub}]}           texto sobre #161616 (gancho, tensão); cada estado entra em t segundos
  foto   {foto, titulo, credito}                foto de carro em faixa com degradê + título + crédito
  tela   {clip, ss, velocidade, selo, pop, pop_t, credito}   gravação real de tela (hoov-gravacao-tela.py)
  final  {titulo, cta, loop, handle}            logo, chamada, pílula "Link na bio", frase de loop
Cada cena tem "duracao" (s). Marcação **trecho** = destaque #FF3214.
Áudio: spec.narracao (arquivo), spec.musica ({seed,bpm,tom} gera por código, custo zero, ou {arquivo})."""
import json, sys, os, html, base64, pathlib, subprocess, tempfile, shutil
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).parent
B = json.loads((ROOT / "brand.json").read_text())
W, H = 1080, 1920
FPS = 30
LOGO = base64.b64encode((ROOT / "assets/hoov-logo-color.png").read_bytes()).decode()
ACC, BG, MUT = B["accent"], B["bg"], B["muted"]

def hl(s):
    out, parts = "", html.escape(s).split("**")
    for i, p in enumerate(parts):
        out += f'<span class="r">{p}</span>' if i % 2 else p
    return out.replace("\n", "<br>")

CSS = f"""
*{{margin:0;padding:0;box-sizing:border-box}}
html,body{{background:transparent}}
body{{font-family:'Inter',sans-serif;color:#fff}}
.s{{position:relative;width:{W}px;height:{H}px;overflow:hidden}}
.bg{{background:{BG}}}
.bar{{position:absolute;left:0;top:0;width:{W}px;height:14px;background:{ACC}}}
.r{{color:{ACC}}}
.t{{position:absolute;left:130px;right:130px;font-weight:800;letter-spacing:-0.02em}}
.p{{position:absolute;left:130px;width:800px;font-weight:500;color:{MUT};font-size:56px;line-height:1.25}}
.cr{{position:absolute;left:130px;right:130px;font-weight:500;font-size:30px;color:{MUT}}}
.ctr{{text-align:center;left:0;right:0;position:absolute;width:{W}px}}
"""

def card(st):
    sub = f'<div class="p" style="top:{st.get("sub_top",934)}px">{html.escape(st["sub"]).replace(chr(10),"<br>")}</div>' if st.get("sub") else ""
    return f'<div class="s bg"><div class="bar"></div><div class="t" style="top:{st.get("top",522)}px;font-size:108px;line-height:1.14">{hl(st["titulo"])}</div>{sub}</div>'

def foto(sc):
    ph = base64.b64encode(pathlib.Path(sc["foto"]).read_bytes()).decode()
    return (f'<div class="s bg"><div class="bar"></div>'
            f'<div class="t" style="top:300px;font-size:100px;line-height:1.1">{hl(sc["titulo"])}</div>'
            f'<div style="position:absolute;left:0;top:760px;width:{W}px;height:640px;background:url(data:image/jpeg;base64,{ph}) center/cover"></div>'
            f'<div style="position:absolute;left:0;top:760px;width:{W}px;height:640px;background:linear-gradient({BG} 0%,transparent 25%,transparent 75%,{BG} 100%)"></div>'
            f'<div class="cr" style="top:1440px">{html.escape(sc.get("credito",""))}</div></div>')

def final(sc):
    return (f'<div class="s bg"><div class="bar"></div>'
            f'<img src="data:image/png;base64,{LOGO}" style="position:absolute;left:330px;top:430px;width:420px">'
            f'<div class="ctr" style="top:{sc.get("top",722)}px;font-weight:800;font-size:88px;line-height:1.15;letter-spacing:-0.02em">{hl(sc["titulo"])}</div>'
            f'<div style="position:absolute;left:330px;top:960px;width:420px;height:101px;border-radius:22px;background:{ACC};display:flex;align-items:center;justify-content:center;font-weight:800;font-size:58px">{html.escape(sc.get("cta","Link na bio"))}</div>'
            + (f'<div class="ctr r" style="top:1150px;font-weight:800;font-size:60px">{html.escape(sc["loop"])}</div>' if sc.get("loop") else "")
            + f'<div class="ctr" style="top:1249px;font-weight:500;font-size:40px;color:{MUT}">{html.escape(sc.get("handle","Siga a @hoovbr pro garimpo do dia"))}</div></div>')

def overlay(sc):
    pop = ""
    if sc.get("pop"):
        pop = (f'<div style="position:absolute;left:90px;right:90px;top:{sc.get("pop_top",1180)}px;background:rgba(22,22,22,.92);border-left:8px solid {ACC};border-radius:14px;padding:26px 34px;font-weight:800;font-size:54px;line-height:1.15">{hl(sc["pop"])}</div>')
    selo = f'<div style="position:absolute;right:70px;top:90px;background:{ACC};border-radius:40px;padding:10px 28px;font-weight:800;font-size:38px">{html.escape(sc["selo"])}</div>' if sc.get("selo") else ""
    cred = f'<div style="position:absolute;left:60px;right:60px;top:1620px;font-weight:500;font-size:28px;color:{MUT};text-align:center;text-shadow:0 2px 6px #000">{html.escape(sc.get("credito",""))}</div>' if sc.get("credito") else ""
    return f'<div class="s" style="background:transparent">{pop}{selo}{cred}</div>'

def run(cmd): subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

def shot(pg, html_s, path):
    pg.set_content(f"<html><head><meta charset='utf-8'><style>{CSS}</style></head><body>{html_s}</body></html>")
    pg.wait_for_timeout(120)
    pg.screenshot(path=str(path), omit_background=True, clip={"x": 0, "y": 0, "width": W, "height": H})

def seg_from_pngs(pngs_durs, out):
    total = sum(d for _, d in pngs_durs)
    lst = out.with_suffix(".txt")
    with open(lst, "w") as f:
        for p, d in pngs_durs: f.write(f"file '{p}'\nduration {d:.3f}\n")
        f.write(f"file '{pngs_durs[-1][0]}'\n")
    run(["ffmpeg","-v","error","-y","-f","concat","-safe","0","-i",str(lst),"-vf",f"fps={FPS},format=yuv420p","-t",f"{total:.3f}","-c:v","libx264","-preset","veryfast","-crf","18",str(out)])

def build_video(spec, tmp):
    segs = []
    with sync_playwright() as p:
        br = p.chromium.launch(); pg = br.new_page(viewport={"width": W, "height": H})
        for i, sc in enumerate(spec["cenas"]):
            out = tmp / f"seg{i:02d}.mp4"; d = sc["duracao"]; t = sc["tipo"]
            if t == "card":
                sts = sc["estados"]; pd = []
                for k, st in enumerate(sts):
                    png = tmp / f"c{i}_{k}.png"; shot(pg, card(st), png)
                    end = sts[k + 1]["t"] if k + 1 < len(sts) else d
                    pd.append((png, end - st["t"]))
                seg_from_pngs(pd, out)
            elif t in ("foto", "final"):
                png = tmp / f"c{i}.png"; shot(pg, foto(sc) if t == "foto" else final(sc), png)
                seg_from_pngs([(png, d)], out)
            elif t == "tela":
                ov = tmp / f"o{i}.png"; shot(pg, overlay(sc), ov)
                v = sc.get("velocidade", 1.0)
                pop_t = sc.get("pop_t", 0)
                flt = (f"[0:v]setpts=PTS/{v},scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS}[a];"
                       f"[a][1:v]overlay=0:0:enable='gte(t,{pop_t})',format=yuv420p")
                run(["ffmpeg","-v","error","-y","-ss",str(sc.get("ss",0)),"-t",str(d * v),"-i",sc["clip"],"-loop","1","-i",str(ov),
                     "-filter_complex",flt,"-t",str(d),"-an","-c:v","libx264","-preset","veryfast","-crf","18",str(out)])
            else:
                raise SystemExit(f"cena desconhecida: {t}")
            segs.append(out)
        br.close()
    lst = tmp / "all.txt"; lst.write_text("".join(f"file '{s}'\n" for s in segs))
    vid = tmp / "video.mp4"
    run(["ffmpeg","-v","error","-y","-f","concat","-safe","0","-i",str(lst),"-c","copy",str(vid)])
    return vid

def build_audio(spec, tmp, dur):
    voz = spec.get("narracao"); mus = spec.get("musica")
    if mus and "arquivo" not in mus:
        wav = tmp / "musica.wav"
        run([sys.executable, str(ROOT / "musica_gerador.py"), str(mus["seed"]), str(mus["bpm"]), mus["tom"], str(dur), str(wav)])
        mus = {"arquivo": str(wav)}
    ins, parts = [], []
    if voz: ins += ["-i", voz]
    if mus: ins += ["-i", mus["arquivo"]]
    if not ins: return None
    out = tmp / "audio.m4a"
    if voz and mus:
        fc = (f"[0:a]loudnorm=I=-15:TP=-1.5,apad=whole_dur={dur},asplit[v1][v2];[1:a]volume=-21dB[m];"
              "[m][v1]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=300[md];"
              "[v2][md]amix=inputs=2:normalize=0:duration=longest,loudnorm=I=-14:TP=-1.5:LRA=11[o]")
    else:
        fc = "[0:a]loudnorm=I=-14:TP=-1.5:LRA=11[o]"
    run(["ffmpeg","-v","error","-y",*ins,"-filter_complex",fc,"-map","[o]","-t",str(dur),"-c:a","aac","-b:a","192k","-ar","48000","-ac","2",str(out)])
    return out

def render(spec_path, out_path, com_audio=True):
    spec = json.loads(pathlib.Path(spec_path).read_text())
    base = pathlib.Path(spec_path).parent
    for sc in spec["cenas"]:
        for k in ("foto", "clip"):
            if k in sc and not os.path.isabs(sc[k]): sc[k] = str((base / sc[k]).resolve())
    for k in ("narracao",):
        if spec.get(k) and not os.path.isabs(spec[k]): spec[k] = str((base / spec[k]).resolve())
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="reel_"))
    try:
        vid = build_video(spec, tmp)
        dur = sum(c["duracao"] for c in spec["cenas"])
        aud = build_audio(spec, tmp, dur) if com_audio else None
        cmd = ["ffmpeg","-v","error","-y","-i",str(vid)]
        if aud: cmd += ["-i", str(aud), "-c:v","copy","-c:a","copy","-shortest"]
        else: cmd += ["-c:v","copy","-an"]
        run(cmd + ["-movflags","+faststart", out_path])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return dur

if __name__ == "__main__":
    d = render(sys.argv[1], sys.argv[2], "--sem-audio" not in sys.argv)
    print(f"ok {sys.argv[2]} ({d:.1f}s)")
