# Experimento 2 — detecção semântica de evidências

Data da execução inicial: 2026-07-21. Execução SapBERT: 2026-07-22.

## Objetivo

Avaliar se um encoder semântico consegue localizar automaticamente trechos fenotípicos em descrições sintéticas, incluindo as paráfrases que o detector lexical não recupera. Esta avaliação usa somente os dez cenários de desenvolvimento com 30 menções; o holdout congelado não é lido.

## Baseline com encoder genérico

Modelo: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`, revisão `e8f8c211226b894fcb81acc59f3b34ba3efd5f42`, limiar `0.8` e janelas de até seis tokens.

| Métrica | Resultado |
|---|---:|
| Recall de trecho exato | 66,67% (20/30) |
| Precisão dos trechos previstos | 43,48% (20/46) |
| HPO Accuracy@1 | 63,33% (19/30) |
| HPO Accuracy@5 | 63,33% (19/30) |
| Taxa de HPO ID inválido | 0,00% |
| Latência média | 342,394 ms |

O método não recuperou nenhuma das cinco paráfrases críticas: “pálpebra caída”, “olhos desalinhados”, “perda de audição de um lado”, “fraqueza próxima ao tronco” e “tosse persistente”. Além disso, produziu 26 previsões sem coincidência com os offsets do ouro. O encoder genérico permanece fora do dashboard.

## Resultado com SapBERT-XLMR

Modelo: `cambridgeltl/SapBERT-UMLS-2020AB-all-lang-from-XLMR`, revisão `5731ee8d59538ce6557641b97ed5c83f4237dd06`, SHA-256 `a5102c2c09ac7fd04b685251bd467cf29f9d883c1fd97d5c09268b9e216ea243`, limiar `0.8` e janelas de até seis tokens. O SapBERT foi projetado para *biomedical entity linking* e alinha representações de sinônimos provenientes do UMLS, enquanto o modelo anterior é um encoder geral de paráfrases.

| Métrica | Resultado |
|---|---:|
| Recall de trecho exato | 83,33% (25/30) |
| Precisão dos trechos previstos | 96,15% (25/26) |
| HPO Accuracy@1 | 83,33% (25/30) |
| HPO Accuracy@5 | 83,33% (25/30) |
| Taxa de HPO ID inválido | 0,00% |
| Latência média | 1.503,698 ms |

O SapBERT recuperou corretamente “perda de audição de um lado” como `HP:0009900` (Surdez unilateral), mas não recuperou “pálpebra caída”, “olhos desalinhados”, “fraqueza próxima ao tronco” ou “tosse persistente”. Também não recuperou a variação ortográfica “nistágmo”. A única previsão excedente foi o subtrecho “tosse”, associado ao conceito mais geral `HP:0012735` (Tosse) dentro de “tosse persistente”.

Em relação ao encoder genérico, houve ganho de 16,66 pontos percentuais no recall exato, 52,67 pontos na precisão e 20 pontos em HPO Accuracy@1. Entretanto, apenas uma das cinco paráfrases críticas foi resolvida, com aumento da latência média e peso local de 1,11 GB. A decisão é manter o SapBERT fora do dashboard e avaliar uma combinação lexical-semântica no desenvolvimento antes de qualquer integração.

## Híbrido lexical + SapBERT

A fusão usa união determinística por offsets: duplicatas preservam a previsão lexical e conflitos sobrepostos preservam o trecho mais longo. Scores lexicais e semânticos não são somados porque não são calibrados na mesma escala.

| Métrica | Resultado |
|---|---:|
| Recall de trecho exato | 86,67% (26/30) |
| Precisão dos trechos previstos | 92,86% (26/28) |
| HPO Accuracy@1 | 86,67% (26/30) |
| HPO Accuracy@5 | 86,67% (26/30) |
| Taxa de HPO ID inválido | 0,00% |
| Latência média | 2.042,533 ms |

O híbrido preservou a variação “nistágmo” recuperada pelo lexical e acrescentou duas contribuições semânticas corretas: “estrabizmo” → `HP:0000486` e “perda de audição de um lado” → `HP:0009900`. Permaneceram sem correspondência “pálpebra caída”, “olhos desalinhados”, “fraqueza próxima ao tronco” e “tosse persistente”. Os dois excedentes foram “próxima” → `HP:0012840` e “tosse” → `HP:0012735`, ambos subtrechos de paráfrases maiores.

O resultado supera cada detector isolado no desenvolvimento, mas resolve apenas uma das cinco paráfrases críticas e adiciona dependência de 1,11 GB com latência média superior a dois segundos. A decisão permanece: não integrar ao dashboard. O próximo experimento deve avaliar um índice SapBERT bilíngue com rótulos HPO em português e inglês, mantendo o mesmo conjunto de desenvolvimento e sem reutilizar o holdout.

## Índice SapBERT bilíngue PT+EN

Para cada HPO ID, foram codificados separadamente `label_pt` e `label_en`; o score do conceito foi o maior entre os dois rótulos. O modelo, revisão, limiar e casos permaneceram idênticos.

| Métrica | Resultado |
|---|---:|
| Recall de trecho exato | 83,33% (25/30) |
| Precisão dos trechos previstos | 96,15% (25/26) |
| HPO Accuracy@1 | 83,33% (25/30) |
| HPO Accuracy@5 | 83,33% (25/30) |
| Taxa de HPO ID inválido | 0,00% |
| Latência média | 1.371,089 ms |

O índice bilíngue reproduziu os mesmos acertos e erros do índice somente em português: recuperou “perda de audição de um lado”, mas não recuperou as outras quatro paráfrases críticas e também perdeu “nistágmo”. O único excedente continuou sendo “tosse” → `HP:0012735`. Adicionar apenas o rótulo inglês não trouxe ganho; essa variante permanece fora do dashboard.

O próximo teste de recuperação deve utilizar sinônimos oficiais do snapshot HPO como aliases adicionais. Isso amplia a superfície lexical com uma fonte pública e versionada, sem inventar equivalências portuguesas e sem tocar no holdout.

## Índice SapBERT com aliases oficiais HPO

Foram extraídos 8.921 sinônimos ingleses com predicado `hasExactSynonym` do mesmo snapshot HPO, após excluir duplicatas, rótulos idênticos e tipos marcados como obsoletos ou requisitos alélicos. Os aliases cobrem 4.085 dos 7.158 conceitos traduzidos (57,07%). Para cada HPO ID, o score foi o maior entre o rótulo português e seus aliases. Modelo, revisão, limiar e desenvolvimento permaneceram fixos; o holdout não foi lido.

| Métrica | Resultado |
|---|---:|
| Recall de trecho exato | 86,67% (26/30) |
| Precisão dos trechos previstos | 96,30% (26/27) |
| HPO Accuracy@1 | 83,33% (25/30) |
| HPO Accuracy@5 | 86,67% (26/30) |
| Taxa de HPO ID inválido | 0,00% |
| Latência média | 1.410,710 ms |

Em relação ao SapBERT somente com rótulos portugueses, o índice detectou “olhos desalinhados” e colocou o alvo `HP:0000486` na segunda posição, elevando recall de trecho e Accuracy@5 em 3,34 pontos percentuais. Não houve ganho em Accuracy@1. Permaneceram sem detecção “pálpebra caída”, “fraqueza próxima ao tronco”, “tosse persistente” e a variação “nistágmo”; o único excedente continuou sendo “tosse” → `HP:0012735`.

O resultado mostra que aliases oficiais ampliam a superfície de recuperação, mas o ganho foi insuficiente para a utilidade pretendida e inferior ao híbrido lexical + SapBERT em Accuracy@1. A variante permanece offline e fora do dashboard. O próximo incremento técnico deve abandonar novas combinações de índice e concentrar-se na segmentação contextual e na apresentação de alternativas ao profissional, preservando os erros como evidência experimental.

## Ablação de fronteiras textuais

A variante `boundary-alias-sapbert` manteve modelo, aliases, limiar e Top-5 do experimento anterior, alterando somente a geração de janelas: nenhum trecho pode atravessar vírgula, ponto e vírgula, dois-pontos, ponto, exclamação, interrogação ou quebra de linha. Não foram introduzidos verbos, regras clínicas ou expressões específicas dos casos sintéticos.

| Métrica | Resultado |
|---|---:|
| Janelas candidatas | 356, contra 491 sem fronteiras (−27,49%) |
| Recall de trecho exato | 86,67% (26/30) |
| Precisão dos trechos previstos | 96,30% (26/27) |
| HPO Accuracy@1 | 83,33% (25/30) |
| HPO Accuracy@5 | 86,67% (26/30) |
| Taxa de HPO ID inválido | 0,00% |
| Latência média | 1.781,133 ms |

As previsões, os rankings e os erros foram os mesmos do índice com aliases; houve apenas diferença de `0,000001` no score arredondado de “miopia”, compatível com variação numérica da inferência. A redução determinística de 135 janelas não produziu ganho de qualidade nem de latência nesta execução. Portanto, a hipótese é negativa e a variante não será integrada ao dashboard. Uma evolução real de detecção exigirá um detector de menções separado do ranking terminológico, em vez de novas regras sobre as mesmas janelas.

- Artigo do SapBERT: <https://arxiv.org/abs/2010.11784>.
- Extensão multilíngue: <https://arxiv.org/abs/2105.14398>.
- Modelo fixado: <https://huggingface.co/cambridgeltl/SapBERT-UMLS-2020AB-all-lang-from-XLMR>.

## Reprodução

```powershell
python scripts/run_semantic_evidence_experiment.py --encoder generic --threshold 0.8
python scripts/run_semantic_evidence_experiment.py --encoder sapbert --threshold 0.8
python scripts/build_aliases.py
python scripts/run_semantic_evidence_experiment.py --encoder alias-sapbert --threshold 0.8
python scripts/run_semantic_evidence_experiment.py --encoder boundary-alias-sapbert --threshold 0.8
```

Os detalhes por alvo, todas as previsões e os metadados ficam em `data/results/semantic_evidence_sapbert_details.csv`, `data/results/semantic_evidence_sapbert_predictions.csv` e `data/results/semantic_evidence_sapbert_metadata.json`.

Os artefatos do híbrido ficam em `data/results/semantic_evidence_hybrid_sapbert_details.csv`, `data/results/semantic_evidence_hybrid_sapbert_predictions.csv`, `data/results/semantic_evidence_hybrid_sapbert_summary.json` e `data/results/semantic_evidence_hybrid_sapbert_metadata.json`.

Os artefatos do índice bilíngue ficam em `data/results/semantic_evidence_bilingual_sapbert_details.csv`, `data/results/semantic_evidence_bilingual_sapbert_predictions.csv`, `data/results/semantic_evidence_bilingual_sapbert_summary.json` e `data/results/semantic_evidence_bilingual_sapbert_metadata.json`.

Os aliases versionados ficam em `data/processed/hpo_exact_synonyms_en.csv` e `data/processed/hpo_exact_synonyms_en_metadata.json`. Os artefatos do índice com aliases ficam em `data/results/semantic_evidence_alias_sapbert_details.csv`, `data/results/semantic_evidence_alias_sapbert_predictions.csv`, `data/results/semantic_evidence_alias_sapbert_summary.json` e `data/results/semantic_evidence_alias_sapbert_metadata.json`.

Os artefatos da ablação por fronteiras ficam em `data/results/semantic_evidence_boundary_alias_sapbert_details.csv`, `data/results/semantic_evidence_boundary_alias_sapbert_predictions.csv`, `data/results/semantic_evidence_boundary_alias_sapbert_summary.json` e `data/results/semantic_evidence_boundary_alias_sapbert_metadata.json`.
