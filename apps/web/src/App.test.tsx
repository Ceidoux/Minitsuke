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

test('keeps at least one language selected and sends selected languages', async () => {
  searchMock.mockResolvedValue(makePage([makeEntry(1, '学校')]))

  render(<App />)

  const english = screen.getByRole('checkbox', { name: 'English' })
  const french = screen.getByRole('checkbox', { name: 'Français' })

  expect(english).toBeChecked()
  expect(english).toBeDisabled()
  expect(french).not.toBeChecked()

  fireEvent.click(french)

  expect(english).toBeEnabled()
  expect(french).toBeChecked()

  typeQuery('school')
  await advanceTime()

  expect(searchMock).toHaveBeenLastCalledWith(
    'school',
    expect.objectContaining({
      languages: ['eng', 'fre'],
      offset: 0,
    }),
  )

  fireEvent.click(english)
  await advanceTime()

  expect(english).not.toBeChecked()
  expect(french).toBeChecked()
  expect(french).toBeDisabled()

  expect(searchMock).toHaveBeenLastCalledWith(
    'school',
    expect.objectContaining({
      languages: ['fre'],
      offset: 0,
    }),
  )
})

test('changing languages cancels a pending page and resets results', async () => {
  let finishOldPage!: (page: SearchResponse) => void

  const oldPage = new Promise<SearchResponse>((resolve) => {
    finishOldPage = resolve
  })

  searchMock
    .mockResolvedValueOnce(makePage([makeEntry(1, '学校')], 0, true))
    .mockReturnValueOnce(oldPage)
    .mockResolvedValueOnce(makePage([makeEntry(3, '学園')]))

  render(<App />)

  typeQuery('school')
  await advanceTime()

  fireEvent.click(screen.getByRole('button', { name: 'Load more' }))
  await advanceTime()

  const oldSignal = searchMock.mock.calls[1][1].signal

  fireEvent.click(screen.getByRole('checkbox', { name: 'Français' }))
  await advanceTime()

  expect(oldSignal.aborted).toBe(true)
  expect(searchMock).toHaveBeenLastCalledWith(
    'school',
    expect.objectContaining({
      languages: ['eng', 'fre'],
      offset: 0,
    }),
  )

  expect(screen.queryByRole('heading', { name: '学校' })).not.toBeInTheDocument()
  expect(screen.getByRole('heading', { name: '学園' })).toBeVisible()

  await act(async () => {
    finishOldPage(makePage([makeEntry(2, '小学校')], 30))
    await oldPage
  })

  expect(screen.queryByRole('heading', { name: '小学校' })).not.toBeInTheDocument()
  expect(screen.getByRole('heading', { name: '学園' })).toBeVisible()
})

test('opens a shared search using URL languages instead of preferences', async () => {
  window.localStorage.setItem(
    'minitsuke.definition-languages',
    JSON.stringify(['ger']),
  )

  window.history.replaceState(
    null,
    '',
    '/?q=school&languages=eng&languages=fre',
  )

  searchMock.mockResolvedValue(makePage([makeEntry(1, '学校')]))

  render(<App />)
  await advanceTime()

  expect(screen.getByRole('searchbox')).toHaveValue('school')
  expect(
    screen.getByRole('checkbox', { name: 'English' }),
  ).toBeChecked()
  expect(
    screen.getByRole('checkbox', { name: 'Français' }),
  ).toBeChecked()
  expect(
    screen.getByRole('checkbox', { name: 'Deutsch' }),
  ).not.toBeChecked()

  expect(searchMock).toHaveBeenLastCalledWith(
    'school',
    expect.objectContaining({
      languages: ['eng', 'fre'],
      offset: 0,
    }),
  )

  expect(
    JSON.parse(
      window.localStorage.getItem('minitsuke.definition-languages')!,
    ),
  ).toEqual(['ger'])
})

test('restores navigation and cancels a pending URL update', async () => {
  searchMock.mockResolvedValue(makePage([makeEntry(1, '学校')]))

  render(<App />)

  typeQuery('school')
  await advanceTime()

  expect(
    new URLSearchParams(window.location.search).get('q'),
  ).toBe('school')

  typeQuery('unfinished')
  await advanceTime(100)

  act(() => {
    window.history.replaceState(
      null,
      '',
      '/?q=tabe&languages=fre',
    )
    window.dispatchEvent(new PopStateEvent('popstate'))
  })

  await advanceTime()

  expect(screen.getByRole('searchbox')).toHaveValue('tabe')
  expect(
    screen.getByRole('checkbox', { name: 'Français' }),
  ).toBeChecked()
  expect(
    screen.getByRole('checkbox', { name: 'English' }),
  ).not.toBeChecked()

  expect(
    new URLSearchParams(window.location.search).get('q'),
  ).toBe('tabe')

  expect(searchMock).toHaveBeenLastCalledWith(
    'tabe',
    expect.objectContaining({
      languages: ['fre'],
      offset: 0,
    }),
  )
})