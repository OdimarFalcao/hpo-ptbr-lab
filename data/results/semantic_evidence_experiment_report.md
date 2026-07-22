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

- Artigo do SapBERT: <https://arxiv.org/abs/2010.11784>.
- Extensão multilíngue: <https://arxiv.org/abs/2105.14398>.
- Modelo fixado: <https://huggingface.co/cambridgeltl/SapBERT-UMLS-2020AB-all-lang-from-XLMR>.

## Reprodução

```powershell
python scripts/run_semantic_evidence_experiment.py --encoder generic --threshold 0.8
python scripts/run_semantic_evidence_experiment.py --encoder sapbert --threshold 0.8
```

Os detalhes por alvo, todas as previsões e os metadados ficam em `data/results/semantic_evidence_sapbert_details.csv`, `data/results/semantic_evidence_sapbert_predictions.csv` e `data/results/semantic_evidence_sapbert_metadata.json`.
