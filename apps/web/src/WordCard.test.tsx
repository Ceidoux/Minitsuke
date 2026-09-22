import { render, screen, within } from '@testing-library/react'
import { expect, test } from 'vitest'
import type { DictionaryEntry } from './dictionary-api'
import WordCard from './WordCard'

test('groups languages in a fixed order while preserving senses and restrictions', () => {
  const entry: DictionaryEntry = {
    source_id: 1206730,
    is_common: true,
    written_forms: ['学校'],
    readings: [
      {
        text: 'がっこう',
        no_kanji: false,
        restricted_to: [],
      },
    ],
    senses: [
      {
        glosses: [{ text: 'école', language: 'fre' }],
        parts_of_speech: ['noun'],
        restricted_to_written_forms: ['学校'],
        restricted_to_readings: [],
      },
      {
        glosses: [
          { text: 'school', language: 'eng' },
          { text: 'educational institution', language: 'eng' },
        ],
        parts_of_speech: ['noun'],
        restricted_to_written_forms: [],
        restricted_to_readings: [],
      },
      {
        glosses: [
          { text: 'school of thought', language: 'eng' },
          { text: 'courant de pensée', language: 'fre' },
        ],
        parts_of_speech: ['noun'],
        restricted_to_written_forms: [],
        restricted_to_readings: ['がっこう'],
      },
      {
        glosses: [],
        parts_of_speech: ['noun'],
        restricted_to_written_forms: [],
        restricted_to_readings: [],
      },
    ],
  }

  render(<WordCard entry={entry} />)

  expect(screen.getAllByRole('article')).toHaveLength(1)

  const headings = screen.getAllByRole('heading', { level: 4 })
  expect(headings.map((heading) => heading.textContent)).toEqual([
    'English',
    'Français',
  ])

  const englishSection = headings[0].closest('section')!
  const frenchSection = headings[1].closest('section')!

  const english = within(englishSection)
  const french = within(frenchSection)

  expect(english.getAllByRole('listitem')).toHaveLength(2)
  expect(french.getAllByRole('listitem')).toHaveLength(2)

  expect(
    english.getByText('school; educational institution'),
  ).toHaveAttribute('lang', 'en')
  expect(english.getByText('school of thought')).toBeVisible()
  expect(english.queryByText('école')).not.toBeInTheDocument()

  expect(french.getByText('école')).toHaveAttribute('lang', 'fr')
  expect(french.getByText('courant de pensée')).toBeVisible()
  expect(
    french.queryByText('school; educational institution'),
  ).not.toBeInTheDocument()

  expect(
    french.getByText(/Applies to written forms:/),
  ).toHaveTextContent('学校')

  expect(
    english.getByText(/Applies to readings:/),
  ).toHaveTextContent('がっこう')

  expect(
    french.getByText(/Applies to readings:/),
  ).toHaveTextContent('がっこう')
})