import { useEffect, useState } from 'react'
import { analyzeSentence } from './sentence-api'
import type { SentenceAnalysis as AnalysisResponse } from './sentence-api'
import SentenceCandidates from './SentenceCandidates'
import type { DictionaryLanguageCode } from './dictionary-languages'

type SentenceAnalysisProps = {
  query: string
  languages: DictionaryLanguageCode[]
  selectedSourceId: number | null
  onSelect: (sourceId: number, trigger: HTMLButtonElement) => void
}

export default function SentenceAnalysis({
  query,
  languages,
  selectedSourceId,
  onSelect,
}: SentenceAnalysisProps) {
  const [analysis, setAnalysis] = useState<AnalysisResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [attempt, setAttempt] = useState(0)
  const [selectedGroupIndex, setSelectedGroupIndex] = useState<number | null>(
    null,
  )

  const selectedGroup =
    selectedGroupIndex === null
      ? undefined
      : analysis?.groups[selectedGroupIndex]
  useEffect(() => {
    const controller = new AbortController()

    async function loadAnalysis() {
      try {
        const result = await analyzeSentence(query, {
          signal: controller.signal,
        })

        if (!controller.signal.aborted) {
          setAnalysis(result)
        }
      } catch (caught) {
        if (!controller.signal.aborted) {
          setError(
            caught instanceof Error
              ? caught.message
              : 'Unable to analyze this text.',
          )
        }
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false)
        }
      }
    }

    const timer = window.setTimeout(() => {
      void loadAnalysis()
    }, 200)

    return () => {
      window.clearTimeout(timer)
      controller.abort()
    }
  }, [query, attempt])

  function retry() {
    setError(null)
    setLoading(true)
    setAttempt((previous) => previous + 1)
  }

  // Avoid a redundant panel for a single unchanged dictionary word.
  // A conjugated word such as 食べました still benefits from analysis.
  const meaningfulGroups = analysis?.groups.filter(
    (group) =>
      group.surface.trim() !== '' &&
      group.tokens.some(
        (item) =>
          !['補助記号', '記号', '空白'].includes(
            item.part_of_speech[0] ?? '',
          ),
      ),
  ) ?? []

  const hasConjugation = meaningfulGroups.some(
    (group) =>
      group.tokens.length > 1 ||
      group.tokens[0]?.dictionary_form !== group.surface,
  )

  if (
    analysis &&
    !loading &&
    !error &&
    meaningfulGroups.length <= 1 &&
    !hasConjugation
  ) {
    return null
  }

  return (
    <section
      className="sentence-analysis"
      aria-labelledby="sentence-heading"
      aria-busy={loading}
    >
      <h2 id="sentence-heading">Words in your text</h2>

      {loading && <p role="status">Analyzing text…</p>}

      {error && (
        <div>
          <p role="alert">{error}</p>
          <button type="button" onClick={retry} disabled={loading}>
            Retry analysis
          </button>
        </div>
      )}

      {analysis && (
        <>
          <p className="entry-note">
            Select a segment to see its dictionary candidates, then select
            a card to open its details.
          </p>

          <div className="sentence-segments" lang="ja">
            {analysis.groups.map((group, index) => {
              const key = `${group.start}:${group.end}`

              if (group.candidate_source_ids.length === 0) {
                return (
                  <span className="sentence-unmatched" key={key}>
                    {group.surface}
                  </span>
                )
              }

              return (
                <button
                  key={key}
                  className="sentence-segment"
                  type="button"
                  aria-controls="sentence-candidates"
                  aria-pressed={index === selectedGroupIndex}
                  onClick={(event) => {
                    const selection = window.getSelection()

                    if (
                      event.detail !== 0 &&
                      selection &&
                      !selection.isCollapsed
                    ) {
                      return
                    }

                    setSelectedGroupIndex(index)
                  }}
                >
                  {group.surface}
                </button>
              )
            })}
          </div>

          {selectedGroup ? (
            <SentenceCandidates
              key={JSON.stringify([
                selectedGroup.start,
                selectedGroup.end,
                selectedGroup.candidate_source_ids,
                languages,
              ])}
              surface={selectedGroup.surface}
              sourceIds={selectedGroup.candidate_source_ids}
              languages={languages}
              selectedSourceId={selectedSourceId}
              onSelect={onSelect}
            />
          ) : (
            <p id="sentence-candidates">
              Select a segment above to see its candidates.
            </p>
          )}
        </>
      )}
    </section>
  )
}