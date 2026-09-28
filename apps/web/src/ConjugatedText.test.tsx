import { render } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import ConjugatedText from './ConjugatedText'

describe('ConjugatedText', () => {
  it.each([
    ['食べる', '食べません', 'v1', 'ません'],
    ['たべる', 'たべません', 'v1', 'ません'],
    ['書く', '書ける', 'v5k', 'ける'],
    ['高い', '高かった', 'adj-i', 'かった'],
    ['高い', '高いです', 'adj-i', 'です'],
    ['いい', 'よかった', 'adj-ix', 'よかった'],
    ['かっこいい', 'かっこよかった', 'adj-ix', 'よかった'],
    ['静か', '静かではない', 'adj-na', 'ではない'],
    ['静か', '静かな', 'adj-na', 'な'],
    ['する', 'しました', 'vs-i', 'しました'],
    ['する', 'すれば', 'vs-i', 'すれば'],
    ['確認する', '確認しました', 'vs-i', 'しました'],
    ['来る', '来ました', 'vk', 'ました'],
    ['くる', 'きました', 'vk', 'きました'],
    ['くる', 'くれば', 'vk', 'くれば'],
    ['だ', 'だった', 'cop', 'だった'],
    ['食べる', '食べるな', 'v1', 'な'],
  ])(
    'highlights the changed ending in %s → %s',
    (dictionaryForm, text, wordClass, expectedEnding) => {
      const { container } = render(
        <ConjugatedText
          dictionaryForm={dictionaryForm}
          text={text}
          wordClass={wordClass}
        />,
      )

      expect(container.textContent).toBe(text)
      expect(
        container.querySelector('.conjugation-ending')?.textContent,
      ).toBe(expectedEnding)
    },
  )

  it('does not highlight an unchanged dictionary form', () => {
    const { container } = render(
      <ConjugatedText
        dictionaryForm="食べる"
        text="食べる"
        wordClass="v1"
      />,
    )

    expect(container.textContent).toBe('食べる')
    expect(container.querySelector('.conjugation-ending')).toBeNull()
  })
})