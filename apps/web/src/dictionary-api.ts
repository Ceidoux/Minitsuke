export type DictionaryReading = {
  text: string
  no_kanji: boolean
  restricted_to: string[]
}

export type DictionaryGloss = {
  text: string
  language: string
}

export type DictionarySense = {
  glosses: DictionaryGloss[]
  parts_of_speech: string[]
  restricted_to_written_forms: string[]
  restricted_to_readings: string[]
}

export type DictionaryEntry = {
  source_id: number
  is_common: boolean
  written_forms: string[]
  readings: DictionaryReading[]
  senses: DictionarySense[]
}

export type SearchResponse = {
  query: string
  results: DictionaryEntry[]
  limit: number
  offset: number
  has_more: boolean
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