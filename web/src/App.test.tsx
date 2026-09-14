import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import App from './App'
import { request } from './api'

vi.mock('./api', () => ({ request: vi.fn() }))
const mockRequest = vi.mocked(request)
const candidate = { hpo_id: 'HP:0000508', label_pt: 'Ptose', label_en: 'Ptosis', score: 1, rank: 1, method: 'fuzzy', reason: 'proximidade lexical', label_pt_status: 'official' as const }
const span = { text: 'ptose', start: 0, end: 5, source: 'lexical', detector_score: 1, suggested_assertion: 'present', rankings: { Exact: [candidate], Fuzzy: [candidate], BM25: [candidate] } }

beforeEach(() => {
  mockRequest.mockReset()
  mockRequest.mockImplementation(async path => {
    if (path === 'health') return { status: 'ok', data_version: 'test', active_terms: 19836, translated_labels_pt: 7158 }
    if (path === 'examples') return [{ id: 'synthetic', domain: 'Ocular', title: 'Exemplo sintético', text: 'ptose' }]
    if (path === 'analyze') return { data_version: 'test', spans: [span] }
    if (path.startsWith('concepts/')) return { ...candidate, definition_en: 'Official definition.', definition_pt: '', parents: [], children: [], path: [], synonyms: [] }
    if (path === 'search') return []
    if (path === 'export') return { schema_version: 'hpo-ptbr-review-v1' }
    if (path === 'semantic') throw new Error('SapBERT indisponível no cache local.')
    throw new Error(`Unexpected endpoint ${path}`)
  })
})
afterEach(cleanup)

async function start() {
  const user = userEvent.setup()
  render(<App />)
  await screen.findByRole('option', { name: 'Exemplo sintético' })
  await user.selectOptions(screen.getByLabelText('Comece com um exemplo'), 'synthetic')
  await user.click(screen.getByRole('button', { name: 'Localizar fenótipos' }))
  await screen.findByRole('button', { name: 'Confirmar e incluir' })
  return user
}

describe('bancada interativa', () => {
  it('exige revisão explícita e bloqueia novamente após editar o contexto', async () => {
    const persist = vi.spyOn(Storage.prototype, 'setItem')
    const user = await start()
    const exportButton = screen.getByRole('button', { name: 'Exportar perfil JSON' }) as HTMLButtonElement
    expect(exportButton.disabled).toBe(true)
    await user.click(screen.getByRole('button', { name: 'Confirmar e incluir' }))
    expect(exportButton.disabled).toBe(false)
    await user.selectOptions(screen.getByLabelText('Contexto da menção'), 'family_history')
    expect(exportButton.disabled).toBe(true)
    await user.click(screen.getByRole('button', { name: 'Descartar' }))
    expect(exportButton.disabled).toBe(false)
    await user.click(screen.getByRole('button', { name: 'Editar descrição' }))
    await user.type(screen.getByLabelText('Texto para anotação'), ' diferente')
    expect(exportButton.disabled).toBe(true)
    expect(screen.queryByLabelText('Contexto da menção')).toBeNull()
    expect(persist).not.toHaveBeenCalled()
  })
  it('mantém fluxo lexical quando SapBERT falha', async () => {
    const user = await start()
    await user.click(screen.getByText('Comparar métodos de recuperação'))
    await user.click(screen.getByRole('button', { name: 'Consultar SapBERT para este trecho' }))
    await screen.findByRole('alert')
    expect(screen.getByRole('alert').textContent).toContain('SapBERT indisponível')
    await user.click(screen.getByRole('button', { name: 'Confirmar e incluir' }))
    expect((screen.getByRole('button', { name: 'Exportar perfil JSON' }) as HTMLButtonElement).disabled).toBe(false)
  })
  it('mostra pendências e exige nova confirmação após caracterizar', async () => {
    const user = await start()
    expect(screen.getByText(/Pendências: Idade ou início/)).toBeTruthy()
    await user.click(screen.getByRole('button', { name: 'Confirmar e incluir' }))
    await user.selectOptions(screen.getByLabelText('Gravidade'), 'mild')
    expect((screen.getByRole('button', { name: 'Exportar perfil JSON' }) as HTMLButtonElement).disabled).toBe(true)
    await user.click(screen.getByRole('button', { name: 'Confirmar e incluir' }))
    expect(screen.getAllByText(/Pendências: Idade ou início, Evolução/).length).toBeGreaterThan(0)
  })
  it('pede confirmação antes de substituir uma anotação', async () => {
    const user = await start()
    await user.click(screen.getByText('Adicionar ou corrigir limites'))
    await user.type(screen.getByLabelText('Copie exatamente uma expressão do texto'), 'ptose')
    expect((screen.getByRole('button', { name: 'Corrigir limites' }) as HTMLButtonElement).disabled).toBe(true)
    await user.click(screen.getByLabelText('Confirmo a substituição e nova revisão.'))
    expect((screen.getByRole('button', { name: 'Corrigir limites' }) as HTMLButtonElement).disabled).toBe(false)
  })
  it('ignora resposta antiga quando o texto muda durante a análise', async () => {
    const user = userEvent.setup()
    render(<App />)
    await screen.findByRole('option', { name: 'Exemplo sintético' })
    await user.selectOptions(screen.getByLabelText('Comece com um exemplo'), 'synthetic')
    let resolveAnalysis: (result: unknown) => void = () => {}
    mockRequest.mockImplementationOnce(() => new Promise(resolve => { resolveAnalysis = resolve }))
    await user.click(screen.getByRole('button', { name: 'Localizar fenótipos' }))
    fireEvent.change(screen.getByLabelText('Texto para anotação'), { target: { value: 'novo texto' } })
    resolveAnalysis({ data_version: 'test', spans: [span] })
    await waitFor(() => expect(screen.queryByRole('button', { name: 'Confirmar e incluir' })).toBeNull())
  })
})
