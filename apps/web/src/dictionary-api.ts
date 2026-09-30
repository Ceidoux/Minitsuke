export type DictionaryReading = {
  text: string
  no_kanji: boolean
  restricted_to: string[]
  info?: string[]
}

export type DictionaryGloss = {
  text: string
  language: string
}

export type DictionaryReferenceTarget = {
  source_id: number
  sense_position: number | null
}

export type DictionaryReference = {
  text: string
  targets: DictionaryReferenceTarget[]
}

export type DictionarySense = {
  glosses: DictionaryGloss[]
  parts_of_speech: string[]
  restricted_to_written_forms: string[]
  restricted_to_readings: string[]
  misc?: string[]
  fields?: string[]
  dialects?: string[]
  notes?: string[]
  cross_references?: DictionaryReference[]
  antonyms?: DictionaryReference[]
}

export type ConjugatedForm = {
  group: string
  form: string
  written: string
  reading: string
}

export type ConjugationTable = {
  written: string
  reading: string
  verb_class: string
  sense_positions: number[]
  forms: ConjugatedForm[]
}

export type DictionaryEntry = {
  source_id: number
  is_common: boolean
  written_forms: string[]
  readings: DictionaryReading[]
  senses: DictionarySense[]
  conjugations?: ConjugationTable[]
  conjugations_incomplete?: boolean
  written_form_info?: Record<string, string[]>
}

export type ConjugationCompletion = {
  written: string
  reading: string
  group: string
  form: string
  description: string
}

export type InflectionMatch = {
  source_ids: number[]
  description: string
  descriptions?: Record<string, string[]>
  completions?: Record<string, ConjugationCompletion[]>
}

export type SearchResponse = {
  query: string
  results: DictionaryEntry[]
  limit: number
  offset: number
  has_more: boolean
  inflection?: InflectionMatch | null
}

type SearchOptions = {
  signal: AbortSignal
  offset?: number
  languages?: string[]
}

export async function searchDictionary(
  query: string,
  {
    signal,
    offset = 0,
    languages = ['eng'],
  }: SearchOptions,
): Promise<SearchResponse> {
  const normalizedQuery = query.trim()

  if (normalizedQuery === '') {
    throw new Error('Enter a word to search.')
  }

  const parameters = new URLSearchParams({
    q: normalizedQuery,
    limit: '30',
    offset: String(offset),
  })

  for (const language of languages) {
    parameters.append('languages', language)
  }

  const response = await fetch(`/api/v1/search?${parameters}`, {
    signal,
    headers: {
      Accept: 'application/json',
    },
  })

  if (!response.ok) {
    throw new Error(`Dictionary search failed (${response.status}).`)
  }

  const data: SearchResponse = await response.json()
  return data
}

type EntryOptions = {
  signal: AbortSignal
  languages: string[]
}

export async function fetchDictionaryEntry(
  sourceId: number,
  { signal, languages }: EntryOptions,
): Promise<DictionaryEntry> {
  const parameters = new URLSearchParams()

  for (const language of languages) {
    parameters.append('languages', language)
  }

  const response = await fetch(
    `/api/v1/entries/${sourceId}?${parameters}`,
    {
      signal,
      headers: {
        Accept: 'application/json',
      },
    },
  )

  if (response.status === 404) {
    throw new Error('This dictionary entry could not be found.')
  }

  if (!response.ok) {
    throw new Error(`Unable to load this entry (${response.status}).`)
  }

  const entry: DictionaryEntry = await response.json()
  return entry
}