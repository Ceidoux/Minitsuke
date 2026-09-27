import { act, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import SentenceAnalysis from './SentenceAnalysis'
import { analyzeSentence } from './sentence-api'
import type { SentenceAnalysis as AnalysisResponse } from './sentence-api'
import { fetchDictionaryEntry } from './dictionary-api'
import type { DictionaryEntry } from './dictionary-api'

vi.mock('./sentence-api', () => ({
  analyzeSentence: vi.fn(),
}))

vi.mock('./dictionary-api', () => ({
  fetchDictionaryEntry: vi.fn(),
}))

const analyze = vi.mocked(analyzeSentence)
const fetchEntry = vi.mocked(fetchDictionaryEntry)

function makeAnalysis(): AnalysisResponse {
  return {
    text: '食べました。',
    offset_unit: 'unicode_code_points',
    groups: [
      {
        surface: '食べました',
        start: 0,
        end: 5,
        candidate_source_ids: [1358280],
        tokens: [
          {
            surface: '食べ',
            start: 0,
            end: 2,
            dictionary_form: '食べる',
            normalized_form: '食べる',
            reading: 'タベ',
            part_of_speech: ['動詞'],
            is_unknown: false,
            candidate_source_ids: [1358280],
          },
          {
            surface: 'まし',
            start: 2,
            end: 4,
            dictionary_form: 'ます',
            normalized_form: 'ます',
            reading: 'マシ',
            part_of_speech: ['助動詞'],
            is_unknown: false,
            candidate_source_ids: [],
          },
          {
            surface: 'た',
            start: 4,
            end: 5,
            dictionary_form: 'た',
            normalized_form: 'た',
            reading: 'タ',
            part_of_speech: ['助動詞'],
            is_unknown: false,
            candidate_source_ids: [],
          },
        ],
      },
      {
        surface: '。',
        start: 5,
        end: 6,
        candidate_source_ids: [],
        tokens: [
          {
            surface: '。',
            start: 5,
            end: 6,
            dictionary_form: '。',
            normalized_form: '。',
            reading: '。',
            part_of_speech: ['補助記号'],
            is_unknown: false,
            candidate_source_ids: [],
          },
        ],
      },
    ],
  }
}

function makeEntry(): DictionaryEntry {
  return {
    source_id: 1358280,
    is_common: true,
    written_forms: ['食べる'],
    readings: [
      { text: 'たべる', no_kanji: false, restricted_to: [] },
    ],
    senses: [
      {
        glosses: [{ text: 'to eat', language: 'eng' }],
        parts_of_speech: [],
        restricted_to_written_forms: [],
        restricted_to_readings: [],
        misc: [],
      },
    ],
  }
}

beforeEach(() => {
  vi.useFakeTimers()
  analyze.mockReset()
  fetchEntry.mockReset()
  analyze.mockResolvedValue(makeAnalysis())
  fetchEntry.mockResolvedValue(makeEntry())
})

afterEach(() => {
  vi.useRealTimers()
})

test('waits for a typing pause before analyzing', async () => {
  render(
    <SentenceAnalysis
      query="食べました。"
      languages={['eng']}
      selectedSourceId={null}
      onSelect={vi.fn()}
    />,
  )

  await act(async () => {
    await vi.advanceTimersByTimeAsync(199)
  })
  expect(analyze).not.toHaveBeenCalled()

  await act(async () => {
    await vi.advanceTimersByTimeAsync(1)
  })

  expect(analyze).toHaveBeenCalledExactlyOnceWith(
    '食べました。',
    expect.objectContaining({ signal: expect.any(AbortSignal) }),
  )
  expect(
    screen.getByRole('button', { name: '食べました' }),
  ).toBeInTheDocument()
})

test('selecting a segment loads candidates without opening details', async () => {
  const onSelect = vi.fn()

  render(
    <SentenceAnalysis
      query="食べました。"
      languages={['eng']}
      selectedSourceId={null}
      onSelect={onSelect}
    />,
  )

  await act(async () => {
    await vi.advanceTimersByTimeAsync(200)
  })

  expect(fetchEntry).not.toHaveBeenCalled()

  await act(async () => {
    fireEvent.click(
      screen.getByRole('button', { name: '食べました' }),
    )
  })

  expect(onSelect).not.toHaveBeenCalled()
  expect(
    screen.getByRole('button', { name: '食べました' }),
  ).toHaveAttribute('aria-pressed', 'true')

  const card = screen.getByRole('button', { name: '食べる' })
  fireEvent.click(card)

  expect(onSelect).toHaveBeenCalledWith(1358280, card)
  expect(screen.queryByRole('button', { name: '。' })).toBeNull()
})

test('cancels pending analysis when the query is replaced', async () => {
  const onSelect = vi.fn()

  const { rerender } = render(
    <SentenceAnalysis
      key="old"
      query="食べ"
      languages={['eng']}
      selectedSourceId={null}
      onSelect={onSelect}
    />,
  )

  await act(async () => {
    await vi.advanceTimersByTimeAsync(100)
  })

  rerender(
    <SentenceAnalysis
      key="new"
      query="食べました。"
      languages={['eng']}
      selectedSourceId={null}
      onSelect={onSelect}
    />,
  )

  await act(async () => {
    await vi.advanceTimersByTimeAsync(200)
  })

  expect(analyze).toHaveBeenCalledTimes(1)
  expect(analyze.mock.calls[0][0]).toBe('食べました。')
})

test('can retry failed analysis', async () => {
  analyze.mockRejectedValueOnce(new Error('Temporary analysis failure'))

  render(
    <SentenceAnalysis
      query="食べました。"
      languages={['eng']}
      selectedSourceId={null}
      onSelect={vi.fn()}
    />,
  )

  await act(async () => {
    await vi.advanceTimersByTimeAsync(200)
  })

  expect(screen.getByRole('alert')).toHaveTextContent(
    'Temporary analysis failure',
  )

  fireEvent.click(screen.getByRole('button', { name: 'Retry analysis' }))

  await act(async () => {
    await vi.advanceTimersByTimeAsync(200)
  })

  expect(screen.queryByRole('alert')).toBeNull()
  expect(
    screen.getByRole('button', { name: '食べました' }),
  ).toBeInTheDocument()
})