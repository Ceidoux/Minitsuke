import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, expect, test, vi } from 'vitest'
import { fetchDictionaryEntry } from './dictionary-api'
import type { DictionaryEntry } from './dictionary-api'
import SentenceCandidates from './SentenceCandidates'

vi.mock('./dictionary-api', () => ({
  fetchDictionaryEntry: vi.fn(),
}))

const fetchEntry = vi.mocked(fetchDictionaryEntry)

function makeEntry(sourceId: number): DictionaryEntry {
  return {
    source_id: sourceId,
    is_common: false,
    written_forms: [`候補${sourceId}`],
    readings: [
      {
        text: 'こうほ',
        no_kanji: false,
        restricted_to: [],
      },
    ],
    senses: [
      {
        glosses: [{ text: 'candidate', language: 'eng' }],
        parts_of_speech: [],
        restricted_to_written_forms: [],
        restricted_to_readings: [],
        misc: [],
      },
    ],
  }
}

function deferred<T>() {
  let resolve!: (value: T) => void

  const promise = new Promise<T>((resolvePromise) => {
    resolve = resolvePromise
  })

  return { promise, resolve }
}

beforeEach(() => {
  fetchEntry.mockReset()
})

test('preserves candidate order and opens the chosen card', async () => {
  const onSelect = vi.fn()
  const first = deferred<DictionaryEntry>()
  const second = deferred<DictionaryEntry>()

  fetchEntry.mockImplementation((sourceId) =>
    sourceId === 200 ? first.promise : second.promise,
  )

  render(
    <SentenceCandidates
      surface="ジム"
      sourceIds={[200, 100]}
      languages={['eng']}
      selectedSourceId={null}
      onSelect={onSelect}
    />,
  )

  // The second request finishes first.
  await act(async () => {
    second.resolve(makeEntry(100))
    first.resolve(makeEntry(200))
  })

  await screen.findByRole('button', { name: '候補200' })

  const cards = screen.getAllByRole('button', { name: /^候補/ })
  expect(cards.map((card) => card.textContent)).toEqual([
    '候補200',
    '候補100',
  ])

  fireEvent.click(cards[1])

  expect(onSelect).toHaveBeenCalledWith(100, cards[1])
})

test('aborts the previous segment and ignores its late response', async () => {
  const oldRequest = deferred<DictionaryEntry>()
  const onSelect = vi.fn()
  let oldSignal: AbortSignal | undefined

  fetchEntry.mockImplementation((sourceId, options) => {
    if (sourceId === 100) {
      oldSignal = options.signal
      return oldRequest.promise
    }

    return Promise.resolve(makeEntry(sourceId))
  })

  const { rerender } = render(
    <SentenceCandidates
      key="old-segment"
      surface="古い"
      sourceIds={[100]}
      languages={['eng']}
      selectedSourceId={null}
      onSelect={onSelect}
    />,
  )

  await waitFor(() => {
    expect(fetchEntry).toHaveBeenCalledTimes(1)
  })

  rerender(
    <SentenceCandidates
      key="new-segment"
      surface="新しい"
      sourceIds={[200]}
      languages={['eng']}
      selectedSourceId={null}
      onSelect={onSelect}
    />,
  )

  await screen.findByRole('button', { name: '候補200' })
  expect(oldSignal?.aborted).toBe(true)

  await act(async () => {
    oldRequest.resolve(makeEntry(100))
  })

  expect(screen.queryByRole('button', { name: '候補100' })).toBeNull()
  expect(screen.getByRole('button', { name: '候補200' })).toBeInTheDocument()
})

test('preserves the first page and retries a failed additional page', async () => {
  const sourceIds = Array.from({ length: 31 }, (_, index) => index + 1)
  let failLastEntry = true

  fetchEntry.mockImplementation(async (sourceId) => {
    if (sourceId === 31 && failLastEntry) {
      throw new Error('Temporary failure')
    }

    return makeEntry(sourceId)
  })

  render(
    <SentenceCandidates
      surface="候補"
      sourceIds={sourceIds}
      languages={['eng']}
      selectedSourceId={null}
      onSelect={vi.fn()}
    />,
  )

  await screen.findByText('30 of 31 candidates shown.')
  expect(screen.getAllByRole('button', { name: /^候補/ })).toHaveLength(30)

  fireEvent.click(screen.getByRole('button', { name: 'Load more candidates' }))

  expect(await screen.findByRole('alert')).toHaveTextContent(
    'Temporary failure',
  )
  expect(screen.getAllByRole('button', { name: /^候補/ })).toHaveLength(30)

  failLastEntry = false
  fireEvent.click(screen.getByRole('button', { name: 'Retry candidates' }))

  await screen.findByText('31 of 31 candidates shown.')
  expect(screen.getAllByRole('button', { name: /^候補/ })).toHaveLength(31)

  // Successfully loaded entries from the first page weren't fetched again.
  expect(
    fetchEntry.mock.calls.filter(([sourceId]) => sourceId === 1),
  ).toHaveLength(1)
})

test('reloads candidates with the newly selected languages', async () => {
  fetchEntry.mockImplementation(async (sourceId) => makeEntry(sourceId))
  const onSelect = vi.fn()

  const { rerender } = render(
    <SentenceCandidates
      key="english"
      surface="ジム"
      sourceIds={[100]}
      languages={['eng']}
      selectedSourceId={null}
      onSelect={onSelect}
    />,
  )

  await screen.findByText('1 of 1 candidates shown.')

  rerender(
    <SentenceCandidates
      key="english-french"
      surface="ジム"
      sourceIds={[100]}
      languages={['eng', 'fre']}
      selectedSourceId={null}
      onSelect={onSelect}
    />,
  )

  await screen.findByText('1 of 1 candidates shown.')

  expect(fetchEntry).toHaveBeenLastCalledWith(
    100,
    expect.objectContaining({
      languages: ['eng', 'fre'],
    }),
  )
})