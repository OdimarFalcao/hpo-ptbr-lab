import { useEffect, useRef, useState } from 'react'
import { ArrowRight, ArrowSquareOut, BookOpen, Check, Checks, CircleNotch, DownloadSimple, FileText, Flask, Info, MagnifyingGlass, PencilSimple, Plus, ShieldCheck, SquaresFour, Trash, X } from '@phosphor-icons/react'
import { request } from './api'
import ConceptPanel from './ConceptPanel'
import { canExport, changeReview, occurrences, overlaps, pendingCharacterization, pendingReview, points, replaceSpan, sliceText, spanKey, union } from './state'
import { ASSERTIONS, CHARACTERIZATION_LABELS, DECISIONS } from './types'
import type { Assertion, Candidate, Characterization, Example, Health, Review, Span } from './types'

export default function App() {
  const [health, setHealth] = useState<Health | null>(null)
  const [examples, setExamples] = useState<Example[]>([])
  const [text, setText] = useState('')
  const [exampleId, setExampleId] = useState('')
  const [topK, setTopK] = useState(5)
  const [reviews, setReviews] = useState<Review[]>([])
  const [analyzed, setAnalyzed] = useState(false)
  const [editorOpen, setEditorOpen] = useState(true)
  const [active, setActive] = useState('')
  const [busy, setBusy] = useState('')
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [manualOpen, setManualOpen] = useState(false)
  const [phrase, setPhrase] = useState('')
  const [occurrence, setOccurrence] = useState('')
  const [replacementApproved, setReplacementApproved] = useState(false)
  const [search, setSearch] = useState('')
  const [found, setFound] = useState<Candidate[]>([])
  const [searched, setSearched] = useState(false)
  const [technicalMethod, setTechnicalMethod] = useState('Fuzzy')
  const generation = useRef(0)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const reviewRef = useRef<HTMLElement>(null)
  const profileRef = useRef<HTMLElement>(null)
  const manualRef = useRef<HTMLInputElement>(null)
  const exportUrl = useRef<string | null>(null)
  const selected = reviews.find(review => spanKey(review) === active)
  const included = reviews.filter(review => review.decision === 'include')
  const pending = reviews.filter(review => review.decision === 'pending').length
  const completed = reviews.length - pending
  const matches = occurrences(text, phrase)
  const match = matches.find(item => `${item.start}:${item.end}` === occurrence) ?? (matches.length === 1 ? matches[0] : undefined)
  const replaced = match ? overlaps(reviews, match) : []
  const ready = canExport(analyzed, reviews)

  useEffect(() => {
    const controller = new AbortController()
    Promise.all([request<Health>('health', undefined, controller.signal), request<Example[]>('examples', undefined, controller.signal)])
      .then(([status, cases]) => { setHealth(status); setExamples(cases) })
      .catch(error => { if (!controller.signal.aborted) setError(error.message) })
    return () => controller.abort()
  }, [])
  useEffect(() => {
    setSearch(''); setFound([]); setSearched(false); setTechnicalMethod('Fuzzy')
  }, [active])
  useEffect(() => () => { if (exportUrl.current) URL.revokeObjectURL(exportUrl.current) }, [])

  function invalidate(value: string) {
    generation.current += 1
    setText(value); setReviews([]); setAnalyzed(false); setEditorOpen(true); setActive(''); setBusy(''); setError('')
    setPhrase(''); setOccurrence(''); setReplacementApproved(false); setManualOpen(false)
    setNotice(analyzed ? 'Descrição alterada. Localize os fenótipos novamente para iniciar uma nova revisão.' : '')
    if (exportUrl.current) { URL.revokeObjectURL(exportUrl.current); exportUrl.current = null }
  }
  async function run(label: string, work: (current: () => boolean) => Promise<void>) {
    const revision = generation.current
    setBusy(label); setError(''); setNotice('')
    try { await work(() => generation.current === revision) }
    catch (error) { if (generation.current === revision) setError(error instanceof Error ? error.message : 'Não foi possível concluir a operação.') }
    finally { if (generation.current === revision) setBusy('') }
  }
  function choose(review: Review) {
    setActive(spanKey(review)); setFound([])
    reviewRef.current?.focus({ preventScroll: true })
    if (window.matchMedia('(max-width: 700px)').matches) reviewRef.current?.scrollIntoView({ block: 'start' })
  }
  function edit(changes: Partial<Pick<Review, 'selected_hpo_id' | 'assertion' | 'characterization'>>) {
    setReviews(items => items.map(item => spanKey(item) === active ? changeReview(item, changes) : item))
  }
  function characterize(field: keyof Characterization, value: string) {
    if (!selected) return
    edit({ characterization: { ...selected.characterization, [field]: value || null } as Characterization })
  }
  function decide(decision: 'include' | 'discard') {
    setReviews(items => items.map(item => spanKey(item) === active ? { ...item, decision, human_modified: item.human_modified || decision === 'discard' } : item))
    setNotice(decision === 'include' ? 'Menção incluída no perfil. Selecione a próxima menção para continuar.' : 'Menção descartada. Ela permanecerá registrada na exportação.')
  }
  async function analyze() {
    await run('Localizando fenótipos…', async current => {
      const result = await request<{ data_version: string; spans: Span[] }>('analyze', { text, top_k: topK })
      if (!current()) return
      const next = result.spans.map(pendingReview)
      setReviews(next); setAnalyzed(true); setEditorOpen(false); setActive(next[0] ? spanKey(next[0]) : '')
      setNotice(next.length ? `${next.length} menções sugeridas. Revise cada uma antes de exportar.` : 'Nenhuma menção encontrada pelo detector lexical. Você pode adicionar um trecho manualmente.')
    })
  }
  async function addManual() {
    if (!match || (replaced.length && !replacementApproved)) return
    await run('Preparando anotação…', async current => {
      const span = await request<Span>('mentions', { text, ...match, top_k: topK })
      if (!current()) return
      const review = pendingReview(span)
      setReviews(items => replaceSpan(items, review)); setActive(spanKey(review)); setPhrase(''); setOccurrence(''); setReplacementApproved(false)
      setNotice('Trecho adicionado. Confirme o conceito e o contexto antes de incluí-lo.')
    })
  }
  async function searchConcept() {
    await run('Buscando conceitos…', async current => {
      const candidates = await request<Candidate[]>('search', { query: search, top_k: topK })
      if (current()) { setFound(candidates); setSearched(true) }
    })
  }
  function useFound(candidate: Candidate) {
    setReviews(items => items.map(item => spanKey(item) === active ? {
      ...changeReview(item, { selected_hpo_id: candidate.hpo_id }),
      rankings: { ...item.rankings, 'Busca manual': [...(item.rankings['Busca manual'] ?? []).filter(previous => previous.hpo_id !== candidate.hpo_id), candidate] },
    } : item))
    setFound([]); setSearched(false)
  }
  async function semantic() {
    if (!selected) return
    const key = spanKey(selected)
    await run('Consultando SapBERT local…', async current => {
      const candidates = await request<Candidate[]>('semantic', { text, start: selected.start, end: selected.end, top_k: topK })
      if (current()) {
        setReviews(items => items.map(item => spanKey(item) === key ? { ...item, rankings: { ...item.rankings, SapBERT: candidates } } : item))
        setTechnicalMethod('SapBERT')
      }
    })
  }
  async function exportProfile() {
    await run('Validando perfil…', async current => {
      const payload = await request<object>('export', { text, data_version: health?.data_version, reviews })
      if (!current()) return
      if (exportUrl.current) URL.revokeObjectURL(exportUrl.current)
      const url = URL.createObjectURL(new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json;charset=utf-8' }))
      exportUrl.current = url
      const link = document.createElement('a'); link.href = url; link.download = 'hpo-ptbr-perfil-revisado.json'; link.click()
      setNotice('Perfil validado. O download foi solicitado; nenhuma cópia foi salva pelo servidor.')
    })
  }
  function highlighted() {
    let cursor = 0
    const fragments = []
    for (const review of reviews) {
      fragments.push(sliceText(text, cursor, review.start))
      fragments.push(<button key={spanKey(review)} className={`mention-mark ${review.decision} ${active === spanKey(review) ? 'selected' : ''}`} onClick={() => choose(review)} disabled={!!busy} aria-label={`Revisar ${review.text}: ${DECISIONS[review.decision]}`}>{review.text}</button>)
      cursor = review.end
    }
    fragments.push(sliceText(text, cursor))
    return fragments
  }

  return <div className="app-shell">
    <a className="skip-link" href="#workspace">Ir para a bancada</a>
    <aside className="sidebar">
      <a className="brand" href="#workspace" aria-label="HPO-PTBR Lab, bancada"><Flask size={31} weight="duotone" /><span>HPO-PTBR<span className="brand-lab">LAB / PESQUISA</span></span></a>
      <div className="sidebar-caption">ESPAÇO DE TRABALHO</div>
      <nav aria-label="Navegação principal">
        <a href="#workspace" className="nav-active" aria-current="page"><SquaresFour size={20} /> Anotação assistida <ArrowRight size={16} /></a>
        <button onClick={() => profileRef.current?.scrollIntoView({ behavior: 'auto' })}><FileText size={20} /> Perfil fenotípico <span className="nav-count">{included.length}</span></button>
        <a href="http://127.0.0.1:8504" target="_blank" rel="noreferrer"><BookOpen size={20} /> Área de pesquisa <ArrowSquareOut size={16} /></a>
      </nav>
      <div className="sidebar-note"><ShieldCheck size={24} /><h3>Uma bancada, não um diagnóstico.</h3><p>Auxilia a investigação fenotípica. Revise evidências; a decisão profissional é sua.</p></div>
      <div className="sidebar-bottom"><span className="status-dot" /> Execução local<p>Textos apenas nesta sessão.</p><small>HUMAN PHENOTYPE ONTOLOGY</small></div>
    </aside>

    <div className="main-shell">
      <header className="topbar"><span>Bancada de anotação fenotípica</span><span className="version-badge">PROTÓTIPO EXPERIMENTAL</span></header>
      <main id="workspace">
        <div className="page-heading"><div><div className="eyebrow">LINGUAGEM CLÍNICA → CONCEITOS HPO</div><h1>Da descrição ao fenótipo.</h1><p>Localize trechos, revise conceitos e construa um perfil estruturado.</p></div><span className="language-badge">PT-BR <span>/</span> HPO</span></div>
        <div className="safety"><ShieldCheck size={19} /><span><strong>Somente textos sintéticos.</strong> O sistema auxilia a investigação fenotípica, não fornece diagnóstico. Revise todas as sugestões.</span></div>
        <ol className="steps" aria-label="Etapas da anotação"><li className="current"><span>01</span> Descrever</li><li className={analyzed ? 'current' : ''}><span>02</span> Revisar</li><li className={ready ? 'current' : ''}><span>03</span> Exportar</li></ol>
        <div aria-live="polite">{busy && <div className="feedback"><CircleNotch size={19} className="spin" />{busy}</div>}{notice && <div className="feedback"><Info size={19} />{notice}</div>}</div>
        {error && <div role="alert" className="error banner"><Info size={20} /><span>{error}</span>{!health && <button className="secondary" onClick={() => window.location.reload()}>Reconectar</button>}<button className="icon-button" aria-label="Fechar mensagem de erro" onClick={() => setError('')}><X size={18} /></button></div>}

        <div className="workspace-grid">
          <div className="source-column">
            <section className="panel source-panel" aria-labelledby="source-heading">
              <div className="panel-title"><div><span className="section-number">01</span><h2 id="source-heading">Descrição sintética</h2></div>{analyzed ? <button className="text-button" aria-expanded={editorOpen} onClick={() => setEditorOpen(!editorOpen)}><PencilSimple size={16} />{editorOpen ? 'Recolher texto' : 'Editar descrição'}</button> : <FileText size={22} className="muted" />}</div>
              {analyzed && !editorOpen && <p className="source-preview">{points(text).length} caracteres · Texto analisado. Editar o conteúdo inicia uma nova revisão.</p>}
              <div hidden={analyzed && !editorOpen}>
              <label htmlFor="example">Comece com um exemplo</label>
              <select id="example" value={exampleId} disabled={!!busy} onChange={event => { const example = examples.find(item => item.id === event.target.value); setExampleId(event.target.value); invalidate(example?.text ?? '') }}>
                <option value="">Escrever meu próprio texto sintético</option>
                {[...new Set(examples.map(example => example.domain))].map(domain => <optgroup key={domain} label={domain}>{examples.filter(example => example.domain === domain).map(example => <option key={example.id} value={example.id}>{example.title}</option>)}</optgroup>)}
              </select>
              <div className="label-row"><label htmlFor="description">Texto para anotação</label><span className={points(text).length > 1000 ? 'error' : 'muted'}>{points(text).length}/1.000</span></div>
              <textarea ref={inputRef} id="description" value={text} onChange={event => { invalidate(event.target.value); setExampleId('') }} placeholder="Escreva uma descrição inventada ou escolha um dos exemplos acima. Não insira prontuários nem dados pessoais." spellCheck={false} aria-describedby="text-help" />
              <p id="text-help" className="helper">Seu texto não é armazenado. Recarregar a página encerra a revisão.</p>
              <div className="source-actions"><details><summary>Opções de análise</summary><label htmlFor="top-k">Alternativas por método</label><select id="top-k" value={topK} disabled={!!busy || analyzed} onChange={event => setTopK(Number(event.target.value))}>{[1, 3, 5, 10].map(value => <option key={value}>{value}</option>)}</select><p className="helper">Detector lexical fixo. Nenhum modelo semântico é carregado automaticamente.</p></details><button className="primary" disabled={!!busy || !text.trim() || points(text).length > 1000 || !health} onClick={analyze}><MagnifyingGlass size={19} /> Localizar fenótipos</button></div>
              </div>
            </section>

            {analyzed ? <section className="panel" aria-labelledby="evidence-heading">
              <div className="panel-title"><div><h2 id="evidence-heading">Evidências no texto</h2><span className="count">{reviews.length}</span></div><button className="text-button" onClick={() => { setManualOpen(true); setTimeout(() => manualRef.current?.focus(), 0) }} disabled={!!busy}><Plus size={17} /> Adicionar trecho</button></div>
              <p className="helper">Selecione um destaque ou uma menção para revisar.</p>
              <div className="evidence-text">{highlighted()}</div>
              <p className="evidence-note"><Info size={15} /> Sem destaque não significa ausência de fenótipo. Paráfrases podem não ser encontradas.</p>
              <div className="mention-list" aria-label="Menções encontradas">{reviews.map((review, index) => <button key={spanKey(review)} className={`mention-row ${spanKey(review) === active ? 'active' : ''}`} aria-pressed={spanKey(review) === active} disabled={!!busy} onClick={() => choose(review)}><span className="mention-index">{String(index + 1).padStart(2, '0')}</span><span className="mention-name">{review.text}<small>{review.source === 'manual' ? 'Adicionada manualmente' : 'Detecção lexical'}</small></span><span className={`decision ${review.decision}`}>{DECISIONS[review.decision]}</span></button>)}</div>
              {!reviews.length && <div className="empty-small">Nenhuma sugestão automática. Adicione uma menção que exista no texto para iniciar a revisão.</div>}
              <details open={manualOpen} onToggle={event => setManualOpen(event.currentTarget.open)} className="manual-form"><summary><PencilSimple size={17} /> Adicionar ou corrigir limites</summary>
                <label htmlFor="manual-phrase">Copie exatamente uma expressão do texto</label><input ref={manualRef} id="manual-phrase" value={phrase} disabled={!!busy} onChange={event => { setPhrase(event.target.value); setOccurrence(''); setReplacementApproved(false) }} placeholder="Trecho a ser anotado" />
                {phrase.trim() && !matches.length && <p className="helper error">A expressão não foi encontrada. Preserve a grafia e a caixa do texto.</p>}
                {matches.length > 1 && <><label htmlFor="occurrence">Qual ocorrência?</label><select id="occurrence" value={occurrence} disabled={!!busy} onChange={event => { setOccurrence(event.target.value); setReplacementApproved(false) }}><option value="">Selecione pelo contexto</option>{matches.map(item => <option key={item.start} value={`${item.start}:${item.end}`}>{item.start}–{item.end}: {sliceText(text, Math.max(0, item.start - 25), item.start)}[{sliceText(text, item.start, item.end)}]{sliceText(text, item.end, item.end + 25)}</option>)}</select></>}
                {!!replaced.length && <div className="overlap-warning"><p>Esta correção substituirá {replaced.map(item => `“${item.text}”`).join(', ')} e suas decisões atuais.</p><label className="checkbox"><input type="checkbox" checked={replacementApproved} onChange={event => setReplacementApproved(event.target.checked)} />Confirmo a substituição e nova revisão.</label></div>}
                <button className="secondary" disabled={!!busy || !match || (!!replaced.length && !replacementApproved)} onClick={addManual}><Plus size={17} />{replaced.length ? 'Corrigir limites' : 'Adicionar menção'}</button>
              </details>
            </section> : <div className="guide"><span className="guide-icon"><BookOpen size={23} /></span><div><h3>O texto é o ponto de partida.</h3><p>A bancada encontra expressões próximas aos rótulos HPO. Você confere o significado, corrige omissões e decide o que entra no perfil.</p></div></div>}
          </div>

          <section ref={reviewRef} tabIndex={-1} className="panel review-panel" aria-labelledby="review-heading">
            <div className="panel-title"><div><span className="section-number">02</span><h2 id="review-heading">Revisão de conceitos</h2></div><span className="count">{completed}/{reviews.length}</span></div>
            {selected ? <>
              <div className="selected-mention"><div className="label-row"><span className="eyebrow">TRECHO SELECIONADO</span><span className={`decision ${selected.decision}`}>{DECISIONS[selected.decision]}</span></div><h3>“{selected.text}”</h3><small>{selected.source === 'manual' ? 'Inclusão manual' : 'Sugestão lexical'} · posições {selected.start}–{selected.end}</small></div>
              <label htmlFor="candidate">Conceito HPO sugerido</label><select id="candidate" value={selected.selected_hpo_id ?? ''} disabled={!!busy} onChange={event => edit({ selected_hpo_id: event.target.value || null })}><option value="">Selecione um conceito</option>{union(selected).map(candidate => <option key={candidate.hpo_id} value={candidate.hpo_id}>{candidate.label_pt || candidate.label_en} · {candidate.hpo_id}</option>)}</select>
              <details className="search-concept"><summary><MagnifyingGlass size={17} /> Procurar outro conceito ou ID</summary><label htmlFor="concept-search">Rótulo, sinônimo oficial ou HP:0000000</label><div className="input-action"><input id="concept-search" maxLength={100} value={search} disabled={!!busy} onChange={event => { setSearch(event.target.value); setFound([]); setSearched(false) }} onKeyDown={event => { if (event.key === 'Enter' && search.trim() && !busy) void searchConcept() }} /><button className="secondary" disabled={!!busy || !search.trim()} onClick={searchConcept}>Buscar</button></div>{found.map(candidate => <button key={`${candidate.method}:${candidate.hpo_id}`} className="search-result" onClick={() => useFound(candidate)}><span>{candidate.label_pt || candidate.label_en}<small>{candidate.label_pt_status === 'official' ? 'Rótulo PT oficial' : 'Sem tradução PT oficial'}{candidate.matched_term && candidate.matched_term !== (candidate.label_pt || candidate.label_en) ? ` · correspondência: “${candidate.matched_term}” (${candidate.matched_language?.toUpperCase()})` : ''}</small></span><code>{candidate.hpo_id}</code><Plus size={16} /></button>)}{searched && !found.length && <p>Nenhum conceito encontrado.</p>}<p className="helper">Resultados em inglês vêm da ontologia HPO e não são apresentados como tradução portuguesa.</p></details>
              <ConceptPanel id={selected.selected_hpo_id} />
              <label htmlFor="assertion">Contexto da menção</label><select id="assertion" value={selected.assertion} disabled={!!busy} onChange={event => edit({ assertion: event.target.value as Assertion })}>{Object.entries(ASSERTIONS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select><p className="helper">Sugestão automática: {ASSERTIONS[selected.suggested_assertion]}. Ao incluir, você confirma conceito e contexto.</p>
              <details className="characterization" open><summary>Caracterização e pendências <span className="count">{pendingCharacterization(selected).length}</span></summary>
                <p className="helper">Preencha o que estiver disponível. “Desconhecido” é informação explícita; campo vazio permanece como pendência.</p>
                <label htmlFor="onset-age">Idade ou início</label><input id="onset-age" maxLength={100} value={selected.characterization.onset_age ?? ''} disabled={!!busy} onChange={event => characterize('onset_age', event.target.value)} placeholder="Ex.: ao nascimento, 3 anos (sem inferência automática)" />
                <div className="characterization-grid">
                  <label>Gravidade<select aria-label="Gravidade" value={selected.characterization.severity ?? ''} onChange={event => characterize('severity', event.target.value)}><option value="">Não informado</option><option value="mild">Leve</option><option value="moderate">Moderada</option><option value="severe">Grave</option><option value="profound">Profunda</option><option value="other">Outra</option><option value="unknown">Desconhecida</option></select></label>
                  <label>Evolução<select aria-label="Evolução" value={selected.characterization.evolution ?? ''} onChange={event => characterize('evolution', event.target.value)}><option value="">Não informada</option><option value="stable">Estável</option><option value="progressive">Progressiva</option><option value="improving">Em melhora</option><option value="fluctuating">Flutuante</option><option value="resolved">Resolvida</option><option value="other">Outra</option><option value="unknown">Desconhecida</option></select></label>
                  <label>Frequência<select aria-label="Frequência" value={selected.characterization.frequency ?? ''} onChange={event => characterize('frequency', event.target.value)}><option value="">Não informada</option><option value="episodic">Episódica</option><option value="intermittent">Intermitente</option><option value="continuous">Contínua</option><option value="other">Outra</option><option value="unknown">Desconhecida</option></select></label>
                  <label>Lateralidade<select aria-label="Lateralidade" value={selected.characterization.laterality ?? ''} onChange={event => characterize('laterality', event.target.value)}><option value="">Não informada</option><option value="left">Esquerda</option><option value="right">Direita</option><option value="bilateral">Bilateral</option><option value="midline">Linha média</option><option value="not_applicable">Não se aplica</option><option value="other">Outra</option><option value="unknown">Desconhecida</option></select></label>
                  <label>Histórico familiar<select aria-label="Histórico familiar" value={selected.characterization.family_history ?? ''} onChange={event => characterize('family_history', event.target.value)}><option value="">Não informado</option><option value="present">Presente</option><option value="absent">Ausente</option><option value="unknown">Desconhecido</option></select></label>
                </div>
                {!!pendingCharacterization(selected).length && <p className="pending-note">Pendências: {pendingCharacterization(selected).map(field => CHARACTERIZATION_LABELS[field]).join('; ')}.</p>}
              </details>
              <div className="review-actions"><button className="primary" disabled={!!busy || !selected.selected_hpo_id || selected.decision === 'include'} onClick={() => decide('include')}><Check size={19} />{selected.decision === 'include' ? 'Incluída no perfil' : 'Confirmar e incluir'}</button><button className="secondary danger" disabled={!!busy || selected.decision === 'discard'} onClick={() => decide('discard')}><Trash size={17} />Descartar</button></div>
              <details className="method-details"><summary>Comparar métodos de recuperação</summary><p className="helper">Scores ordenam candidatos dentro de cada método. Não são medidas de certeza clínica nem comparáveis entre métodos.</p><label htmlFor="method">Método</label><select id="method" value={technicalMethod} onChange={event => setTechnicalMethod(event.target.value)}>{Object.keys(selected.rankings).map(method => <option key={method}>{method}</option>)}</select><ol className="ranking-list">{(selected.rankings[technicalMethod] ?? []).map(candidate => <li key={`${candidate.hpo_id}:${candidate.rank}`}><strong>{candidate.label_pt || candidate.label_en}</strong><code>{candidate.hpo_id}</code><span>Score: {candidate.score === null ? 'não aplicável' : candidate.score.toFixed(4)} · {candidate.reason}</span></li>)}</ol>{!selected.rankings[technicalMethod]?.length && <p className="muted">Sem candidatos neste método.</p>}<button className="secondary" disabled={!!busy} onClick={semantic}>Consultar SapBERT para este trecho</button><p className="helper">Opcional e experimental. Usa apenas modelo já disponível no cache local; a bancada funciona sem ele.</p></details>
            </> : <div className="review-empty"><div className="empty-symbol"><MagnifyingGlass size={42} weight="light" /></div><span className="eyebrow">REVISÃO HUMANA, SEMPRE</span><h3>Uma sugestão.<br />Uma decisão sua.</h3><p>Os conceitos encontrados aparecerão aqui, com definições oficiais e alternativas para você comparar.</p><div className="empty-checks"><span><Check size={17} /> IDs válidos no snapshot HPO</span><span><Check size={17} /> Evidência ligada ao texto</span><span><Check size={17} /> Contexto confirmado por você</span></div></div>}
          </section>
        </div>

        <section ref={profileRef} className="panel profile-panel" aria-labelledby="profile-heading"><div className="panel-title"><div><span className="section-number">03</span><h2 id="profile-heading">Perfil fenotípico</h2></div><span className="muted">{included.length} {included.length === 1 ? 'menção incluída' : 'menções incluídas'}</span></div>
          <div className="profile-content"><div className="profile-summary">{included.length ? <ul className="profile-list">{included.map(review => <li key={spanKey(review)}><Checks size={19} /><div><strong>{union(review).find(candidate => candidate.hpo_id === review.selected_hpo_id)?.label_pt || union(review).find(candidate => candidate.hpo_id === review.selected_hpo_id)?.label_en || review.selected_hpo_id}</strong><code>{review.selected_hpo_id}</code><small>{pendingCharacterization(review).length ? `Pendências: ${pendingCharacterization(review).map(field => CHARACTERIZATION_LABELS[field]).join(', ')}` : 'Caracterização revisada sem campos pendentes'}</small></div><span className={`assertion ${review.assertion}`}>{ASSERTIONS[review.assertion]}</span></li>)}</ul> : <p className="muted">As menções que você confirmar serão reunidas aqui.</p>}
            <p className="helper">{analyzed ? `${pending} pendentes · ${reviews.filter(review => review.decision === 'discard').length} descartadas · ${reviews.filter(review => review.source === 'manual').length} manuais` : 'Comece pela descrição sintética para criar um perfil.'}</p></div><div className="export-box"><button className="primary" disabled={!!busy || !ready} onClick={exportProfile}><DownloadSimple size={20} />Exportar perfil JSON</button><small>{pending ? 'Resolva as menções pendentes para exportar.' : 'Formato hpo-ptbr-review-v1. Não é um Phenopacket.'}</small></div></div>
        </section>
        <footer><span>HPO-PTBR Lab · pesquisa em ontologia clínica</span><span>{health ? `Snapshot ${health.data_version}` : 'Conectando à API local…'}</span></footer>
      </main>
    </div>
  </div>
}
