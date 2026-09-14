# Agregação por palavra no detector de menções

## Objetivo

Avaliar se a fragmentação produzida pelo tokenizer WordPiece pode ser reduzida por uma agregação geral por palavra, sem alterar o modelo, adicionar vocabulário clínico específico ou executar qualquer holdout.

## Transparência metodológica

Esta configuração foi especificada depois de um dry-run exploratório nos dez casos de desenvolvimento. Portanto, seu resultado não estima generalização e não é tratado como pré-registro cego. O resultado negativo original com decodificação BIOES permanece preservado.

## Agregação

- Somar as probabilidades BIOES dentro dos grupos `O`, `PROBLEM`, `TREATMENT` e `TEST`.
- Calcular a média por grupo entre subpalavras com o mesmo `word_id`.
- Selecionar o grupo de maior score, com `O` vencendo empates exatos.
- Descartar tokens formados apenas por pontuação.
- Unir palavras consecutivas `PROBLEM` somente quando separadas por espaço ou hífen.
- Não aplicar limiar, regras clínicas ou linking HPO.

## Avaliação

A métrica primária é F1 de span exato. Métricas secundárias: precisão e recall exatos, F1 relaxado com IoU ≥ 0,5, recall das cinco paráfrases críticas, offsets inválidos e latência.

Os gates exploratórios permanecem os mesmos do candidato original: recall exato ≥ 90%, precisão exata ≥ 85%, pelo menos quatro das cinco paráfrases críticas e zero offsets inválidos. Passar nesses critérios não promoveria automaticamente o método ao dashboard.

## Resultado de desenvolvimento

- 31 previsões válidas para 30 menções ouro.
- Precisão exata: 64,52%.
- Recall exato: 66,67%.
- F1 exato: 65,57%.
- F1 relaxado: 78,69%.
- Recall das paráfrases críticas: 40,00% (2/5).
- Zero offsets inválidos.
- Latência média local: 132,470 ms.

O método melhorou substancialmente o resultado original fragmentado, mas reprovou os gates. Ele permanece offline, sem linking HPO, sem holdout e fora da bancada.
