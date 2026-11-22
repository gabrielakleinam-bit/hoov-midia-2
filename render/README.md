# Renderizador Hoov (Fase 1)

Separa inteligência (Claude escreve um JSON) de execução (scripts fixos geram o arquivo).

| Script | O que faz |
|---|---|
| `render_carousel.py spec.json saida/` | JSON → PNGs 1080x1350 no padrão aprovado (capa, texto, passo, lista, cta) |
| `compare.py novo/ aprovado/` | Teste de equivalência (SSIM ≥ 0,92 por slide). Nada novo entra em produção se falhar |
| `finalize_reel.py in.mp4 out.mp4` | Exportação padrão do Reel: 1080x1920, 30 fps, H.264, AAC 48 kHz estéreo, -14 LUFS |
| `brand.json` | Cores, fonte, margens, handle e logo extraídos dos posts publicados |

Validação: `specs/2026-10-27.json` reproduz os 9 slides de `posts/2026-10-27/` (SSIM 0,92 a 0,96).

Sintaxe do JSON: `**trecho**` vira destaque em #FF3214. Tipos: `capa` (titulo, sub), `texto` (titulo, corpo),
`passo` (n, titulo, corpo), `lista` (titulo, itens[]), `cta` (titulo, corpo).

Pendente (Fase 2): render do Reel a partir de JSON (cenas, narração ElevenLabs, trilha) com o mesmo teste de equivalência.
