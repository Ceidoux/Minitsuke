import SearchResults from './SearchResults'
import { DICTIONARY_LANGUAGES } from './dictionary-languages'
import { useSearchLocation } from './use-search-location'
import './App.css'

export default function App() {
  const {
    query,
    languages,
    isComposing,
    changeQuery,
    beginComposition,
    finishComposition,
    toggleLanguage,
  } = useSearchLocation()

  const normalizedQuery = query.trim()
  const searchKey = JSON.stringify([normalizedQuery, languages])

  return (
    <div className="app">
      <header className="app-header">
        <h1>Minitsuke</h1>
        <p>Your Japanese dictionary.</p>
      </header>

      <main>
        <section className="search-section" aria-labelledby="search-heading">
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
                    <span lang={language.htmlLang}>{language.label}</span>
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
          />
        )}
      </main>
    </div>
  )
}