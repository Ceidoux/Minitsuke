import { useState } from 'react'
import SearchResults from './SearchResults'
import './App.css'

export default function App() {
  const [query, setQuery] = useState('')
  const [isComposing, setIsComposing] = useState(false)

  const normalizedQuery = query.trim()

  return (
    <div className="app">
      <header className="app-header">
        <h1>Minitsuke</h1>
        <p>Your Japanese dictionary.</p>
      </header>

      <main>
        <section className="search-section" aria-labelledby="search-heading">
          <h2 id="search-heading">Search the dictionary</h2>

          <label htmlFor="word-search">Japanese or English</label>
          <input
            id="word-search"
            className="search-input"
            type="search"
            name="q"
            placeholder="学校, tabe, school…"
            autoComplete="off"
            spellCheck={false}
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            onCompositionStart={() => setIsComposing(true)}
            onCompositionEnd={(event) => {
              setQuery(event.currentTarget.value)
              setIsComposing(false)
            }}
          />

          <p className="search-hint">
            Search by Japanese spelling, reading, romaji, or English meaning.
          </p>
        </section>

        {isComposing ? (
          <p role="status">Finish composing your text to search.</p>
        ) : normalizedQuery === '' ? (
          <p>Type a word to begin.</p>
        ) : (
          <SearchResults key={normalizedQuery} query={normalizedQuery} />
        )}
      </main>
    </div>
  )
}