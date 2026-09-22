import { useEffect, useState } from 'react'
import { searchDictionary } from './dictionary-api'
import type { SearchResponse } from './dictionary-api'
import type { DictionaryLanguageCode } from './dictionary-languages'
import WordCard from './WordCard'

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

  return (
    <section aria-labelledby="results-heading">
      <h2 id="results-heading">Results</h2>

      <p role="status">
        {loading
          ? page
            ? 'Loading more results…'
            : 'Searching…'
          : error
            ? 'Search could not be completed.'
            : page?.results.length === 0
              ? `No results for “${query}”.`
              : `${page?.results.length ?? 0} results shown.`}
      </p>

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
  key={entry.source_id}
  entry={entry}
  selected={entry.source_id === selectedSourceId}
  onSelect={onSelect}
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
  )
}