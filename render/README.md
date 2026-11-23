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

## Reel (foco do feed e dos stories)

Fluxo de um Reel, em comandos (a inteligência do Claude fica só no JSON):

```bash
mkdir work && cd work
python3 ../render/gravacao_tela.py "Creta" "Hyundai Creta" 2022      # grava hoov.com.br (fotos borradas)
python3 ../render/frames_para_clip.py fr meta.json rec.mp4
# Claude escreve spec.json (ver render/specs/exemplo-reel-creta.json); narração opcional: "narracao": "voz.mp3"
python3 ../render/render_reel.py spec.json reel.mp4                    # cenas, trilha por código, mixagem -14 LUFS
```

Testado: cenas de texto e final com SSIM 0,95 a 0,96 contra Reels publicados; áudio -14 LUFS;
exportação 1080x1920, 30 fps, H.264, AAC 48 kHz. Trilha por código (`musica_gerador.py`) custa zero crédito.
Obs.: o ducking exige a voz preenchida até o fim do vídeo (`apad`), já tratado no script.

## Atalhos que economizam chamadas (23/11/2026)

- `bash render/preparar.sh` — instala/valida numpy, scipy, playwright+chromium, ffmpeg numa chamada; imprime 1 linha (`OK | whisper piper` ou `FALTA: ...`).
- `python3 -I render/validar.py video.mp4 --tipo story|reel [--folha folha.png] [--narracao "texto"]` — ffprobe (1080x1920, h264, 30 fps), áudio presente, loudness, duração (story 6–15 s; reel 15–60 s), palavras da narração (story ≤ 20) e UMA folha de contato para abrir com Read. Saída: 1 linha JSON; exit 1 se algo falhar.
