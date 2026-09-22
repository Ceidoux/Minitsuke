import { useEffect, useState } from 'react'
import { fetchDictionaryEntry } from './dictionary-api'
import type { DictionaryEntry } from './dictionary-api'
import type { DictionaryLanguageCode } from './dictionary-languages'
import WordCard from './WordCard'

type WordDetailProps = {
  sourceId: number
  languages: DictionaryLanguageCode[]
}

export default function WordDetail({
  sourceId,
  languages,
}: WordDetailProps) {
  const [entry, setEntry] = useState<DictionaryEntry | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    const controller = new AbortController()

    async function loadEntry() {
      try {
        const result = await fetchDictionaryEntry(sourceId, {
          signal: controller.signal,
          languages,
        })

        if (!controller.signal.aborted) {
          setEntry(result)
        }
      } catch (caught) {
        if (!controller.signal.aborted) {
          setError(
            caught instanceof Error
              ? caught.message
              : 'Unable to load this entry.',
          )
        }
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false)
        }
      }
    }

    void loadEntry()

    return () => controller.abort()
  }, [sourceId, languages, attempt])

  function retry() {
    setError(null)
    setLoading(true)
    setAttempt((previous) => previous + 1)
  }

  return (
    <div aria-busy={loading}>
      {loading && <p role="status">Loading word details…</p>}

      {error && (
        <div className="search-error">
          <p role="alert">{error}</p>
          <button type="button" onClick={retry} disabled={loading}>
            Retry loading word
          </button>
        </div>
      )}

      {entry && (
        <>
          <WordCard entry={entry} />
          <p className="entry-note">JMdict entry: {entry.source_id}</p>
        </>
      )}
    </div>
  )
}