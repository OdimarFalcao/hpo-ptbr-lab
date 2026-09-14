export type Assertion = 'present' | 'absent' | 'uncertain' | 'family_history'
export type Decision = 'pending' | 'include' | 'discard'
export interface Candidate {
  hpo_id: string; label_pt: string; label_en: string; score: number | null
  rank: number; method: string; reason: string
  matched_term?: string | null; matched_language?: 'pt' | 'en' | null
  matched_field?: string | null; matched_audience?: string | null; term_source?: string | null
  label_pt_status: 'official' | 'unavailable'
}
export interface Span {
  text: string; start: number; end: number; source: 'lexical' | 'manual'
  detector_score: number | null; suggested_assertion: Assertion
  rankings: Record<string, Candidate[]>
}
export interface Review extends Span {
  selected_hpo_id: string | null; assertion: Assertion
  decision: Decision; human_modified: boolean
  characterization: Characterization
}
export interface Characterization {
  onset_age: string | null
  severity: 'mild' | 'moderate' | 'severe' | 'profound' | 'other' | 'unknown' | null
  evolution: 'stable' | 'progressive' | 'improving' | 'fluctuating' | 'resolved' | 'other' | 'unknown' | null
  frequency: 'episodic' | 'intermittent' | 'continuous' | 'other' | 'unknown' | null
  laterality: 'left' | 'right' | 'bilateral' | 'midline' | 'not_applicable' | 'other' | 'unknown' | null
  family_history: 'present' | 'absent' | 'unknown' | null
}
export interface Example { id: string; title: string; domain: string; text: string }
export interface Health { status: string; data_version: string; active_terms: number; translated_labels_pt: number }
export interface Related { hpo_id: string; label: string }
export interface Concept {
  hpo_id: string; label_pt: string; label_en: string; definition_pt: string; definition_en: string
  synonyms: {text: string; scope: string; audience: string}[]
  parents: Related[]; children: Related[]; path: Related[]
}
export const ASSERTIONS: Record<Assertion, string> = {
  present: 'Presente', absent: 'Ausente', uncertain: 'Incerto', family_history: 'Histórico familiar',
}
export const DECISIONS: Record<Decision, string> = { pending: 'Pendente', include: 'Incluída', discard: 'Descartada' }
export const CHARACTERIZATION_LABELS: Record<keyof Characterization, string> = {
  onset_age: 'Idade ou início', severity: 'Gravidade', evolution: 'Evolução', frequency: 'Frequência',
  laterality: 'Lateralidade, quando aplicável', family_history: 'Histórico familiar',
}
