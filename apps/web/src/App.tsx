import { useEffect, useRef } from 'react'
import SearchResults from './SearchResults'
import WordDetail from './WordDetail'
import { DICTIONARY_LANGUAGES } from './dictionary-languages'
import { useSearchLocation } from './use-search-location'
import './App.css'

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
        <p>Your Japanese dictionary.</p>
      </header>

      <main
        className={`dictionary-workspace${
          selectedSourceId !== null ? ' detail-open' : ''
        }`}
      >
        <div className="search-pane">
          <section
            className="search-section"
            aria-labelledby="search-heading"
          >
            <h2 id="search-heading">Search the dictionary</h2>

            <label htmlFor="word-search">
              Japanese or a selected definition language
            </label>
            <input
              id="word-search"
              className="search-input"
              type="search"
              name="q"
              placeholder="学校, tabe, school…"
              autoComplete="off"
              spellCheck={false}
              value={query}
              onChange={(event) => changeQuery(event.target.value)}
              onCompositionStart={beginComposition}
              onCompositionEnd={(event) => {
                finishComposition(event.currentTarget.value)
              }}
            />

            <p className="search-hint">
              Search by Japanese spelling, reading, romaji, or translation.
            </p>

            <fieldset
              className="language-selection"
              aria-describedby="language-help"
            >
              <legend>Definition languages</legend>

              <p id="language-help" className="search-hint">
                Show multiple languages together. Keep at least one selected.
              </p>

              <div className="language-options">
                {DICTIONARY_LANGUAGES.map((language) => {
                  const selected = languages.includes(language.code)

                  return (
                    <label className="language-option" key={language.code}>
                      <input
                        type="checkbox"
                        checked={selected}
                        disabled={selected && languages.length === 1}
                        onChange={() => toggleLanguage(language.code)}
                      />
                      <span lang={language.htmlLang}>
                        {language.label}
                      </span>
                    </label>
                  )
                })}
              </div>
            </fieldset>
          </section>

          {isComposing ? (
            <p role="status">Finish composing your text to search.</p>
          ) : normalizedQuery === '' ? (
            <p>Type a word to begin.</p>
          ) : (
            <SearchResults
              key={searchKey}
              query={normalizedQuery}
              languages={languages}
              selectedSourceId={selectedSourceId}
              onSelect={selectEntry}
            />
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