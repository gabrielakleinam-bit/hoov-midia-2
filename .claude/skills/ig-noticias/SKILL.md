---
name: ig-noticias
description: Levanta as notícias automotivas da semana que mexem no mercado brasileiro de carro (juros, impostos, FIPE, descontos, Fenabrave, chinesas, recall), ranqueia pelo impacto no usado e sugere pauta para a Hoov. Use para notícias de carro, o que aconteceu no mercado, pauta da semana.
---

# ig-noticias

Transforma o noticiário automotivo da semana num briefing curto: o que mexe no
preço e na liquidez do usado no Brasil, por que importa para quem compra e
revende, e qual post a Hoov pode fazer em cima.

Uma ferramenta roda nesta pasta:

```bash
python3 noticias.py --fetch                                  # lê os feeds de fontes.json
python3 noticias.py --input itens.json --dias 7              # lê o que veio da busca
python3 noticias.py --fetch --input itens.json --out noticias.md
```

## O ciclo

1. **Feeds.** Rode `noticias.py --fetch --json` para ver o que os feeds de
   `fontes.json` trazem (Webmotors WM1, AutoIndústria, Notícias Automotivas,
   Garagem 360). Se o ambiente bloquear a rede, o script avisa quais feeds
   falharam; siga para a busca.
2. **Busca.** Rode uma busca na web para cada item da lista `buscas` de
   `fontes.json`, uma por vez, não combinadas. Guarde em `itens.json` uma lista
   com `titulo`, `url`, `fonte` e `data` (AAAA-MM-DD, quando o resultado
   mostrar). É assim que entram sites sem feed, como Autoesporte, Quatro Rodas,
   Motor1, AutoPapo e Jornal do Carro.
3. **Ranking.** Rode `noticias.py --fetch --input itens.json --dias 7`. O
   script agrupa a mesma notícia de vários sites, classifica em 12 temas, pesa
   relevância para o Brasil, cobertura e recência, e rebaixa carro de nicho
   (acima de R$ 300 mil). Notícia sem data fica no meio da fila: preencha a
   data quando souber.
4. **Confirme antes de usar.** Título não é fato. Para as 3 a 5 primeiras,
   abra a fonte, ou uma segunda fonte, e confirme o número que vai virar post.
   Se a página recusar acesso, use só o título e o link e diga que não foi
   possível confirmar. Nunca tente contornar o bloqueio.
5. **Pauta.** Para cada uma das primeiras, escreva com suas palavras:
   - o fato em uma frase, com a fonte;
   - o efeito no usado (preço, tempo para vender, parcela);
   - o dado da Hoov que prova ou testa isso, marcado `{{dado da base}}` até
     alguém puxar o número real;
   - a fórmula de gancho de `/ig-reel` (a sugestão do script é ponto de
     partida, não regra).
6. **Entregue** o briefing e grave em `noticias-AAAA-MM-DD.md`, na mesma pasta
   do arquivo de voz. Ofereça mandar a melhor pauta para `/ig-reel`.

## Formato do briefing

```
NOTÍCIAS DA SEMANA · 26/10/2026 · 13 com impacto no mercado
Por tema: Preço de carro novo 3 · Vendas 3 · Tributos 2 · Juros 2

1. [Preço de carro novo] Duster 170 cv com desconto de R$ 37 mil
   Webmotors WM1 · 26/10 · link
   Efeito no usado: Duster e Pulse usados perdem força na negociação.
   Dado da Hoov: {{quanto o Duster usado caiu na praça em 30 dias}}
   Pauta: #17 Mano a Mano, "Duster 0 km ou Duster 2023 usado?"
```

## Regras

- **Não copie reportagem.** Do item, só título, link, fonte e data. O fato vai
  numa frase sua. Citação literal só se a palavra exata importar, e curta.
- **Brasil primeiro.** Notícia de fora só entra se tiver efeito claro aqui
  (tarifa, fábrica, preço de importado). O script marca como "impacto
  indireto".
- **Sem opinião política.** Juros e impostos são fato e efeito no bolso, não
  posição sobre governo.
- **Número da Hoov só da base.** Nada de inventar quanto um modelo caiu ou
  quanto tempo ficou no ar.

## Rodar toda semana

Isto rende mais como rotina: toda segunda, antes do ritual dos sócios. Se o
usuário quiser, crie uma tarefa agendada que rode este ciclo e entregue o
briefing.
