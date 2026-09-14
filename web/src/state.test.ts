import { describe, it, expect } from 'vitest'
import { canExport, changeReview, occurrences, overlaps, pendingReview, points, replaceSpan, sliceText } from './state'
import type { Span } from './types'

const span: Span = { text: 'ptose', start: 2, end: 7, source: 'lexical', detector_score: 1, suggested_assertion: 'present', rankings: { Fuzzy: [{ hpo_id: 'HP:0000508', label_pt: 'Ptose', label_en: 'Ptosis', score: 1, rank: 1, method: 'fuzzy', reason: 'proximidade lexical', label_pt_status: 'official' }] } }
describe('contrato de revisão', () => {
  it('converte UTF-16 para pontos Unicode e encontra ocorrências repetidas', () => {
    const text = '🧪 ptose\ná ptose'
    expect(points(text).length).toBe(15)
    expect(sliceText(text, 2, 7)).toBe('ptose')
    expect(occurrences(text, 'ptose')).toEqual([{ start: 2, end: 7 }, { start: 10, end: 15 }])
    expect(occurrences(text, 'Ptose')).toEqual([])
  })
  it('começa pendente, bloqueia exportação e invalida decisão ao editar', () => {
    const review = pendingReview(span)
    expect(review.decision).toBe('pending')
    expect(canExport(true, [review])).toBe(false)
    expect(canExport(false, [])).toBe(false)
    expect(canExport(true, [{ ...review, decision: 'include' }])).toBe(true)
    expect(canExport(true, [{ ...review, decision: 'discard', selected_hpo_id: null }])).toBe(true)
    expect(changeReview({ ...review, decision: 'include' }, { assertion: 'absent' }).decision).toBe('pending')
    expect(changeReview(review, { selected_hpo_id: 'HP:0000639' }).human_modified).toBe(true)
  })
  it('substitui sobreposições sem remover vizinhos', () => {
    const first = pendingReview(span), next = pendingReview({ ...span, start: 12, end: 17 })
    const replacement = pendingReview({ ...span, start: 1, end: 8, source: 'manual' })
    expect(overlaps([first, next], replacement)).toEqual([first])
    expect(replaceSpan([first, next], replacement)).toEqual([replacement, next])
    expect(overlaps([first], { start: 7, end: 9 })).toEqual([])
  })
})
