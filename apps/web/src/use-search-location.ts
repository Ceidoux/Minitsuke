import { useEffect, useState } from 'react'
import { DICTIONARY_LANGUAGES } from './dictionary-languages'
import type { DictionaryLanguageCode } from './dictionary-languages'
import {
  readLanguagePreferences,
  saveLanguagePreferences,
} from './language-preferences'
import { readSearchLocation, writeSearchLocation } from './search-location'
import type { SearchLocation } from './search-location'

type SearchState = SearchLocation & {
  isComposing: boolean
}

function readBrowserSearch(): SearchState {
  return {
    ...readSearchLocation(
      window.location.search,
      readLanguagePreferences(),
    ),
    isComposing: false,
  }
}

function buildBrowserUrl(state: SearchLocation): string {
  return (
    window.location.pathname +
    writeSearchLocation(state, window.location.search) +
    window.location.hash
  )
}

function replaceBrowserUrl(state: SearchLocation) {
  window.history.replaceState(
    window.history.state,
    '',
    buildBrowserUrl(state),
  )
}

export function useSearchLocation() {
  const [state, setState] = useState<SearchState>(readBrowserSearch)

  useEffect(() => {
    // Record explicit languages so returning here restores this selection.
    replaceBrowserUrl(readBrowserSearch())
  }, [])

  useEffect(() => {
    let timer: number | undefined

    if (!state.isComposing) {
      timer = window.setTimeout(() => {
        const nextUrl = buildBrowserUrl(state)
        const currentUrl =
          window.location.pathname +
          window.location.search +
          window.location.hash

        if (nextUrl !== currentUrl) {
          window.history.pushState(null, '', nextUrl)
        }
      }, 200)
    }

    function restoreFromHistory() {
      window.clearTimeout(timer)

      const restored = readBrowserSearch()
      replaceBrowserUrl(restored)
      setState(restored)
    }

    window.addEventListener('popstate', restoreFromHistory)

    return () => {
      window.clearTimeout(timer)
      window.removeEventListener('popstate', restoreFromHistory)
    }
  }, [state])

  function changeQuery(query: string) {
    setState((previous) => ({
      ...previous,
      query,
    }))
  }

  function beginComposition() {
    setState((previous) => ({
      ...previous,
      isComposing: true,
    }))
  }

  function finishComposition(query: string) {
    setState((previous) => ({
      ...previous,
      query,
      isComposing: false,
    }))
  }

  function toggleLanguage(code: DictionaryLanguageCode) {
    const selected = state.languages.includes(code)

    if (selected && state.languages.length === 1) {
      return
    }

    const languages = DICTIONARY_LANGUAGES
      .filter((language) =>
        selected
          ? language.code !== code &&
            state.languages.includes(language.code)
          : language.code === code ||
            state.languages.includes(language.code),
      )
      .map((language) => language.code)

    saveLanguagePreferences(languages)

    setState((previous) => ({
      ...previous,
      languages,
    }))
  }

  return {
    ...state,
    changeQuery,
    beginComposition,
    finishComposition,
    toggleLanguage,
  }
}