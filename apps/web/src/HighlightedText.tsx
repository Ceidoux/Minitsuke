import { toHiragana, toKatakana } from 'wanakana'

type HighlightedTextProps = {
  text: string
  query: string
}

function lowercaseLatin(text: string): string {
  return text.replace(/[A-Z]/g, (character) => character.toLowerCase())
}

function getSearchTerms(query: string): string[] {
  const cleaned = query.trim().normalize('NFKC')

  if (!cleaned) {
    return []
  }

  const literal = lowercaseLatin(cleaned)
  const terms = new Set([literal])

  const isRomaji = /^[a-z]+(?:'[a-z]+)*'?$/.test(literal)
  const isKana = /^[ぁ-ゖァ-ヶー]+$/.test(literal)

  if (isRomaji || isKana) {
    const hiragana = toHiragana(literal, {
      convertLongVowelMark: false,
    })

    // Only add a converted term when conversion produced complete kana.
    if (/^[ぁ-ゖー]+$/.test(hiragana)) {
      terms.add(hiragana)
      terms.add(toKatakana(hiragana))
    }
  }

  return [...terms].sort((left, right) => right.length - left.length)
}

export default function HighlightedText({
  text,
  query,
}: HighlightedTextProps) {
  const terms = getSearchTerms(query)

  if (terms.length === 0) {
    return <>{text}</>
  }

  const searchableText = lowercaseLatin(text)
  const parts = []
  let cursor = 0

  while (cursor < text.length) {
    let matchStart = -1
    let matchLength = 0

    for (const term of terms) {
      const start = searchableText.indexOf(term, cursor)

      if (
        start !== -1 &&
        (
          matchStart === -1 ||
          start < matchStart ||
          (start === matchStart && term.length > matchLength)
        )
      ) {
        matchStart = start
        matchLength = term.length
      }
    }

    if (matchStart === -1) {
      parts.push(text.slice(cursor))
      break
    }

    if (matchStart > cursor) {
      parts.push(text.slice(cursor, matchStart))
    }

    const matchEnd = matchStart + matchLength

    parts.push(
      <mark className="search-match" key={matchStart}>
        {text.slice(matchStart, matchEnd)}
      </mark>,
    )

    cursor = matchEnd
  }

  return <>{parts}</>
}