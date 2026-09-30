import {
  getEntryHeading,
  isUsuallyKana,
  USUALLY_KANA,
} from './entry-presentation'
import type {
  ConjugationCompletion,
  DictionaryEntry,
} from './dictionary-api'
import ConjugationMatches from './ConjugationMatches'

import { DICTIONARY_LANGUAGES } from './dictionary-languages'
import HighlightedText from './HighlightedText'
import AnnotatedForm from './AnnotatedForm'
import DictionaryReferences from './DictionaryReferences'

type WordCardProps = {
  entry: DictionaryEntry
  searchQuery?: string
  selected?: boolean
  onSelect?: (sourceId: number, trigger: HTMLButtonElement) => void
  inflection?: {
    query: string
    description: string
  }
  compact?: boolean
  completions?: ConjugationCompletion[]
}

export default function WordCard({
  entry,
  searchQuery = '',
  completions = [],
  selected = false,
  onSelect,
  inflection,
  compact = false,
}: WordCardProps) {
  const {
    title,
    titleWrittenForms,
    alternateWrittenForms,
  } = getEntryHeading(entry)
  function renderWrittenForms(forms: string[]) {
    return forms.map((form, index) => (
      <span key={form}>
        {index > 0 && ' / '}
        <AnnotatedForm
          text={form}
          query={searchQuery}
          info={entry.written_form_info?.[form]}
        />
      </span>
    ))
  }

  const headingContent =
    titleWrittenForms.length > 0 ? (
      renderWrittenForms(titleWrittenForms)
    ) : (
      <AnnotatedForm
        text={title}
        query={searchQuery}
        info={entry.readings.find((reading) => reading.text === title)?.info}
      />
    )
  const availableSenses = entry.senses
      .map((sense, sourcePosition) => ({
        ...sense,
        sourcePosition,
        usageLabels: Array.from(new Set(sense.misc ?? []))
          .filter((label) => label !== USUALLY_KANA),
      }))
    .filter((sense) => sense.glosses.length > 0)

  const displayedSenses = compact
    ? availableSenses.slice(0, 4)
    : availableSenses

  const hiddenSenseCount = availableSenses.length - displayedSenses.length

  const languageGroups = DICTIONARY_LANGUAGES
    .map((language) => ({
      language,
      senses: displayedSenses
        .map((sense) => ({
          ...sense,
          glosses: sense.glosses.filter(
            (gloss) => gloss.language === language.code,
          ),
        }))
        .filter((sense) => sense.glosses.length > 0),
    }))
    .filter((group) => group.senses.length > 0)
  return (
<article
  className={[
    'word-card',
    compact ? 'word-card-compact' : '',
    selected ? 'word-card-selected' : '',
    onSelect ? 'word-card-clickable' : '',
  ].filter(Boolean).join(' ')}
  onClick={onSelect ? (event) => {
    const target = event.target

    if (!(target instanceof Element)) {
      return
    }

    // The title button handles its own clicks.
    if (target.closest('button, a, input, select, textarea')) {
      return
    }

    // Dragging to select text should not open the entry.
    const selection = window.getSelection()

    if (selection && !selection.isCollapsed) {
      return
    }

    const button = event.currentTarget.querySelector<HTMLButtonElement>(
      '.word-title-button',
    )

    if (button) {
      button.click()
    }
  } : undefined}
>
      <div className="word-heading">
        <h3 lang="ja">
  {onSelect ? (
    <button
      className="word-title-button"
      aria-label={title}
      type="button"
      aria-controls="word-detail-panel"
      aria-pressed={selected}
      onClick={(event) => {
  const selection = window.getSelection()

  // Ignore mouse clicks ending a text selection.
  // Keyboard activation still opens the entry.
  if (
    event.detail !== 0 &&
    selection &&
    !selection.isCollapsed
  ) {
    return
  }

  onSelect(entry.source_id, event.currentTarget)
}}
    >
{headingContent}
    </button>
  ) : (
headingContent
  )}
</h3>
        {alternateWrittenForms.length > 0 && (
          <span className="alternate-written-forms">
            Also written:{' '}
            {renderWrittenForms(alternateWrittenForms)}
          </span>
        )}
        {entry.is_common && <span className="common-badge">Common</span>}
      </div>
      {inflection && (
        <p className="inflection-note">
          <span>
            <HighlightedText
              text={inflection.query}
              query={searchQuery}
            />
          </span>          {' — '}
          {inflection.description}
        </p>
      )}
      <ConjugationMatches
        query={searchQuery}
        matches={completions}
      />
      <ul className="reading-list">
        {entry.readings.map((reading) => (
          <li key={reading.text}>
            <AnnotatedForm
              text={reading.text}
              query={searchQuery}
              info={reading.info}
            />
            {reading.no_kanji && (
              <span className="entry-note"> — used without kanji</span>
            )}

            {reading.restricted_to.length > 0 && (
              <span className="entry-note">
                {' — applies to '}
                <span lang="ja">{reading.restricted_to.join(' / ')}</span>
              </span>
            )}
          </li>
        ))}
      </ul>

      {languageGroups.length === 0 ? (
        <p>No definitions in the selected languages.</p>
      ) : (
        languageGroups.map(({ language, senses }) => (
          <section className="definition-language" key={language.code}>
            <h4 lang={language.htmlLang}>{language.label}</h4>

            <ol className="sense-list">
              {senses.map((sense) => (
              <li
                key={sense.sourcePosition}
                data-sense-position={sense.sourcePosition + 1}
                tabIndex={-1}
              >
                  {(isUsuallyKana(sense) ||
                    sense.usageLabels.length > 0 ||
                    sense.parts_of_speech.length > 0) && (
                    <div className="sense-meta">
                      {isUsuallyKana(sense) && (
                        <span className="usage-badge">Usually kana</span>
                      )}

                      {sense.usageLabels.map((label) => (
                        <span className="usage-badge" key={label}>
                          {label}
                        </span>
                      ))}

                      {sense.parts_of_speech.length > 0 && (
                        <span className="entry-note">
                          {sense.parts_of_speech.join(' · ')}
                        </span>
                      )}
                    </div>
                  )}
                  {((sense.fields?.length ?? 0) > 0 ||
                    (sense.dialects?.length ?? 0) > 0) && (
                    <div className="sense-meta">
                      {(sense.fields ?? []).map((field, index) => (
                        <span
                          className="entry-note"
                          key={`field-${index}`}
                        >
                          Field: {field}
                        </span>
                      ))}

                      {(sense.dialects ?? []).map((dialect, index) => (
                        <span
                          className="entry-note"
                          key={`dialect-${index}`}
                        >
                          Dialect: {dialect}
                        </span>
                      ))}
                    </div>
                  )}
                  <p lang={language.htmlLang}>
                    {sense.glosses.map((gloss) => gloss.text).join('; ')}
                  </p>
                  {(sense.notes ?? []).map((note, index) => (
                    <p className="entry-note" key={`note-${index}`}>
                      {note}
                    </p>
                  ))}
                  {sense.restricted_to_written_forms.length > 0 && (
                    <p className="entry-note">
                      Applies to written forms:{' '}
                      <span lang="ja">
                        {sense.restricted_to_written_forms.join(' / ')}
                      </span>
                    </p>
                  )}

                  {sense.restricted_to_readings.length > 0 && (
                    <p className="entry-note">
                      Applies to readings:{' '}
                      <span lang="ja">
                        {sense.restricted_to_readings.join(' / ')}
                      </span>
                    </p>
                  )}
                                    <DictionaryReferences
                    label="See also"
                    references={sense.cross_references ?? []}
                  />
                  <DictionaryReferences
                    label="Antonyms"
                    references={sense.antonyms ?? []}
                  />
                </li>
              ))}
            </ol>
          </section>
        ))
      )}
      {hiddenSenseCount > 0 && (
        <p className="entry-note">
          {hiddenSenseCount} more {hiddenSenseCount === 1 ? 'sense' : 'senses'}
          {' — open word details to see all.'}
        </p>
      )}
    </article>
  )
}