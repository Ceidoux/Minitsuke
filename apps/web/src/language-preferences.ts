import type { DictionaryLanguageCode } from './dictionary-languages'
import { normalizeLanguages } from './search-location'

export const LANGUAGE_PREFERENCES_KEY = 'minitsuke.definition-languages'

export function readLanguagePreferences(): DictionaryLanguageCode[] {
  try {
    const stored = window.localStorage.getItem(LANGUAGE_PREFERENCES_KEY)

    if (stored === null) {
      return ['eng']
    }

    const parsed: unknown = JSON.parse(stored)

    if (!Array.isArray(parsed)) {
      return ['eng']
    }

    const codes = parsed.filter(
      (value): value is string => typeof value === 'string',
    )

    return normalizeLanguages(codes)
  } catch {
    return ['eng']
  }
}

export function saveLanguagePreferences(
  languages: readonly DictionaryLanguageCode[],
): void {
  try {
    window.localStorage.setItem(
      LANGUAGE_PREFERENCES_KEY,
      JSON.stringify(normalizeLanguages(languages)),
    )
  } catch {
    // Search remains usable when browser storage is unavailable.
  }
}