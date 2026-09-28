import { useEffect, useState } from 'react'
import { searchDictionary } from './dictionary-api'
import type { SearchResponse } from './dictionary-api'
import type { DictionaryLanguageCode } from './dictionary-languages'
import WordCard from './WordCard'
import SentenceAnalysis from './SentenceAnalysis'
type SearchResultsProps = {
  query: string
  languages: DictionaryLanguageCode[]
  selectedSourceId: number | null
  onSelect: (sourceId: number, trigger: HTMLButtonElement) => void
}

export default function SearchResults({
  query,
  languages,
  selectedSourceId,
  onSelect,
}: SearchResultsProps) {
  const [page, setPage] = useState<SearchResponse | null>(null)
  const [offset, setOffset] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    const controller = new AbortController()

    async function loadResults() {
      try {
        const nextPage = await searchDictionary(query, {
          signal: controller.signal,
          offset,
          languages,
        })

        if (controller.signal.aborted) {
          return
        }

        setPage((previous) => ({
          ...nextPage,
          results:
            offset === 0
              ? nextPage.results
              : [...(previous?.results ?? []), ...nextPage.results],
        }))
      } catch (caught) {
        if (!controller.signal.aborted) {
          setError(
            caught instanceof Error
              ? caught.message
              : 'Unable to search the dictionary.',
          )
        }
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false)
        }
      }
    }

    const timer = window.setTimeout(() => {
      void loadResults()
    }, offset === 0 ? 200 : 0)

    return () => {
      window.clearTimeout(timer)
      controller.abort()
    }
  }, [query, languages, offset, attempt])

  function loadMore() {
    if (!page || loading) {
      return
    }

    setLoading(true)
    setError(null)
    setOffset(page.offset + page.limit)
  }

  function retry() {
    setLoading(true)
    setError(null)
    setAttempt((previous) => previous + 1)
  }
  const containsJapanese =
    /[\p{Script=Hiragana}\p{Script=Katakana}\p{Script=Han}]/u.test(query)

  const showSentenceAnalysis =
    containsJapanese &&
    (page !== null || error !== null) &&
    !page?.inflection
  return (
    <>
      {showSentenceAnalysis && (
        <SentenceAnalysis
          key={query}
          query={query}
          languages={languages}
          selectedSourceId={selectedSourceId}
          onSelect={onSelect}
        />
      )}

      <section aria-label="Results">
        {loading && (
          <p className="search-status" role="status">
            {page ? 'Loading more results…' : 'Searching…'}
          </p>
        )}

        {!loading && !error && page?.results.length === 0 && (
          <p className="search-status" role="status">
            No results for “{query}”.
          </p>
        )}

        {error && (
          <div className="search-error">
            <p role="alert">{error}</p>
            <button type="button" onClick={retry} disabled={loading}>
              Try again
            </button>
          </div>
        )}

        <div className="word-list" aria-busy={loading}>
          {page?.results.map((entry) => (
            <WordCard
              compact
              key={entry.source_id}
              entry={entry}
              searchQuery={page.query}
              completions={
                page.inflection?.completions?.[String(entry.source_id)]
              }
              selected={entry.source_id === selectedSourceId}
              onSelect={onSelect}
              inflection={
                page.inflection?.source_ids.includes(entry.source_id)
                  ? {
                      query: page.query,
                      description:
                        page.inflection.descriptions?.[
                          String(entry.source_id)
                        ]?.join(' / ') ?? page.inflection.description,
                    }
                  : undefined
              }
            />
          ))}
        </div>

        {page?.has_more && !error && (
          <button
            className="load-more"
            type="button"
            onClick={loadMore}
            disabled={loading}
          >
            {loading ? 'Loading…' : 'Load more'}
          </button>
        )}
      </section>
    </>
  )
}