import { useEffect, useRef, useState } from 'react'
import { DICTIONARY_LANGUAGES } from './dictionary-languages'
import type { DictionaryLanguageCode } from './dictionary-languages'
import { readSelectedEntry, writeSelectedEntry } from './entry-location'
import {
  readLanguagePreferences,
  saveLanguagePreferences,
} from './language-preferences'
import { readSearchLocation, writeSearchLocation } from './search-location'
import type { SearchLocation } from './search-location'

type SearchState = SearchLocation & {
  isComposing: boolean
  selectedSourceId: number | null
}

function readBrowserSearch(): SearchState {
  return {
    ...readSearchLocation(
      window.location.search,
      readLanguagePreferences(),
    ),
    isComposing: false,
    selectedSourceId: readSelectedEntry(window.location.search),
  }
}

function buildBrowserUrl(state: SearchState): string {
  const search = writeSelectedEntry(
    writeSearchLocation(state, window.location.search),
    state.selectedSourceId,
  )

  return window.location.pathname + search + window.location.hash
}

function currentBrowserUrl(): string {
  return (
    window.location.pathname +
    window.location.search +
    window.location.hash
  )
}

function replaceBrowserUrl(state: SearchState) {
  window.history.replaceState(
    window.history.state,
    '',
    buildBrowserUrl(state),
  )
}

function pushBrowserUrl(state: SearchState) {
  const nextUrl = buildBrowserUrl(state)

  if (nextUrl !== currentBrowserUrl()) {
    window.history.pushState(null, '', nextUrl)
  }
}

export function useSearchLocation() {
  const [state, setState] = useState<SearchState>(readBrowserSearch)
  const pendingTimer = useRef<number | undefined>(undefined)

  useEffect(() => {
    replaceBrowserUrl(readBrowserSearch())
  }, [])

  useEffect(() => {
    if (!state.isComposing) {
      pendingTimer.current = window.setTimeout(() => {
        pushBrowserUrl(state)
      }, 200)
    }

    function restoreFromHistory() {
      window.clearTimeout(pendingTimer.current)

      const restored = readBrowserSearch()
      replaceBrowserUrl(restored)

      setState((previous) => ({
        ...restored,
        languages:
          previous.languages.join(',') === restored.languages.join(',')
            ? previous.languages
            : restored.languages,
      }))
    }

    window.addEventListener('popstate', restoreFromHistory)

    return () => {
      window.clearTimeout(pendingTimer.current)
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

  function selectSourceId(sourceId: number | null) {
    if (sourceId === state.selectedSourceId) {
      return
    }

    window.clearTimeout(pendingTimer.current)

    // Record any pending search before recording the word selection.
    pushBrowserUrl(state)

    const nextState = {
      ...state,
      selectedSourceId: sourceId,
    }

    pushBrowserUrl(nextState)
    setState(nextState)
  }

  return {
    ...state,
    changeQuery,
    beginComposition,
    finishComposition,
    toggleLanguage,
    selectSourceId,
  }
}