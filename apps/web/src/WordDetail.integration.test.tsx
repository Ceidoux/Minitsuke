import { act, fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import App from './App'
import {
  fetchDictionaryEntry,
  searchDictionary,
} from './dictionary-api'
import type {
  DictionaryEntry,
  SearchResponse,
} from './dictionary-api'

vi.mock('./dictionary-api', () => ({
  searchDictionary: vi.fn(),
  fetchDictionaryEntry: vi.fn(),
}))

const searchMock = vi.mocked(searchDictionary)
const detailMock = vi.mocked(fetchDictionaryEntry)

function makeEntry(
  sourceId: number,
  writtenForm: string,
): DictionaryEntry {
  return {
    source_id: sourceId,
    is_common: true,
    written_forms: [writtenForm],
    readings: [],
    senses: [
      {
        glosses: [{ text: 'school', language: 'eng' }],
        parts_of_speech: ['noun'],
        restricted_to_written_forms: [],
        restricted_to_readings: [],
      },
    ],
  }
}

const school = makeEntry(100, '学校')
const academy = makeEntry(200, '学園')

function makePage(
  results: DictionaryEntry[],
  offset = 0,
  hasMore = false,
): SearchResponse {
  return {
    query: 'school',
    results,
    limit: 30,
    offset,
    has_more: hasMore,
  }
}

async function settle() {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(200)
  })
}

function resultsPanel() {
  return within(screen.getByRole('region', { name: 'Results' }))
}

function detailPanel() {
  return within(screen.getByRole('region', { name: 'Word details' }))
}

beforeEach(() => {
  vi.useFakeTimers()
  searchMock.mockReset()
  detailMock.mockReset()

  detailMock.mockImplementation(async (sourceId) => {
    return sourceId === 100 ? school : academy
  })
})

afterEach(() => {
  vi.useRealTimers()
})

test('opens a shared entry without requiring search results', async () => {
  window.history.replaceState(
    null,
    '',
    '/?entry=100&languages=eng&languages=fre',
  )

  render(<App />)
  await settle()

  expect(searchMock).not.toHaveBeenCalled()
  expect(detailMock).toHaveBeenCalledWith(
    100,
    expect.objectContaining({
      languages: ['eng', 'fre'],
    }),
  )

  expect(
    detailPanel().getByRole('heading', { name: '学校' }),
  ).toBeVisible()
})

test('preserves loaded pages when selecting words and restoring history', async () => {
  searchMock
    .mockResolvedValueOnce(makePage([school], 0, true))
    .mockResolvedValueOnce(makePage([academy], 30))

  render(<App />)

  fireEvent.change(screen.getByRole('searchbox'), {
    target: { value: 'school' },
  })
  await settle()

  fireEvent.click(screen.getByRole('button', { name: 'Load more' }))
  await settle()

  fireEvent.click(
    resultsPanel().getByRole('button', { name: '学校' }),
  )
  await settle()

  const schoolUrl = window.location.href

  fireEvent.click(
    resultsPanel().getByRole('button', { name: '学園' }),
  )
  await settle()

  expect(
    detailPanel().getByRole('heading', { name: '学園' }),
  ).toBeVisible()
  expect(
    new URLSearchParams(window.location.search).get('entry'),
  ).toBe('200')

  // Simulate the URL and event delivered when navigating back.
  act(() => {
    window.history.replaceState(null, '', schoolUrl)
    window.dispatchEvent(new PopStateEvent('popstate'))
  })
  await settle()

  expect(
    detailPanel().getByRole('heading', { name: '学校' }),
  ).toBeVisible()

  expect(searchMock).toHaveBeenCalledTimes(2)
  expect(resultsPanel().getAllByRole('article')).toHaveLength(2)
  expect(
    resultsPanel().getByRole('button', { name: '学校' }),
  ).toHaveAttribute('aria-pressed', 'true')

  fireEvent.click(
    screen.getByRole('button', { name: 'Back to results' }),
  )
  await settle()

  expect(
    new URLSearchParams(window.location.search).has('entry'),
  ).toBe(false)
  expect(detailPanel().queryByRole('article')).not.toBeInTheDocument()
  expect(resultsPanel().getAllByRole('article')).toHaveLength(2)
  expect(searchMock).toHaveBeenCalledTimes(2)
})

test('cancels an old detail request and ignores its late response', async () => {
  let finishOldRequest!: (entry: DictionaryEntry) => void

  const oldRequest = new Promise<DictionaryEntry>((resolve) => {
    finishOldRequest = resolve
  })

  searchMock.mockResolvedValue(makePage([school, academy]))
  detailMock
    .mockReturnValueOnce(oldRequest)
    .mockResolvedValueOnce(academy)

  render(<App />)

  fireEvent.change(screen.getByRole('searchbox'), {
    target: { value: 'school' },
  })
  await settle()

  fireEvent.click(
    resultsPanel().getByRole('button', { name: '学校' }),
  )
  await settle()

  const oldSignal = detailMock.mock.calls[0][1].signal

  fireEvent.click(
    resultsPanel().getByRole('button', { name: '学園' }),
  )
  await settle()

  expect(oldSignal.aborted).toBe(true)

  await act(async () => {
    finishOldRequest(school)
    await oldRequest
  })

  expect(
    detailPanel().getByRole('heading', { name: '学園' }),
  ).toBeVisible()
  expect(
    detailPanel().queryByRole('heading', { name: '学校' }),
  ).not.toBeInTheDocument()
})

test('retries a failed detail request without repeating the search', async () => {
  searchMock.mockResolvedValue(makePage([school]))
  detailMock
    .mockRejectedValueOnce(new Error('Connection lost'))
    .mockResolvedValueOnce(school)

  render(<App />)

  fireEvent.change(screen.getByRole('searchbox'), {
    target: { value: 'school' },
  })
  await settle()

  fireEvent.click(
    resultsPanel().getByRole('button', { name: '学校' }),
  )
  await settle()

  expect(detailPanel().getByRole('alert')).toHaveTextContent(
    'Connection lost',
  )
  expect(resultsPanel().getAllByRole('article')).toHaveLength(1)

  fireEvent.click(
    detailPanel().getByRole('button', { name: 'Retry loading word' }),
  )
  await settle()

  expect(detailPanel().queryByRole('alert')).not.toBeInTheDocument()
  expect(
    detailPanel().getByRole('heading', { name: '学校' }),
  ).toBeVisible()

  expect(detailMock).toHaveBeenCalledTimes(2)
  expect(searchMock).toHaveBeenCalledTimes(1)
})