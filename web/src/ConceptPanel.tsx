import { useEffect, useState } from 'react'
import { TreeStructure, BookOpen } from '@phosphor-icons/react'
import { request } from './api'
import type { Concept, Related } from './types'

export default function ConceptPanel({ id }: { id: string | null }) {
  const [concept, setConcept] = useState<Concept | null>(null)
  const [error, setError] = useState('')
  useEffect(() => {
    const controller = new AbortController()
    setConcept(null); setError('')
    if (id) request<Concept>(`concepts/${encodeURIComponent(id)}`, undefined, controller.signal)
      .then(setConcept).catch(error => { if (!controller.signal.aborted) setError(error.message) })
    return () => controller.abort()
  }, [id])
  const related = (items: Related[]) => items.length
    ? <ul className="relation-list">{items.map(item => <li key={item.hpo_id}><span>{item.label}</span><code>{item.hpo_id}</code></li>)}</ul>
    : <p className="muted">Nenhum no snapshot.</p>
  if (!id) return null
  if (error) return <p role="alert" className="error">{error}</p>
  if (!concept) return <p role="status" className="muted">Consultando conceito oficial…</p>
  return <div className="concept-panel">
    <div className="concept-heading"><BookOpen size={18} /><span>Conceito no snapshot oficial</span></div>
    <h3>{concept.label_pt || concept.label_en}</h3>
    <div className="concept-meta"><code>{concept.hpo_id}</code><span>{concept.label_pt ? 'Rótulo PT oficial' : 'Sem rótulo PT oficial'}</span></div>
    <p className="definition">{concept.definition_pt || concept.definition_en || 'Definição não disponível neste snapshot.'}</p>
    {(concept.definition_pt || concept.definition_en) && <small className="muted">{concept.definition_pt ? 'Definição portuguesa oficial' : 'Definição oficial em inglês · não traduzida automaticamente'}</small>}
    <details><summary>Sinônimos oficiais HPO em inglês <span className="count">{concept.synonyms.length}</span></summary>
      {concept.synonyms.length ? <ul className="synonyms">{concept.synonyms.map((synonym, index) => <li key={index}>{synonym.text} <small>EN · {synonym.scope} · {synonym.audience}</small></li>)}</ul> : <p className="muted">Sem sinônimos no snapshot.</p>}
    </details>
    <details><summary><TreeStructure size={17} /> Posição na ontologia</summary>
      <p className="field-label">Caminho até HP:0000118</p>
      {concept.path.length ? <ol className="ontology-path">{concept.path.map(item => <li key={item.hpo_id}>{item.label} <code>{item.hpo_id}</code></li>)}</ol> : <p>Não há caminho até a raiz fenotípica neste snapshot.</p>}
      <details><summary>Pais diretos ({concept.parents.length})</summary>{related(concept.parents)}</details>
      <details><summary>Filhos diretos ({concept.children.length})</summary>{related(concept.children)}</details>
    </details>
  </div>
}
