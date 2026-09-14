import { afterEach, expect, it, vi } from 'vitest'
import { request } from './api'

afterEach(() => vi.unstubAllGlobals())

it('apresenta erro de conexão sem perder o contrato de chamada', async () => {
  vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('offline')))
  await expect(request('analyze', { text: 'ptose' })).rejects.toThrow('API local')
})

it('usa POST JSON, não põe texto na URL e desativa cache', async () => {
  const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ spans: [] }) })
  vi.stubGlobal('fetch', fetchMock)
  await request('analyze', { text: 'texto sintético' })
  expect(fetchMock.mock.calls[0][0]).toBe('/api/analyze')
  expect(fetchMock.mock.calls[0][1]).toMatchObject({ method: 'POST', cache: 'no-store', body: '{"text":"texto sintético"}' })
})

it('mostra falhas de validação sem erro de parsing secundário', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, json: async () => ({ detail: 'Offsets inválidos.' }) }))
  await expect(request('mentions', {})).rejects.toThrow('Offsets inválidos.')
})
