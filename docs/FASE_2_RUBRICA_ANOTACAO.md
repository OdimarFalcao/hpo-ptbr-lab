# Fase 2 — rubrica de anotação do padrão-ouro

Status: implementada para o conjunto sintético de desenvolvimento; revisão clínica pendente.

## Unidade de anotação

Cada unidade liga uma evidência textual contínua a, no máximo, um conceito HPO e a um contexto. O anotador deve conservar o menor trecho que ainda sustenta o achado. Modificadores temporais ou familiares podem permanecer fora do span, mas precisam estar refletidos no contexto e na caracterização.

1. **Menção textual:** transcrever exatamente o trecho e registrar offsets de início inclusivo e fim exclusivo. Não reescrever a frase no campo de menção.
2. **Conceito HPO:** selecionar um HPO ID existente no snapshot congelado. O rótulo português copiado para o padrão-ouro deve coincidir com o snapshot; quando ausente, usar `null`, nunca uma tradução inventada.
3. **Contexto:** escolher `present`, `absent`, `uncertain` ou `family_history`. Histórico familiar prevalece quando o achado pertence somente a familiar; contraste com a pessoa avaliada deve ser descrito no limite da evidência.
4. **Limite da evidência:** registrar o que o trecho não permite concluir — etiologia, confirmação instrumental, subtipo, distribuição ou diagnóstico, por exemplo.
5. **Especificidade:** registrar um grau descritivo e justificar por que o conceito é sustentado, provisório, inferido de função ou limitado a um domínio. Não escolher descendente mais específico sem evidência textual.
6. **Informações ausentes:** avaliar `onset_age`, `severity`, `evolution`, `frequency`, `laterality` e `family_history`. Valores presentes vão em `characterization`; campos não sustentados ficam `null` e aparecem em `information_absent`.

## Regras de adjudicação

- Duas interpretações HPO plausíveis tornam o caso pendente; não se força consenso automático.
- Inferência a partir de função deve ser marcada e revisada por especialista clínico.
- Erro de grafia ou abreviação é preservado no texto e não corrigido silenciosamente no padrão-ouro.
- Uma paráfrase sintética é evidência de teste, não sinônimo oficial nem tradução validada.
- Achados administrativos sem fenótipo formam controles negativos. Sintomas reais, mesmo irrelevantes para uma hipótese diagnóstica, continuam sendo fenótipos e não devem ser usados como controles fáceis.
- O padrão-ouro técnico só se torna clinicamente validado após dupla anotação independente, adjudicação e registro dos responsáveis e da versão.

## Carga e tempo de revisão

O executor aceita, opcionalmente, uma lista JSON local com `case_id`, `elapsed_seconds` e `correction_actions`. Esse arquivo é fornecido conscientemente pelo estudo, não é capturado pela interface nem armazenado automaticamente. Na ausência dele, apenas um proxy computacional de componentes de correção é reportado, sem convertê-lo em tempo humano.

## Uso dos conjuntos

- **Desenvolvimento:** pode ser executado repetidamente para análise de erros.
- **Validação:** será criado por autoria independente e usado para selecionar mudanças já propostas.
- **Holdout:** será guardado sem acesso durante desenvolvimento e validação e executado somente depois do congelamento final do método.

O registro em `data/eval/phase2_split_registry.json` mantém validação e holdout deliberadamente sem textos ou conceitos-alvo nesta implementação. Isso evita apresentar como holdout um conjunto conhecido por quem está desenvolvendo o sistema.
