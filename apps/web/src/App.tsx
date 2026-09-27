import { useEffect, useRef } from 'react'
import SearchResults from './SearchResults'
import WordDetail from './WordDetail'
import { useSearchLocation } from './use-search-location'
import './App.css'
import OptionsMenu from './OptionsMenu'

export default function App() {
  const {
    query,
    languages,
    isComposing,
    selectedSourceId,
    changeQuery,
    beginComposition,
    finishComposition,
    toggleLanguage,
    selectSourceId,
  } = useSearchLocation()

  const selectedButton = useRef<HTMLButtonElement | null>(null)
  const closeButton = useRef<HTMLButtonElement | null>(null)

  const normalizedQuery = query.trim()
  const searchKey = JSON.stringify([normalizedQuery, languages])
  const detailKey = JSON.stringify([selectedSourceId, languages])

  useEffect(() => {
    if (selectedSourceId !== null) {
      closeButton.current?.focus({ preventScroll: true })
    }
  }, [selectedSourceId])

  function selectEntry(sourceId: number, trigger: HTMLButtonElement) {
    selectedButton.current = trigger
    selectSourceId(sourceId)
  }

  function closeEntry() {
    selectSourceId(null)

    window.requestAnimationFrame(() => {
      const trigger = selectedButton.current

      if (trigger?.isConnected) {
        trigger.focus({ preventScroll: true })
      } else {
        document.getElementById('word-search')?.focus({
          preventScroll: true,
        })
      }
    })
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>Minitsuke</h1>
        <OptionsMenu
          languages={languages}
          toggleLanguage={toggleLanguage}
        />
      </header>

      <main
        className={`dictionary-workspace${
          selectedSourceId !== null ? ' detail-open' : ''
        }`}
      >
        <div className="search-pane">
          <section className="search-section" aria-label="Dictionary search">
            <label className="visually-hidden" htmlFor="word-search">
              Japanese, romaji, or a selected definition language
            </label>
            <input
              id="word-search"
              className="search-input"
              type="search"
              name="q"
              placeholder="学校, tabemasu, school…"
              autoComplete="off"
              spellCheck={false}
              value={query}
              onChange={(event) => changeQuery(event.target.value)}
              onCompositionStart={beginComposition}
              onCompositionEnd={(event) => {
                finishComposition(event.currentTarget.value)
              }}
            />
          </section>

          {isComposing ? (
            <p role="status">Finish composing your text to search.</p>
          ) : normalizedQuery === '' ? (
            <p>Type a word to begin.</p>
          ) : (
            <>
            <SearchResults
              key={searchKey}
              query={normalizedQuery}
              languages={languages}
              selectedSourceId={selectedSourceId}
              onSelect={selectEntry}
            />
            </>
          )}
        </div>

        <section
          id="word-detail-panel"
          className="detail-pane"
          aria-labelledby="detail-heading"
        >
          <div className="detail-toolbar">
            <h2 id="detail-heading">Word details</h2>

            {selectedSourceId !== null && (
              <button
                ref={closeButton}
                type="button"
                onClick={closeEntry}
              >
                Back to results
              </button>
            )}
          </div>

          {selectedSourceId === null ? (
            <p>Select a word from the results to see its details.</p>
          ) : (
            <WordDetail
              key={detailKey}
              sourceId={selectedSourceId}
              languages={languages}
            />
          )}
        </section>
      </main>
    </div>
  )
}