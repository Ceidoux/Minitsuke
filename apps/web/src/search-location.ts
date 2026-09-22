import { DICTIONARY_LANGUAGES } from './dictionary-languages'
import type { DictionaryLanguageCode } from './dictionary-languages'

export type SearchLocation = {
  query: string
  languages: DictionaryLanguageCode[]
}

export function normalizeLanguages(
  values: readonly string[],
): DictionaryLanguageCode[] {
  const selected = DICTIONARY_LANGUAGES
    .filter((language) => values.includes(language.code))
    .map((language) => language.code)

  return selected.length > 0 ? selected : ['eng']
}

export function readSearchLocation(
  search: string,
  preferredLanguages: readonly string[] = ['eng'],
): SearchLocation {
  const parameters = new URLSearchParams(search)

  return {
    query: parameters.get('q')?.trim() ?? '',
    languages: normalizeLanguages(
      parameters.has('languages')
        ? parameters.getAll('languages')
        : preferredLanguages,
    ),
  }
}

export function writeSearchLocation(
  state: SearchLocation,
  currentSearch = '',
): string {
  const parameters = new URLSearchParams(currentSearch)
  const query = state.query.trim()

  parameters.delete('q')
  parameters.delete('languages')

  if (query !== '') {
    parameters.set('q', query)
  }

  for (const language of normalizeLanguages(state.languages)) {
    parameters.append('languages', language)
  }

  return `?${parameters.toString()}`
}