---
name: ig-humano
description: Tira a cara de texto de máquina de qualquer rascunho em português - travessões, vícios de vocabulário, folheto de concessionária, caracteres invisíveis - e dá nota antes de sair. Use para humanizar, "parece IA", ou antes de mostrar legenda, roteiro, comentário ou direct.
---

# ig-humano (PT-BR)

Duas ferramentas rodam nesta pasta. Use as duas. Não faça no olho.

```bash
python3 humanize.py rascunho.txt --report        # limpa e mostra o que mudou
python3 detect.py rascunho.txt                    # nota em cinco checagens
python3 detect.py antes.txt depois.txt            # prova a diferença
```

As duas leem `vicios.json`: palavras e expressões com troca em português
simples, 18 classes de caractere invisível, 11 trocas tipográficas e 19
estruturas. Dois blocos são específicos: `instagram` (vício de legenda e
locução) e `carro` (folheto de concessionária: "carro dos seus sonhos",
"ofertas imperdíveis", "venha conferir"). O arquivo é para ser editado. Se o
usuário usa de propósito uma palavra que o léxico apaga, tire do arquivo.

"Insights" não está no léxico de propósito: é nome de produto da Hoov.

## O que é corrigido sozinho

1. **Caracteres invisíveis.** Espaço de largura zero, juntores, hífen suave,
   BOM, caracteres de tag Unicode, espaço não separável.
2. **Tipografia.** Travessão vira vírgula, aspas curvas viram retas,
   reticências de um caractere viram três pontos.
3. **Vocabulário.** "No cenário atual", "vale ressaltar que", "além disso,",
   "potencializar", "ecossistema", "inovador", "imperdível", "corre que é por
   pouco tempo", "me segue pra mais". Links, @menções e #hashtags não são
   tocados.

## O que é apontado e NÃO corrigido

Mudar o formato da frase pede julgamento. Isso volta para você reescrever:

- "Não é só X, é Y" e "não apenas X, mas também Y"
- "O resultado?" sozinho numa linha
- tríade de três itens
- lista com ✅ no lugar de marcador
- parede de hashtag (6 ou mais; o limite do Instagram é 5)
- isca de seguir, marcar amigo ou curtir
- urgência fabricada ("corre que", "não perca")
- pontuação em série (!!!)
- três palavras em caixa alta seguidas (FIPE, IPVA e SUV não contam)
- frases todas do mesmo tamanho

## O painel de cinco checagens

| checagem | mede | o que derruba |
| --- | --- | --- |
| RITMO | variação do tamanho das frases | tudo do mesmo tamanho |
| CONCRETO | preço, FIPE, modelo, km, cidade a cada 100 palavras | texto abstrato |
| VÍCIOS | densidade de termos do léxico | "no cenário atual" |
| DIGITAL | invisíveis, travessões, aspas curvas | tipografia perfeita demais |
| VOZ | marcas de fala (pra, tá, né, a gente), pronomes, estruturas | voz de folheto |

APROVADO pede nota 70+ e nenhuma checagem abaixo de 55. Isto não é GPTZero
nem Turnitin e não chama esses serviços. Nunca diga que o texto está
"indetectável".

## O ciclo

1. `humanize.py --report` no rascunho.
2. Reescreva cada estrutura apontada, à mão, na voz do usuário.
3. `detect.py antes.txt depois.txt`. Se não estiver APROVADO, corrija o sinal
   mais fraco e rode de novo.
4. Entregue o texto limpo e uma linha: quantas marcas saíram, nota antes e
   depois.

## Não invente para passar

Se CONCRETO está baixo, a correção é um número real do anúncio ou do
monitoramento, não um número inventado. Faltou o dado, deixe `{{número}}`
e avise.
