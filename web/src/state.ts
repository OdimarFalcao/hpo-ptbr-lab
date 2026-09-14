import type { Candidate, Characterization, Review, Span } from './types'

export const EMPTY_CHARACTERIZATION: Characterization = {
  onset_age: null, severity: null, evolution: null, frequency: null, laterality: null, family_history: null,
}

export const points = (text: string) => Array.from(text)
export const sliceText = (text: string, start: number, end?: number) => points(text).slice(start, end).join('')
export const spanKey = (span: Span) => `${span.start}:${span.end}`
export const union = (span: Span): Candidate[] => [...new Map(Object.values(span.rankings).flat().map(candidate => [candidate.hpo_id, candidate])).values()]
export function pendingReview(span: Span): Review {
  return { ...span, selected_hpo_id: span.rankings.Fuzzy?.[0]?.hpo_id ?? union(span)[0]?.hpo_id ?? null,
    assertion: span.suggested_assertion, decision: 'pending', human_modified: span.source === 'manual',
    characterization: { ...EMPTY_CHARACTERIZATION } }
}
export function occurrences(text: string, phrase: string): { start: number; end: number }[] {
  const needle = points(phrase.trim()), haystack = points(text)
  if (!needle.length) return []
  const found = []
  for (let offset = 0; offset <= haystack.length - needle.length; offset++) {
    if (needle.every((character, index) => haystack[offset + index] === character)) {
      found.push({ start: offset, end: offset + needle.length })
      offset += needle.length - 1
    }
  }
  return found
}
export function overlaps(spans: Review[], replacement: {start: number; end: number}) {
  return spans.filter(span => replacement.start < span.end && span.start < replacement.end)
}
export function replaceSpan(spans: Review[], replacement: Review): Review[] {
  const removed = new Set(overlaps(spans, replacement).map(spanKey))
  return [...spans.filter(span => !removed.has(spanKey(span))), replacement].sort((left, right) => left.start - right.start)
}
export function changeReview(review: Review, changes: Partial<Pick<Review, 'selected_hpo_id' | 'assertion' | 'characterization'>>): Review {
  return { ...review, ...changes, decision: 'pending', human_modified: true }
}
export const pendingCharacterization = (review: Review) => Object.entries(review.characterization)
  .filter(([, value]) => value === null || value === '')
  .map(([field]) => field as keyof Characterization)
export const canExport = (analyzed: boolean, reviews: Review[]) => analyzed && reviews.every(review => review.decision !== 'pending' && (review.decision === 'discard' || !!review.selected_hpo_id))
