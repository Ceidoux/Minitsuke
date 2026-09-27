export type SentenceToken = {
  surface: string
  start: number
  end: number
  dictionary_form: string
  normalized_form: string
  reading: string
  part_of_speech: string[]
  is_unknown: boolean
  candidate_source_ids: number[]
}

export type SentenceGroup = {
  surface: string
  start: number
  end: number
  candidate_source_ids: number[]
  tokens: SentenceToken[]
}

export type SentenceAnalysis = {
  text: string
  offset_unit: 'unicode_code_points'
  groups: SentenceGroup[]
}

type AnalyzeSentenceOptions = {
  signal?: AbortSignal
}

export async function analyzeSentence(
  text: string,
  { signal }: AnalyzeSentenceOptions = {},
): Promise<SentenceAnalysis> {
  if (text.trim() === '') {
    throw new Error('Enter some text to analyze.')
  }

  const response = await fetch('/api/v1/analyze', {
    method: 'POST',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ text }),
    signal,
  })

  if (!response.ok) {
    throw new Error(`Sentence analysis failed (${response.status}).`)
  }

  return response.json()
}