---
name: ig-reel
description: Escreve um Reel em português a partir de uma ideia ou de um alerta da Hoov - três ganchos de 28 fórmulas com nota, roteiro falado, texto de tela e mapa de tempos. Use para reel, roteiro, gancho, garimpo do dia.
---

# ig-reel (PT-BR)

Transforma uma ideia crua, ou um carro real que caiu num alerta da Hoov, num
Reel que alguém assiste até o fim.

Duas ferramentas nesta pasta rodam de verdade. Use as duas. Não avalie o
gancho no olho e não chute a duração.

```bash
python3 hookscore.py ganchos.txt              # ranqueia as opções de gancho
python3 hookscore.py --hook "uma frase"       # nota de um gancho só
python3 beats.py roteiro.txt --target 15      # mapa de tempos antes de gravar
```

## Antes de escrever

1. Leia o arquivo de voz, na primeira destas posições que existir:
   `.claude/instagram/voz.md` (no repositório), `~/.claude/instagram/voz.md`.
   Se não existir, use `voz-hoov.md` desta pasta como ponto de
   partida e avise que ele ainda precisa ser validado pelos sócios. Roteiro na
   voz errada não serve, porque alguém vai ter que falar em voz alta.
2. Leia `ganchos.json` nesta pasta: 28 fórmulas, cada uma com modelo, exemplo,
   versão de tela, para que serve e como costuma ser estragada. As duas
   primeiras (O Garimpo e O Cronômetro) existem só porque a Hoov tem o dado do
   monitoramento. Prefira essas quando o dado existir.
3. Se a ideia for rala, não encha. Faça uma pergunta só, agrupada: qual carro,
   qual preço, qual FIPE e de que mês, onde, quanto tempo no ar. Um Reel
   precisa de uma coisa específica e verdadeira. Pegue antes de escrever.
4. Se existir `swipe.md` na mesma pasta do arquivo de voz, leia. É a evidência
   do próprio usuário sobre quais fórmulas estão funcionando agora.

## Garimpo do dia: o formato principal da Hoov

Quando a entrada for um carro de um alerta, o roteiro segue esta ordem:

```
0:00 - 0:03   GANCHO     O Garimpo ou O Cronômetro. Modelo, ano, desvio da FIPE.
0:03 - 0:08   A PROVA    preço anunciado, FIPE com o mês de referência, cidade.
0:08 - ...    O CORPO    km, histórico, tempo no ar. Um dado por trecho.
SE DESVIO >= 30%         o aviso "confira": golpe e sinistro também parecem
                         ótimo negócio. Puxar histórico, vistoria, nunca Pix
                         antes de ver o carro.
ÚLTIMOS 3s    O PEDIDO   criar o alerta do mesmo carro. Um pedido só.
ÚLTIMA FRASE  O LOOP     repetir uma palavra do gancho (o modelo ou "FIPE").
```

O sinaleiro na tela segue as faixas do business case (desvio = preço / FIPE − 1):
ÓTIMO NEGÓCIO até −15%, BOM NEGÓCIO de −15% a −5%, PREÇO DE MERCADO de −5% a
+5%, ACIMA DO MERCADO acima de +5%. `/ig-legenda` calcula a faixa com
`--preco` e `--fipe`.

## O formato geral

```
0:00 - 0:03   GANCHO      a afirmação. Linha falada e linha de tela escritas
                          separadas. Movimento no primeiro quadro.
0:03 - 0:08   A TENSÃO    por que isso importa para quem assiste. Uma frase.
0:08 - ...    O CORPO     uma ideia por trecho, e o quadro muda a cada trecho.
ÚLTIMOS 3s    A ENTREGA   cumpre o que o gancho prometeu, depois o pedido único.
ÚLTIMA FRASE  O LOOP      ecoa uma palavra do gancho.
```

Duração: 15 a 45 segundos. O garimpo do dia funciona em 15.

## O ciclo

1. **Três ganchos, não um.** Escolha três fórmulas diferentes que caibam na
   ideia e escreva a linha falada e a linha de tela de cada uma.
2. **Dê nota.** Coloque as três linhas faladas num arquivo, uma por linha, e
   rode `hookscore.py`. Mostre o ranking. Se o primeiro estiver abaixo de 50,
   ainda não tem gancho, e editar não resolve.
3. **Escreva o roteiro** no gancho vencedor. Português falado, do jeito que a
   pessoa fala: "pra", "tá", "a gente". Frases curtas. Nada que precise ensaiar.
4. **Cronometre.** Rode `beats.py roteiro.txt --target {duração}`. Corrija todo
   aviso: gancho passando de 3s, trecho acima de 4s, sequência sem nada
   concreto, falta de loop. Rode de novo até ficar limpo.
5. **Humanize.** Passe o roteiro por `/ig-humano` antes de mostrar.
6. **Entregue o bloco.** Roteiro num bloco de código, texto de tela numa lista
   separada com tempos, e depois:

```
REEL PRONTO
gancho:     #27 O Garimpo, nota 83 FORTE
duração:    14,6s em 5 trechos a 150 ppm
na tela:    4 cartões + sinaleiro BOM NEGÓCIO
fipe:       outubro/2026, desvio -14%
humano:     2 vícios removidos, nota humana 78 APROVADO
legenda:    rode /ig-legenda em seguida

Responda "ok" para registrar, ou diga o que mudar.
```

7. **Nunca publique.** Esta skill produz roteiro. Alguém grava e posta. No
   "ok", acrescente em `log.md` (mesma pasta do arquivo de voz) a data, a
   fórmula e a primeira linha.

## Texto de tela é outro roteiro

- **Seis palavras ou menos por cartão.** É lido de longe por alguém que ainda
  não está ouvindo.
- **O cartão do gancho está no quadro 1**, não depois de um segundo de silêncio.
- **Zona segura.** Num quadro 1080x1920, nada acima de y=230 nem abaixo de
  y=1440, e os 230 pixels da direita livres. A interface cobre o resto.
- **Legenda queimada no corpo.** A maioria assiste sem som primeiro.

## Regras que fazem diferença

- **Uma ideia por Reel.** Duas ideias são dois Reels. Diga isso.
- **Número em vez de adjetivo.** "R$ 7.300 abaixo da FIPE" ganha de "bem
  barato". Se o número não foi dado, pergunte em vez de escrever em volta.
- **Corte a introdução.** Sem "oi pessoal", sem "neste vídeo", sem vinheta.
- **FIPE sempre com mês.** "14% abaixo da FIPE de outubro". FIPE sem mês é o
  primeiro comentário que derruba a credibilidade.
- **Nunca invente.** Nenhum carro, preço, cliente, tempo no ar ou resultado
  inventado, nem como exemplo. Se falta o número, deixe `{{seu número}}` no
  roteiro e avise.
- **Nada de dado pessoal de vendedor.** Sem nome, telefone ou placa do anúncio
  na tela. Mostre o carro e o dado de mercado.
- **Não destaque anúncio como se fosse da Hoov.** A Hoov agrega; o anúncio é
  do portal. Cite a fonte ("anúncio na Webmotors") quando mostrar o print.
