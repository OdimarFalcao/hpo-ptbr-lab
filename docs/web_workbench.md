# Bancada web — especificação e operação

## Decisão de 09/09/2026

React + TypeScript + Vite apresenta a bancada; FastAPI adapta o núcleo Python existente. Streamlit permanece como área de pesquisa e referência. Esta entrega não muda métodos, resultados ou datasets e não executa holdouts.

## Direção visual aprovada

Identidade grafite (#102529), azul-petróleo (#125C64) e ciano (#89E2DC), com bancada clara (#F4F6F5), texto #203438 e bordas #D7E0DE. Tipografia de sistema, ícones Phosphor, espaçamento base de 8 px, painéis com raio de 16 px. A referência escura enviada inspira a identidade, não uma cópia da marca nem uma página promocional.

Desktop: navegação lateral escura, cabeçalho compacto e bancada em duas colunas; texto e menções à esquerda, revisão à direita. Celular: navegação compacta e painéis empilhados. Nenhuma animação decorativa contínua. Destaques e estados têm texto e não dependem apenas de cores.

## Contrato de revisão

Cada menção começa pendente. Candidato e contexto são sugestões até o revisor incluir ou descartar. Alterar conceito, contexto ou caracterização devolve a menção para pendente. Alterar a descrição invalida a análise inteira. Substituições por sobreposição exigem confirmação visível. Exportação só permite decisões resolvidas e preserva `hpo-ptbr-review-v1`.

A caracterização por fenótipo cobre idade/início, gravidade, evolução, frequência, lateralidade e histórico familiar. Campo vazio é exportado como `null` e também aparece em `pending_characterization`; selecionar “desconhecido” registra uma resposta explícita. Lateralidade oferece “não se aplica”. A interface e o JSON mantêm contexto da menção separado de histórico familiar como característica.

Offsets são índices Unicode por ponto de código, como em Python, não posições UTF-16. O frontend usa `Array.from` para converter e recortar. Nenhum texto é salvo em banco, disco, armazenamento do navegador ou telemetria; o JSON é baixado somente por ação explícita. Recarregar a aba perde a revisão.

## Validação prevista

Compatibilidade API/núcleo; revisão manual e contexto; offsets com espaços, acentos, quebras de linha e caracteres fora do BMP; exportação determinística; ausência de SapBERT; erros de rede; testes existentes; build; inspeção desktop/celular. A meta de cinco minutos depende de teste humano de Odimar, não de automação.

## API local

- `GET /api/health`: snapshot e contagens; `GET /api/examples`: textos sintéticos sem alvos ouro.
- `POST /api/analyze`: `{text, top_k}` retorna versão, menções e latência; detector lexical inalterado.
- `POST /api/mentions`: `{text, start, end, top_k}` retorna menção manual com contexto sugerido e rankings.
- `POST /api/search`: `{query, top_k}` preserva a busca por rótulo português/HPO ID e acrescenta resultados suplementares de rótulos e sinônimos oficiais HPO. Cada candidato informa idioma, fonte e estado do rótulo PT; termos ingleses não são traduções.
- `GET /api/concepts/{hpo_id}`: definição oficial disponível, sinônimos, pais, filhos e caminho determinístico.
- `POST /api/semantic`: `{text, start, end, top_k}` consulta opcional por trecho; HTTP 503 mantém o fluxo lexical utilizável.
- `POST /api/export`: `{text, data_version, reviews}` valida e gera `hpo-ptbr-review-v1` com proveniência terminológica. Pendentes, IDs desconhecidos, trechos inconsistentes e sobreposições são rejeitados; campos clínicos não informados permanecem como pendências explícitas.

O adaptador corrige o deslocamento causado pelo `strip()` interno do detector, recolocando os espaços iniciais nos offsets; não altera ranking ou segmentação. O frontend converte Unicode explicitamente. Inclusões e descartes só entram no JSON após ação humana; trocar candidato/contexto volta a pendente.

O servidor é stateless para textos e revisões. Apenas snapshot, rankers e modelo opcional ficam em cache. Respostas são `no-store`; origem e Host são limitados; POST exige JSON e tem limite de 256 KiB. Mensagens de validação não ecoam conteúdo. O launcher usa apenas loopback e desliga access logs da API. Sem autenticação: esta configuração é exclusivamente local, não adequada a exposição em rede. A revisão não constitui validação clínica nem comprovação de fidelidade contra um cliente malicioso.

## Execução e desenvolvimento

Instale `requirements-web.txt`, execute `npm ci` e `npm run build` em `web/`, depois `.\.venv\Scripts\python.exe scripts/run_web.py` na raiz. Portas: 8000 (API + frontend compilado), 8504 (Streamlit). Ctrl+C encerra os processos iniciados pelo launcher. Ele recusa portas ocupadas em vez de assumir controle de processos existentes.

Para desenvolvimento: execute a API com `PYTHONPATH=src` e `python -m uvicorn hpo_ptbr.web_api:app --host 127.0.0.1 --port 8000 --no-access-log`; em outro terminal, `npm run dev` em `web/` serve em 5173 com proxy local. Nunca usar `--host 0.0.0.0` nesta versão.

Testes: `python -m pytest tests/test_web_api.py -q`, `npm test`, `npm run build`, `python -m pytest -q`, `python scripts/check_dashboard_readiness.py`, `git diff --check`. CI separa testes Python leves e testes/build frontend; não carrega SapBERT nem executa holdouts.

## Conceitos de engenharia aplicados

- Separação de responsabilidades: interface React, contrato HTTP e lógica científica Python independente.
- Máquina de estados: pendente → incluída/descartada; alterações invalidam confirmação.
- Testes de contrato e regressão: API retorna os mesmos rankings do núcleo, mesmo com Unicode.
- Privacidade por minimização: nenhum armazenamento automático e nenhuma integração externa.
- Controle de concorrência: respostas de análise anteriores são ignoradas após mudança do texto.

Referências técnicas: [React](https://react.dev/learn), [FastAPI](https://fastapi.tiangolo.com/), [Vite](https://vite.dev/guide/), [Testing Library](https://testing-library.com/docs/react-testing-library/intro/). Não são novas referências metodológicas clínicas.
