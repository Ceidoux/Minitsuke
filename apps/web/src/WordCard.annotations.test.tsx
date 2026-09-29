import { render, screen, within } from '@testing-library/react'
import { expect, test } from 'vitest'
import type { DictionaryEntry } from './dictionary-api'
import { USUALLY_KANA } from './entry-presentation'
import WordCard from './WordCard'

function makeEntry(usuallyKana: boolean): DictionaryEntry {
  return {
    source_id: 1000001,
    is_common: false,
    written_forms: ['学校', '學校'],
    written_form_info: {
      學校: ['out-dated kanji or kanji usage'],
    },
    readings: [
      {
        text: 'がっこう',
        no_kanji: false,
        restricted_to: [],
        info: [],
      },
      {
        text: 'ガッコウ',
        no_kanji: false,
        restricted_to: ['學校'],
        info: ['rarely used kana form'],
      },
    ],
    senses: [
      {
        glosses: [{ text: 'school', language: 'eng' }],
        parts_of_speech: ['noun'],
        misc: usuallyKana ? [USUALLY_KANA] : [],
        restricted_to_written_forms: [],
        restricted_to_readings: [],
      },
    ],
  }
}

test.each([false, true])(
  'attaches annotations to their forms with compact=%s',
  (compact) => {
    render(
      <WordCard
        entry={makeEntry(false)}
        compact={compact}
        searchQuery="學"
      />,
    )

    const heading = screen.getByRole('heading', { level: 3 })
    const annotatedSpelling = within(heading)
      .getByText('(out-dated kanji or kanji usage)')
      .closest('.annotated-form')

    expect(annotatedSpelling).toHaveTextContent('學校')
    expect(annotatedSpelling?.querySelector('mark')).toHaveTextContent('學')

    const ordinarySpelling = within(heading)
      .getByText('学校')
      .closest('.annotated-form')

    expect(
      ordinarySpelling?.querySelector('.form-annotation'),
    ).toBeNull()

    const annotatedReading = screen
      .getByText('(rarely used kana form)')
      .closest('li')

    expect(annotatedReading).toHaveTextContent('ガッコウ')
    expect(annotatedReading).toHaveTextContent('applies to 學校')
  },
)

test('preserves annotations in the also-written list for kana-first headings', () => {
  render(<WordCard entry={makeEntry(true)} />)

  const heading = screen.getByRole('heading', { level: 3 })

  expect(heading).toHaveTextContent('がっこう')
  expect(heading).not.toHaveTextContent('out-dated')

  const annotation = screen.getByText(
    '(out-dated kanji or kanji usage)',
  )

  expect(annotation.closest('.alternate-written-forms')).not.toBeNull()
  expect(annotation.closest('.annotated-form')).toHaveTextContent('學校')
})

test('shows a search-only spelling as an annotated alternative', () => {
  const entry = makeEntry(false)
  entry.written_form_info = {
    學校: ['search-only kanji form'],
  }

  render(<WordCard entry={entry} searchQuery="學" />)

  const heading = screen.getByRole('heading', { level: 3 })

  expect(heading).toHaveTextContent('学校')
  expect(heading).not.toHaveTextContent('學校')

  const annotation = screen.getByText('(search-only kanji form)')
  const alternative = annotation.closest('.alternate-written-forms')

  expect(alternative).toHaveTextContent('學校')
  expect(alternative?.querySelector('mark')).toHaveTextContent('學')
})