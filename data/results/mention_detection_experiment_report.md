# Experimento 3 — detecção independente de menções

## Objetivo

Avaliar detecção de trechos clínicos antes do linking HPO. O protocolo foi publicado no commit `ae84fc9` antes do download do modelo. A execução usou somente os dez casos sintéticos de desenvolvimento e não leu o holdout.

## Configuração congelada

- Modelo: `HUMADEX/portugese_medical_ner`.
- Revisão: `51368a80d5b81aa211199aa1988574869197f288`.
- Pesos: `model.safetensors`, SHA-256 `4769703ed392083116fa2fbbf012095f8fccfbdf264880494e11e0be06dd82e0`.
- Classe aceita: `PROBLEM`.
- Decodificação: maior logit por token no esquema BIOES.
- Limiar adicional: nenhum.
- Dados: 10 casos, 30 menções e 5 paráfrases críticas.

## Resultado

| Métrica | Resultado |
|---|---:|
| Previsões válidas | 112 |
| Precisão de trecho exato | 0,00% |
| Recall de trecho exato | 0,00% |
| F1 de trecho exato | 0,00% |
| F1 relaxado, IoU ≥ 0,5 | 11,27% |
| Recall exato nas paráfrases críticas | 0,00% |
| Previsões com offsets inválidos | 0 |
| Latência média | 48,244 ms |
| Critério para avançar | Reprovado |

## Análise do erro

O modelo produziu fragmentos de WordPiece como entidades isoladas, por exemplo “f”, “ra”, “quez” e “a” dentro de “fraqueza”. Nenhuma das 112 previsões coincidiu exatamente com uma menção de ouro. Apenas oito das 30 menções tiveram algum fragmento com IoU ≥ 0,5.

A configuração respeitou o protocolo: pesos fixados, classe `PROBLEM`, argmax BIOES e ausência de limiar ajustável. Mesclar retrospectivamente fragmentos `S-PROBLEM` após observar o resultado constituiria uma nova regra de decodificação e exigiria outro protocolo, não uma correção silenciosa desta execução.

## Decisão

O detector foi reprovado e não seguirá para linking HPO, dashboard ou holdout. O resultado não demonstra que NER é inadequado para a tarefa; demonstra que este modelo e esta decodificação congelada são incompatíveis com os textos de desenvolvimento.

Um próximo candidato deverá usar tokenizer e treinamento clínico nativos de português, possuir classe compatível com problemas ou sinais e sintomas e ser pré-registrado antes da execução. Não será ajustado limiar nem criada regra de junção usando estes resultados.

## Reprodução

```powershell
python scripts/download_mention_model.py
$env:HF_HUB_OFFLINE='1'
$env:TRANSFORMERS_OFFLINE='1'
python scripts/run_mention_detection_experiment.py
```

Os hashes ficam em `data/results/mention_detection_model_manifest.json`. Predições, resumo e metadados ficam em `data/results/mention_detection_ner_predictions.csv`, `data/results/mention_detection_ner_summary.json` e `data/results/mention_detection_ner_metadata.json`.
