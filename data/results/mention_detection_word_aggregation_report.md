# Experimento de agregação WordPiece por palavra

## Pergunta

Uma agregação geral por palavra reduz a fragmentação do modelo `HUMADEX/portugese_medical_ner` nos dez textos sintéticos de desenvolvimento?

## Resultado

| Métrica | Resultado |
|---|---:|
| Precisão exata | 64,52% |
| Recall exato | 66,67% |
| F1 exato | 65,57% |
| F1 relaxado (IoU ≥ 0,5) | 78,69% |
| Recall de paráfrases críticas | 40,00% (2/5) |
| Previsões inválidas | 0 |
| Latência média | 132,470 ms |

## Decisão

O reparo elevou o F1 exato de 0,00% para 65,57%, demonstrando que parte do erro original vinha da fragmentação de subpalavras. Entretanto, precisão, recall e recuperação de paráfrases ficaram abaixo dos gates especificados. O candidato permanece offline, não realiza linking HPO, não foi executado em holdout e não será integrado ao dashboard.

O método foi desenhado após um dry-run no próprio desenvolvimento. Por isso, o resultado serve somente para análise técnica e formulação do próximo candidato; não demonstra generalização ou validade clínica.
