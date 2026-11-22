# Gravação real de tela do hoov.com.br (celular 405x720 ampliado para 1080x1920).
# Origem: claude/hoov-gravacao-tela.py do Projeto HOOV (10/11/2026) + blur 10 px em toda foto de anúncio por folha de estilo (22/11).
# Uso: python3 gravacao_tela.py "<texto digitado>" "<sugestão exata>" <ano>   (rodar numa pasta de trabalho vazia)
# Saída: fr/*.jpg + meta.json. Depois: python3 frames_para_clip.py fr meta.json rec.mp4
import base64, json, os, time, sys
from playwright.sync_api import sync_playwright
MODEL=sys.argv[1]; SUG=sys.argv[2]; YEAR=sys.argv[3]
os.makedirs('fr',exist_ok=True)
for f in os.listdir('fr'): os.remove('fr/'+f)
TOUCH="""
(()=>{const add=(x,y)=>{const d=document.createElement('div');d.style.cssText=`position:fixed;left:${x-22}px;top:${y-22}px;width:44px;height:44px;border-radius:50%;background:rgba(255,255,255,.55);border:3px solid rgba(255,50,20,.9);z-index:2147483647;pointer-events:none;transition:transform .45s ease-out,opacity .45s ease-out`;document.documentElement.appendChild(d);requestAnimationFrame(()=>{d.style.transform='scale(1.9)';d.style.opacity='0'});setTimeout(()=>d.remove(),600)};
window.addEventListener('pointerdown',e=>add(e.clientX,e.clientY),true);
window.addEventListener('touchstart',e=>{const t=e.touches[0];if(t)add(t.clientX,t.clientY)},true);})();
"""
BLUR="""
(()=>{const st=document.createElement('style');st.textContent='img.hoov-blur{filter:blur(10px)!important}';
const go=()=>{document.head&&!st.isConnected&&document.head.appendChild(st);document.querySelectorAll('img').forEach(i=>{const r=i.getBoundingClientRect();if(r.width>150&&r.height>90)i.classList.add('hoov-blur')})};
new MutationObserver(go).observe(document,{childList:true,subtree:true,attributes:true,attributeFilter:['src']});setInterval(go,120);})();
"""
log=[]
with sync_playwright() as p:
    b=p.chromium.launch()
    c=b.new_context(viewport={'width':405,'height':720},device_scale_factor=1080/405,locale='pt-BR',is_mobile=True,has_touch=True,color_scheme='dark',
        user_agent='Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1')
    c.add_init_script(TOUCH); c.add_init_script(BLUR)
    pg=c.new_page()
    pg.goto('https://hoov.com.br',wait_until='networkidle'); pg.wait_for_timeout(1200)
    cdp=c.new_cdp_session(pg); frames=[]
    def on(f):
        n=len(frames); open(f'fr/{n:05d}.jpg','wb').write(base64.b64decode(f['data']))
        frames.append(f['metadata']['timestamp']); cdp.send('Page.screencastFrameAck',{'sessionId':f['sessionId']})
    cdp.on('Page.screencastFrame',on)
    cdp.send('Page.startScreencast',{'format':'jpeg','quality':92,'maxWidth':1080,'maxHeight':1920,'everyNthFrame':1})
    T0=time.time(); mark=lambda k: log.append((k,round(time.time()-T0,2)))
    pg.evaluate("(()=>{const d=document.createElement('div');d.style.cssText='position:fixed;left:0;top:0;width:1px;height:1px;opacity:.01;z-index:2147483647';document.documentElement.appendChild(d);let i=0;setInterval(()=>{d.style.transform='translateX('+(i++%2)+'px)'},33)})()")
    mark('home'); pg.wait_for_timeout(1500)
    pg.get_by_text('Usados',exact=True).first.tap(); pg.wait_for_timeout(500)
    inp=pg.locator('input[type=text]').first; inp.tap(); pg.wait_for_timeout(400)
    mark('digita'); inp.type(MODEL,delay=170); pg.wait_for_timeout(1300)
    mark('sugestao'); pg.get_by_text(SUG,exact=True).first.tap()
    mark('carregando')
    for i in range(60):
        pg.wait_for_timeout(500)
        t=pg.inner_text('body')
        if 'Estimamos' in t and 'R$ ' in t: break
    mark('resultados'); pg.wait_for_timeout(2200)
    mark('rola')
    for i in range(14): pg.mouse.wheel(0,90); pg.wait_for_timeout(110)
    pg.wait_for_timeout(1300)
    for i in range(10): pg.mouse.wheel(0,110); pg.wait_for_timeout(110)
    pg.wait_for_timeout(1100)
    for i in range(24): pg.mouse.wheel(0,-110); pg.wait_for_timeout(45)
    pg.wait_for_timeout(700)
    mark('filtro')
    fb=pg.locator('button:has(svg.lucide-funnel), button:has(svg.lucide-filter)')
    if fb.count(): fb.first.tap()
    else:
        bb=pg.get_by_text('Mais relevantes').first.bounding_box(); pg.touchscreen.tap(bb['x']-46,bb['y']+bb['height']/2)
    pg.wait_for_timeout(1300)
    chip=pg.get_by_role('button',name=YEAR,exact=True).first
    for i in range(6): pg.mouse.wheel(0,70); pg.wait_for_timeout(90)
    chip.scroll_into_view_if_needed(); pg.wait_for_timeout(500)
    mark('ano'); chip.tap(); pg.wait_for_timeout(1100)
    aut=pg.get_by_role('button',name='Automático',exact=True).first
    for i in range(10): pg.mouse.wheel(0,80); pg.wait_for_timeout(90)
    aut.scroll_into_view_if_needed(); pg.wait_for_timeout(500)
    mark('cambio'); aut.tap(); pg.wait_for_timeout(1100)
    mark('aplicar'); pg.get_by_role('button',name='Aplicar filtros').first.tap()
    pg.wait_for_timeout(1500)
    for i in range(80):
        pg.wait_for_timeout(500)
        t=pg.inner_text('body')
        if YEAR in pg.url and 'Estimamos' in t and 'R$ ' in t: break
    mark('filtrado'); pg.wait_for_timeout(2400)
    for i in range(8): pg.mouse.wheel(0,90); pg.wait_for_timeout(110)
    pg.wait_for_timeout(900)
    for i in range(8): pg.mouse.wheel(0,-90); pg.wait_for_timeout(60)
    pg.wait_for_timeout(600)
    bb=pg.get_by_text('Mais relevantes').first.bounding_box()
    mark('salvar'); pg.touchscreen.tap(bb['x']-92,bb['y']+bb['height']/2); pg.wait_for_timeout(2600)
    mark('fim')
    est=[l for l in pg.inner_text('body').split('\n') if 'Estimamos' in l]
    cdp.send('Page.stopScreencast'); url=pg.url; b.close()
json.dump({'ts':frames,'log':log,'url':url,'est':est},open('meta.json','w'),ensure_ascii=False)
print(len(frames),'frames', round(frames[-1]-frames[0],1),'s'); print(log); print(url, est)
