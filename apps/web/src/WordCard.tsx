import type { DictionaryEntry } from './dictionary-api'
import { DICTIONARY_LANGUAGES } from './dictionary-languages'

type WordCardProps = {
  entry: DictionaryEntry
  selected?: boolean
  onSelect?: (sourceId: number, trigger: HTMLButtonElement) => void
}

export default function WordCard({
  entry,
  selected = false,
  onSelect,
}: WordCardProps) {
  const title =
    entry.written_forms.join(' / ') || entry.readings[0]?.text || 'Entry'

  const languageGroups = DICTIONARY_LANGUAGES
    .map((language) => ({
      language,
      senses: entry.senses
        .map((sense, sourcePosition) => ({
          ...sense,
          sourcePosition,
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
      {title}
    </button>
  ) : (
    title
  )}
</h3>
        {entry.is_common && <span className="common-badge">Common</span>}
      </div>

      <ul className="reading-list">
        {entry.readings.map((reading) => (
          <li key={reading.text}>
            <span lang="ja">{reading.text}</span>

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
                <li key={sense.sourcePosition}>
                  {sense.parts_of_speech.length > 0 && (
                    <p className="entry-note">
                      {sense.parts_of_speech.join('; ')}
                    </p>
                  )}

                  <p lang={language.htmlLang}>
                    {sense.glosses.map((gloss) => gloss.text).join('; ')}
                  </p>

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
                </li>
              ))}
            </ol>
          </section>
        ))
      )}
    </article>
  )
}