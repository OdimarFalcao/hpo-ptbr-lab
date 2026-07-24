# Protocolo de detecção independente de menções

## Objetivo

Avaliar se um modelo de NER consegue localizar trechos que descrevem problemas clínicos em textos sintéticos em português antes de qualquer tentativa de vinculação à HPO. Esta etapa mede somente detecção de offsets; IDs HPO, ranking e score de linking ficam explicitamente fora da avaliação.

## Candidato pré-registrado

O primeiro candidato é `HUMADEX/portugese_medical_ner`, revisão `51368a80d5b81aa211199aa1988574869197f288`. O modelo possui uma classe `PROBLEM` para doenças, sintomas e condições, usa classificação de tokens e disponibiliza pesos `safetensors`.

A escolha é exploratória. O modelo foi treinado de forma fracamente supervisionada, combinando dados anotados e traduções, e sua métrica publicada não pode ser transferida para nossos textos. Modelos BioBERTpt específicos para classes terapêuticas ou diagnósticos principais não foram escolhidos porque seus rótulos não correspondem à detecção ampla de fenótipos.

Fontes:

- Modelo: <https://huggingface.co/HUMADEX/portugese_medical_ner>
- Artigo associado: <https://doi.org/10.3390/app15105585>
- Alternativa BioBERTpt analisada: <https://huggingface.co/liaad/hfpt-biobertpt-all-er_ner>

## Dados e congelamento

- Usar somente `data/demo/synthetic_review_cases.json`.
- Tratar as 30 menções dos dez casos como ouro de detecção, inclusive as cinco paráfrases que os métodos anteriores não localizaram.
- Não ler nem executar o holdout congelado.
- Não criar exemplos a partir da saída do modelo.
- Não usar dados clínicos reais.

## Inferência fixa

- Baixar somente os arquivos necessários ao tokenizer, configuração e pesos `safetensors`.
- Fixar a revisão do modelo e registrar SHA-256 dos arquivos usados.
- Após o download, executar com `local_files_only=True`.
- Usar tokenizer rápido com offsets.
- Decodificar o maior logit por token no esquema BIOES.
- Manter apenas entidades `PROBLEM`.
- Não aplicar limiar de confiança nem ajustá-lo no desenvolvimento.
- Preservar texto, offsets, classe e score do modelo em artefato separado.

## Métricas

Métrica primária:

- F1 de trecho exato.

Métricas secundárias:

- precisão e recall de trecho exato;
- F1 relaxado com IoU ≥ 0,5;
- recall exato nas cinco paráfrases críticas;
- previsões com offsets inválidos;
- latência média.

O avaliador de menções não calcula Accuracy@K, MRR ou validade de HPO ID, pois essas métricas pertencem à etapa posterior de linking.

## Critério para avançar

O detector poderá seguir para um experimento separado de linking somente se, no desenvolvimento:

- recall exato for pelo menos 90%;
- precisão exata for pelo menos 85%;
- recuperar exatamente ao menos quatro das cinco paráfrases críticas;
- produzir zero previsões com offsets inválidos.

Cumprir esse critério não promove o método ao dashboard, não demonstra validade clínica e não autoriza execução no holdout. Se falhar, o resultado negativo será registrado sem ajuste de limiar no mesmo conjunto.
