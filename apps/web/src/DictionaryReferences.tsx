import type {
  DictionaryReference,
  DictionaryReferenceTarget,
} from './dictionary-api'
import { writeSelectedEntry } from './entry-location'

type DictionaryReferencesProps = {
  label: string
  references: DictionaryReference[]
}

function targetHref(target: DictionaryReferenceTarget): string {
  const search = writeSelectedEntry(
    window.location.search,
    target.source_id,
  )

  const hash = target.sense_position === null
    ? ''
    : `#entry-${target.source_id}-sense-${target.sense_position}`

  return `${window.location.pathname}${search}${hash}`
}

export default function DictionaryReferences({
  label,
  references,
}: DictionaryReferencesProps) {
  if (references.length === 0) {
    return null
  }

  return (
    <div className="dictionary-references">
      <span className="entry-note">{label}: </span>

      {references.map((reference, index) => (
        <span key={`${index}-${reference.text}`}>
          {index > 0 && '; '}

          {reference.targets.length === 0 ? (
            <>
              <span lang="ja">{reference.text}</span>
              <span className="entry-note"> (target unavailable)</span>
            </>
          ) : reference.targets.length === 1 ? (
            <a href={targetHref(reference.targets[0])}>
              <span lang="ja">{reference.text}</span>
              {reference.targets[0].sense_position !== null && (
                <span>
                  {' — sense '}
                  {reference.targets[0].sense_position}
                </span>
              )}
            </a>
          ) : (
            <>
              <span lang="ja">{reference.text}</span>
              <span className="entry-note"> — possible targets: </span>

              {reference.targets.map((target, targetIndex) => (
                <span
                  key={`${target.source_id}-${target.sense_position}`}
                >
                  {targetIndex > 0 && ', '}
                  <a href={targetHref(target)}>
                    Entry {target.source_id}
                    {target.sense_position !== null && (
                      <> · sense {target.sense_position}</>
                    )}
                  </a>
                </span>
              ))}
            </>
          )}
        </span>
      ))}
    </div>
  )
}