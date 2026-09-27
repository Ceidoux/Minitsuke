import { useEffect, useState } from 'react'
import { fetchDictionaryEntry } from './dictionary-api'
import type { DictionaryEntry } from './dictionary-api'
import type { DictionaryLanguageCode } from './dictionary-languages'
import WordCard from './WordCard'

type SentenceCandidatesProps = {
  surface: string
  sourceIds: number[]
  languages: DictionaryLanguageCode[]
  selectedSourceId: number | null
  onSelect: (sourceId: number, trigger: HTMLButtonElement) => void
}

const PAGE_SIZE = 30

export default function SentenceCandidates({
  surface,
  sourceIds,
  languages,
  selectedSourceId,
  onSelect,
}: SentenceCandidatesProps) {
  const [entries, setEntries] = useState<DictionaryEntry[]>([])
  const [offset, setOffset] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    const controller = new AbortController()

    async function loadCandidates() {
      try {
        const pageIds = sourceIds.slice(offset, offset + PAGE_SIZE)
        const loaded: DictionaryEntry[] = []

        for (let index = 0; index < pageIds.length; index += 4) {
          if (controller.signal.aborted) {
            return
          }

          const batch = await Promise.all(
            pageIds.slice(index, index + 4).map((sourceId) =>
              fetchDictionaryEntry(sourceId, {
                signal: controller.signal,
                languages,
              }),
            ),
          )

          loaded.push(...batch)
        }

        if (controller.signal.aborted) {
          return
        }

        setEntries((previous) =>
          offset === 0 ? loaded : [...previous, ...loaded],
        )
      } catch (caught) {
        if (!controller.signal.aborted) {
          setError(
            caught instanceof Error
              ? caught.message
              : 'Unable to load candidate entries.',
          )
        }
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false)
        }
      }
    }

    void loadCandidates()

    return () => controller.abort()
  }, [sourceIds, languages, offset, attempt])

  function loadMore() {
    if (loading || error) {
      return
    }

    setLoading(true)
    setOffset(entries.length)
  }

  function retry() {
    setLoading(true)
    setError(null)
    setAttempt((previous) => previous + 1)
  }

  return (
    <section
      id="sentence-candidates"
      className="sentence-candidates"
      aria-labelledby="sentence-candidates-heading"
    >
      <h3 id="sentence-candidates-heading">
        Matches for <span lang="ja">{surface}</span>
      </h3>

      <p role="status">
        {loading
          ? 'Loading candidate entries…'
          : error
            ? 'Candidate entries could not be loaded.'
            : `${entries.length} of ${sourceIds.length} candidates shown.`}
      </p>

      {error && (
        <div className="search-error">
          <p role="alert">{error}</p>
          <button type="button" onClick={retry} disabled={loading}>
            Retry candidates
          </button>
        </div>
      )}

      <div className="word-list" aria-busy={loading}>
        {entries.map((entry) => (
          <WordCard
            key={entry.source_id}
            entry={entry}
            selected={entry.source_id === selectedSourceId}
            onSelect={onSelect}
          />
        ))}
      </div>

      {!error && entries.length < sourceIds.length && (
        <button type="button" onClick={loadMore} disabled={loading}>
          {loading ? 'Loading…' : 'Load more candidates'}
        </button>
      )}
    </section>
  )
}