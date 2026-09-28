type ConjugatedTextProps = {
  dictionaryForm: string
  text: string
  wordClass: string
}

function unchangedPrefix(
  dictionaryForm: string,
  text: string,
  wordClass: string,
): string {
  if (!dictionaryForm) {
    return ''
  }

  if (text === dictionaryForm) {
    return dictionaryForm
  }

  // Changed copulas are highlighted in full.
  if (wordClass === 'cop') {
    return ''
  }

  // Added constructions can preserve the complete dictionary form:
  // 高い → 高いです, 食べる → 食べるな.
  if (text.startsWith(dictionaryForm)) {
    return dictionaryForm
  }

  // Preserve the compound prefix, but highlight the changed する part.
  if (
    ['vs-i', 'vs-s', 'vs-s-aisu'].includes(wordClass) &&
    dictionaryForm.endsWith('する')
  ) {
    const prefix = dictionaryForm.slice(0, -2)
    return text.startsWith(prefix) ? prefix : ''
  }

  // Kana くる changes to き / こ / くれ.
  // Written 来 is handled by the ordinary comparison below.
  if (wordClass === 'vk' && dictionaryForm.endsWith('くる')) {
    const prefix = dictionaryForm.slice(0, -2)
    return text.startsWith(prefix) ? prefix : ''
  }

  const dictionaryCharacters = Array.from(dictionaryForm)
  const formCharacters = Array.from(text)
  let length = 0

  while (
    length < dictionaryCharacters.length &&
    length < formCharacters.length &&
    dictionaryCharacters[length] === formCharacters[length]
  ) {
    length += 1
  }

  return formCharacters.slice(0, length).join('')
}

export default function ConjugatedText({
  dictionaryForm,
  text,
  wordClass,
}: ConjugatedTextProps) {
  const prefix = unchangedPrefix(dictionaryForm, text, wordClass)
  const ending = text.slice(prefix.length)

  return (
    <>
      {prefix}
      {ending && (
        <span className="conjugation-ending">{ending}</span>
      )}
    </>
  )
}