import { useEffect, useRef, useState } from 'react'
import { fetchDictionaryEntry } from './dictionary-api'
import type { DictionaryEntry } from './dictionary-api'
import type { DictionaryLanguageCode } from './dictionary-languages'
import WordCard from './WordCard'
import ConjugationSection from './ConjugationSection'

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

    const detailRoot = useRef<HTMLDivElement | null>(null)

  const referenceMatch = window.location.hash.match(
    /^#entry-([0-9]+)-sense-([0-9]+)$/,
  )

  const requestedSense =
    referenceMatch && Number(referenceMatch[1]) === sourceId
      ? Number(referenceMatch[2])
      : null

  const targetSense =
    entry &&
    requestedSense !== null &&
    Number.isSafeInteger(requestedSense) &&
    requestedSense >= 1
      ? entry.senses[requestedSense - 1]
      : undefined

  useEffect(() => {
    if (!entry || !targetSense || requestedSense === null) {
      return
    }

    const target = detailRoot.current?.querySelector<HTMLElement>(
      `[data-sense-position="${requestedSense}"]`,
    )

    if (target) {
      target.scrollIntoView?.({ block: 'nearest' })
      target.focus({ preventScroll: true })
    }
  }, [entry, requestedSense, targetSense])

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
    <div ref={detailRoot} aria-busy={loading}>
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
          {requestedSense !== null && (
            <p className="entry-note" role="status">
              {!targetSense
                ? `Referenced sense ${requestedSense} is unavailable.`
                : targetSense.glosses.length === 0
                  ? `Referenced sense ${requestedSense} has no definition in the selected languages.`
                  : `Reference to sense ${requestedSense}.`}
            </p>
          )}
          <WordCard entry={entry} />
          <ConjugationSection
            key={entry.source_id}
            tables={entry.conjugations ?? []}
            incomplete={entry.conjugations_incomplete ?? false}
          />
          <p className="entry-note">JMdict entry: {entry.source_id}</p>
        </>
      )}
    </div>
  )
}