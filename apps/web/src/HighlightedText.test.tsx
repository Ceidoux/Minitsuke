import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import HighlightedText from './HighlightedText'

describe('HighlightedText', () => {
  it('highlights the matching Japanese characters', () => {
    render(
      <div data-testid="text">
        <HighlightedText text="食べる" query="食べ" />
      </div>,
    )

    const element = screen.getByTestId('text')

    expect(element.textContent).toBe('食べる')
    expect(element.querySelector('mark')?.textContent).toBe('食べ')
  })

  it('highlights only the typed part of a romaji completion', () => {
    render(
      <div data-testid="text">
        <HighlightedText text="takakunai" query="takakuna" />
      </div>,
    )

    const element = screen.getByTestId('text')

    expect(element.textContent).toBe('takakunai')
    expect(element.querySelector('mark')?.textContent).toBe('takakuna')
    expect(element.lastChild?.textContent).toBe('i')
  })

  it('treats search characters literally', () => {
    render(
      <div data-testid="text">
        <HighlightedText text="word[?]" query="[?]" />
      </div>,
    )

    expect(
      screen.getByTestId('text').querySelector('mark')?.textContent,
    ).toBe('[?]')
  })

  it('leaves unmatched text unchanged', () => {
    render(
      <div data-testid="text">
        <HighlightedText text="学校" query="食べ" />
      </div>,
    )

    const element = screen.getByTestId('text')

    expect(element.textContent).toBe('学校')
    expect(element.querySelector('mark')).toBeNull()
  })

  it('handles an empty query', () => {
    render(
      <div data-testid="text">
        <HighlightedText text="学校" query="" />
      </div>,
    )

    const element = screen.getByTestId('text')

    expect(element.textContent).toBe('学校')
    expect(element.querySelector('mark')).toBeNull()
  })
})

describe('romaji and kana highlighting', () => {
  it.each([
    ['tabe', 'たべる', 'たべ'],
    ['TABE', 'たべる', 'たべ'],
    ['kamera', 'カメラ', 'カメラ'],
    ['takakuna', 'たかくない', 'たかくな'],
    ['たべ', 'タベル', 'タベ'],
    ['食べ', '食べる', '食べ'],
  ])(
    'highlights %s inside %s',
    (query, text, expected) => {
      const { container } = render(
        <HighlightedText text={text} query={query} />,
      )

      expect(container.textContent).toBe(text)
      expect(container.querySelector('mark')?.textContent).toBe(expected)
    },
  )
})