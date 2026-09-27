import { afterEach, expect, test, vi } from 'vitest'
import { analyzeSentence } from './sentence-api'
import type { SentenceAnalysis } from './sentence-api'

afterEach(() => {
  vi.unstubAllGlobals()
})

test('posts the original text and returns the analysis', async () => {
  const text = ' 昨日りんごを食べました。 '
  const payload: SentenceAnalysis = {
    text,
    offset_unit: 'unicode_code_points',
    groups: [],
  }

  const fetchMock = vi.fn().mockResolvedValue(
    new Response(JSON.stringify(payload), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    }),
  )
  vi.stubGlobal('fetch', fetchMock)

  const controller = new AbortController()
  const result = await analyzeSentence(text, {
    signal: controller.signal,
  })

  expect(result).toEqual(payload)
  expect(fetchMock).toHaveBeenCalledExactlyOnceWith(
    '/api/v1/analyze',
    {
      method: 'POST',
      headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ text }),
      signal: controller.signal,
    },
  )
})

test('rejects blank input without sending a request', async () => {
  const fetchMock = vi.fn()
  vi.stubGlobal('fetch', fetchMock)

  await expect(analyzeSentence(' \n ')).rejects.toThrow(
    'Enter some text to analyze.',
  )

  expect(fetchMock).not.toHaveBeenCalled()
})

test('reports an unsuccessful HTTP response', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue(new Response(null, { status: 503 })),
  )

  await expect(analyzeSentence('学校')).rejects.toThrow(
    'Sentence analysis failed (503).',
  )
})

test('preserves cancellation errors for the component to handle', async () => {
  const cancellation = new DOMException('Aborted', 'AbortError')

  vi.stubGlobal(
    'fetch',
    vi.fn().mockRejectedValue(cancellation),
  )

  await expect(analyzeSentence('学校')).rejects.toBe(cancellation)
})