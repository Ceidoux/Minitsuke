import { act, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import App from './App'
import { searchDictionary } from './dictionary-api'
import type { DictionaryEntry, SearchResponse } from './dictionary-api'

vi.mock('./dictionary-api', () => ({
  searchDictionary: vi.fn(),
}))

const searchMock = vi.mocked(searchDictionary)

function makeEntry(sourceId: number, writtenForm: string): DictionaryEntry {
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

function makePage(
  entries: DictionaryEntry[],
  offset = 0,
  hasMore = false,
): SearchResponse {
  return {
    query: 'school',
    results: entries,
    limit: 30,
    offset,
    has_more: hasMore,
  }
}

function typeQuery(value: string) {
  fireEvent.change(screen.getByRole('searchbox'), {
    target: { value },
  })
}

async function advanceTime(milliseconds = 200) {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(milliseconds)
  })
}

beforeEach(() => {
  vi.useFakeTimers()
  searchMock.mockReset()
})

afterEach(() => {
  vi.useRealTimers()
})

test('waits for a typing pause and does not search blank input', async () => {
  searchMock.mockResolvedValue(makePage([makeEntry(1, '学校')]))

  render(<App />)

  await advanceTime()
  expect(searchMock).not.toHaveBeenCalled()

  typeQuery('s')
  await advanceTime(100)

  typeQuery('school')
  await advanceTime(199)
  expect(searchMock).not.toHaveBeenCalled()

  await advanceTime(1)

  expect(searchMock).toHaveBeenCalledTimes(1)
  expect(searchMock).toHaveBeenCalledWith(
    'school',
    expect.objectContaining({ offset: 0 }),
  )
  expect(screen.getByRole('heading', { name: '学校' })).toBeVisible()

  typeQuery('   ')
  await advanceTime()

  expect(searchMock).toHaveBeenCalledTimes(1)
  expect(screen.queryByRole('heading', { name: '学校' })).not.toBeInTheDocument()
})

test('cancels an old query and ignores its late response', async () => {
  let finishOldRequest!: (page: SearchResponse) => void

  const oldRequest = new Promise<SearchResponse>((resolve) => {
    finishOldRequest = resolve
  })

  searchMock
    .mockReturnValueOnce(oldRequest)
    .mockResolvedValueOnce(makePage([makeEntry(2, '食べる')]))

  render(<App />)

  typeQuery('school')
  await advanceTime()

  const oldSignal = searchMock.mock.calls[0][1].signal

  typeQuery('tabe')
  await advanceTime()

  expect(oldSignal.aborted).toBe(true)
  expect(screen.getByRole('heading', { name: '食べる' })).toBeVisible()

  await act(async () => {
    finishOldRequest(makePage([makeEntry(1, '学校')]))
    await oldRequest
  })

  expect(screen.queryByRole('heading', { name: '学校' })).not.toBeInTheDocument()
  expect(screen.getByRole('heading', { name: '食べる' })).toBeVisible()
})

test('appends another page and resets pagination for a new query', async () => {
  searchMock
    .mockResolvedValueOnce(makePage([makeEntry(1, '学校')], 0, true))
    .mockResolvedValueOnce(makePage([makeEntry(2, '学園')], 30))
    .mockResolvedValueOnce(makePage([makeEntry(3, '食べる')]))

  render(<App />)

  typeQuery('school')
  await advanceTime()

  fireEvent.click(screen.getByRole('button', { name: 'Load more' }))
  await advanceTime()

  expect(searchMock).toHaveBeenNthCalledWith(
    2,
    'school',
    expect.objectContaining({ offset: 30 }),
  )
  expect(screen.getByRole('heading', { name: '学校' })).toBeVisible()
  expect(screen.getByRole('heading', { name: '学園' })).toBeVisible()
  expect(
    screen.queryByRole('button', { name: 'Load more' }),
  ).not.toBeInTheDocument()

  typeQuery('tabe')
  await advanceTime()

  expect(searchMock).toHaveBeenLastCalledWith(
    'tabe',
    expect.objectContaining({ offset: 0 }),
  )
  expect(screen.queryByRole('heading', { name: '学校' })).not.toBeInTheDocument()
  expect(screen.getByRole('heading', { name: '食べる' })).toBeVisible()
})

test('preserves existing results and retries a failed additional page', async () => {
  searchMock
    .mockResolvedValueOnce(makePage([makeEntry(1, '学校')], 0, true))
    .mockRejectedValueOnce(new Error('Connection lost'))
    .mockResolvedValueOnce(makePage([makeEntry(2, '学園')], 30))

  render(<App />)

  typeQuery('school')
  await advanceTime()

  fireEvent.click(screen.getByRole('button', { name: 'Load more' }))
  await advanceTime()

  expect(screen.getByRole('alert')).toHaveTextContent('Connection lost')
  expect(screen.getByRole('heading', { name: '学校' })).toBeVisible()

  fireEvent.click(screen.getByRole('button', { name: 'Try again' }))
  await advanceTime()

  expect(searchMock).toHaveBeenLastCalledWith(
    'school',
    expect.objectContaining({ offset: 30 }),
  )
  expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  expect(screen.getByRole('heading', { name: '学校' })).toBeVisible()
  expect(screen.getByRole('heading', { name: '学園' })).toBeVisible()
})

test('waits until Japanese composition finishes before searching', async () => {
  searchMock.mockResolvedValue(makePage([makeEntry(1, '学校')]))

  render(<App />)

  const input = screen.getByRole('searchbox')

  fireEvent.compositionStart(input)
  typeQuery('がっこう')
  await advanceTime(500)

  expect(searchMock).not.toHaveBeenCalled()

  typeQuery('学校')
  fireEvent.compositionEnd(input)
  await advanceTime()

  expect(searchMock).toHaveBeenCalledTimes(1)
  expect(searchMock).toHaveBeenCalledWith(
    '学校',
    expect.objectContaining({ offset: 0 }),
  )
  expect(screen.getByRole('heading', { name: '学校' })).toBeVisible()
})