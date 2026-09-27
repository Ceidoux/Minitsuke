import { useEffect, useRef, useState } from 'react'
import { DICTIONARY_LANGUAGES } from './dictionary-languages'
import type { DictionaryLanguageCode } from './dictionary-languages'

type OptionsMenuProps = {
  languages: DictionaryLanguageCode[]
  toggleLanguage: (language: DictionaryLanguageCode) => void
}

export default function OptionsMenu({
  languages,
  toggleLanguage,
}: OptionsMenuProps) {
  const [open, setOpen] = useState(false)
  const [languagesOpen, setLanguagesOpen] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)
  const buttonRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    if (!open) {
      return
    }

    function handlePointerDown(event: PointerEvent) {
      if (
        event.target instanceof Node &&
        !containerRef.current?.contains(event.target)
      ) {
        setOpen(false)
        setLanguagesOpen(false)
      }
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        setOpen(false)
        setLanguagesOpen(false)
        buttonRef.current?.focus()
      }
    }

    document.addEventListener('pointerdown', handlePointerDown)
    document.addEventListener('keydown', handleKeyDown)

    return () => {
      document.removeEventListener('pointerdown', handlePointerDown)
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [open])

  return (
    <div className="options-menu" ref={containerRef}>
      <button
        ref={buttonRef}
        className="options-toggle"
        type="button"
        aria-label="Options"
        aria-expanded={open}
        aria-controls="app-options"
        onClick={() => {
          setOpen(!open)
          setLanguagesOpen(false)
        }}
      >
        <svg
          width="22"
          height="22"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          aria-hidden="true"
        >
          <path d="M4 6h16M4 12h16M4 18h16" />
        </svg>
      </button>

      {open && (
        <div className="options-panel" id="app-options">
          <button
            className="options-item"
            type="button"
            aria-expanded={languagesOpen}
            aria-controls="language-options"
            onClick={() => setLanguagesOpen(!languagesOpen)}
          >
            <span>Languages</span>
            <span aria-hidden="true">{languagesOpen ? '−' : '+'}</span>
          </button>

          {languagesOpen && (
            <fieldset
              className="menu-languages"
              id="language-options"
              aria-describedby="language-help"
            >
              <legend className="visually-hidden">
                Definition languages
              </legend>

              <p id="language-help" className="entry-note">
                Choose one or more definition languages.
              </p>

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
            </fieldset>
          )}
        </div>
      )}
    </div>
  )
}