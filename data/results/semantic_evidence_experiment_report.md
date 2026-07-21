# Experimento 2 — detecção semântica de evidências

Data da execução inicial: 2026-07-21.

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

## Próximo encoder experimental

O próximo teste utilizará `cambridgeltl/SapBERT-UMLS-2020AB-all-lang-from-XLMR`, revisão `5731ee8d59538ce6557641b97ed5c83f4237dd06`. O SapBERT foi projetado para *biomedical entity linking* e alinha representações de sinônimos provenientes do UMLS, enquanto o modelo anterior é um encoder geral de paráfrases.

- Artigo do SapBERT: <https://arxiv.org/abs/2010.11784>.
- Extensão multilíngue: <https://arxiv.org/abs/2105.14398>.
- Modelo fixado: <https://huggingface.co/cambridgeltl/SapBERT-UMLS-2020AB-all-lang-from-XLMR>.

O peso de 1,11 GB não foi concluído em 21/07 porque a transferência local estimou mais de duas horas. O código, a revisão e os testes estão prontos, mas não há resultado SapBERT a declarar. A execução será retomada sem alterar o holdout.

## Reprodução

```powershell
python scripts/run_semantic_evidence_experiment.py --encoder generic --threshold 0.8
python scripts/run_semantic_evidence_experiment.py --encoder sapbert --threshold 0.8
```
