import { toRomaji } from 'wanakana'
import type { ConjugationCompletion } from './dictionary-api'
import HighlightedText from './HighlightedText'

type ConjugationMatchesProps = {
  query: string
  matches: ConjugationCompletion[]
}

export default function ConjugationMatches({
  query,
  matches,
}: ConjugationMatchesProps) {
  if (matches.length === 0) {
    return null
  }

  const isRomaji = /^[a-z]+(?:'[a-z]+)*'?$/i.test(
    query.trim().normalize('NFKC'),
  )

  const visibleMatches = matches.slice(0, 3)
  const hiddenCount = matches.length - visibleMatches.length

  return (
    <div className="conjugation-matches">
      <p className="entry-note">Matches the start of:</p>

      <ul className="conjugation-match-list">
        {visibleMatches.map((match) => {
          const romanized = isRomaji ? toRomaji(match.reading) : null

          return (
            <li
              key={[
                match.written,
                match.reading,
                match.group,
                match.form,
              ].join(':')}
            >
              {romanized !== null && (
                <>
                  <HighlightedText text={romanized} query={query} />
                  {' · '}
                </>
              )}

              <span lang="ja">
                <HighlightedText text={match.written} query={query} />
              </span>

              {match.reading !== match.written && (
                <>
                  {' ('}
                  <span lang="ja">
                    <HighlightedText text={match.reading} query={query} />
                  </span>
                  {')'}
                </>
              )}

              {' — '}
              {match.description}
            </li>
          )
        })}
      </ul>

      {hiddenCount > 0 && (
        <p className="entry-note">
          {hiddenCount} more matching forms — open word details.
        </p>
      )}
    </div>
  )
}