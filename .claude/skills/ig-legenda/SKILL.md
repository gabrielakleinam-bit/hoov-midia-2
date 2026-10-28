---
name: ig-legenda
description: Escreve e revisa a legenda de Instagram em português - a linha que sobrevive ao corte do "... mais", o pedido único, os termos de busca, até 5 hashtags e as regras de FIPE da Hoov. Use para legenda, caption, hashtags.
---

# ig-legenda (PT-BR)

Uma ferramenta roda nesta pasta:

```bash
python3 legenda.py legenda.txt
python3 legenda.py legenda.txt --keywords "hb20 usado,carro abaixo da fipe"
python3 legenda.py legenda.txt --preco 45100 --fipe 52400
```

Ela imprime a legenda como o feed imprime: os primeiros 125 caracteres numa
caixa, o resto atrás do toque. Leia a caixa antes de qualquer outra coisa.

## Primeiro, qual é o trabalho desta legenda

**Trabalho A: o vídeo já fisgou.** O Reel tem o próprio gancho nos dois
primeiros segundos. A legenda não é um segundo gancho. O trabalho dela é o
pedido, o contexto que faz o pedido fazer sentido e as palavras que as pessoas
buscam.

**Trabalho B: a legenda é o conteúdo.** Foto, imagem única, capa de
carrossel. Aqui a linha 1 é o gancho e funciona como gancho de Reel: concreta,
curta e cortada num suspense, não no meio de uma oração.

Diga qual dos dois está escrevendo. Para o garimpo do dia em card estático,
é B: a primeira linha é modelo, ano, preço e cidade.

## O formato

```
Linha 1     125 caracteres visíveis. A: o pedido, direto. B: o gancho.
            Nunca saudação, nunca hashtag, nunca emoji como primeiro caractere.
Corpo       parágrafos curtos, uma linha em branco entre eles. Dois a seis.
            Aqui moram os termos de busca.
O pedido    um só. Na Hoov, quase sempre: criar o alerta do mesmo carro.
Hashtags    até cinco, numa linha no fim, ou nenhuma.
```

## Regras da Hoov (o script confere)

- **FIPE sempre com o mês.** Falou em FIPE com preço ou porcentagem, diga o
  mês de referência: "FIPE de outubro". Sem isso o script reprova.
- **Desvio de 30% ou mais pede aviso.** Golpe e sinistro também aparecem como
  ótimo negócio. Inclua: conferir histórico e vistoria, nunca pagar Pix antes
  de ver o carro. Sem isso o script reprova.
- **O sinaleiro tem que bater com a conta.** Rode com `--preco` e `--fipe` do
  anúncio. Se a legenda disser "14% abaixo" e a conta der 12%, ou chamar de
  "ótimo negócio" algo que está na faixa "bom negócio", o script reprova.
  Faixas (desvio = preço / FIPE − 1): ÓTIMO até −15%, BOM de −15% a −5%,
  MERCADO de −5% a +5%, ACIMA acima de +5%.
- **Sem dado do vendedor.** Nada de nome, telefone ou placa.

## Hashtags

O Instagram limitou a 5 hashtags por post e Reel em 18 de dezembro de 2025.
Hashtag é rótulo, não alavanca de alcance. Use o modelo e a cidade
(`#hb20 #curitiba`), não `#carros #viral #fyp #explore`, que o script marca
como genéricas.

## Termos de busca valem mais que hashtag

A busca do Instagram lê o texto da legenda. O termo que a pessoa digitaria
("hb20 usado curitiba", "carro abaixo da fipe") entra numa frase normal no
corpo. Peça dois ou três termos e passe em `--keywords`.

## Outras regras

- **Sem link na legenda.** Legenda não é clicável. Bio ou direct.
- **Um pedido.** Dois pedidos valem zero. O script conta.
- **Palavra-chave digitável.** "Comenta HB20" funciona. "Comenta 'quero o
  link do carro'" não.
- **Emoji como pontuação, não enfeite.** Mais de 4 a cada 100 caracteres é
  marcado.
- **Texto alternativo** para foto e carrossel. Leitor de tela e o Instagram
  leem.

## O ciclo

1. Decida A ou B e diga qual.
2. Escreva.
3. Passe por `/ig-humano`. Legenda é curta, então vício de texto aparece mais.
4. Rode `legenda.py` com os termos de busca e, se for garimpo, com `--preco` e
   `--fipe`. Corrija toda FALHA. Decida cada AVISO em voz alta.
5. Entregue o bloco pronto para copiar e o recibo:

```
LEGENDA PRONTA
trabalho:   B - card estático do garimpo do dia
visível:    69 de 125 caracteres antes do corte
pedido:     um, criar alerta
hashtags:   3
fipe:       outubro, sinaleiro BOM NEGÓCIO (-13,9%)
revisão:    PRONTA
```

Nada é publicado. Alguém cola e posta.
