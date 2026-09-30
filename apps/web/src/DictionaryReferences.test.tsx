import { render, screen } from '@testing-library/react'
import { afterEach, expect, test } from 'vitest'
import DictionaryReferences from './DictionaryReferences'

const originalLocation =
  window.location.pathname +
  window.location.search +
  window.location.hash

afterEach(() => {
  window.history.replaceState(null, '', originalLocation)
})

test('preserves search and languages while linking to a numbered sense', () => {
  window.history.replaceState(
    null,
    '',
    '/?q=maru&languages=eng&languages=fre&entry=100#old',
  )

  render(
    <DictionaryReferences
      label="See also"
      references={[
        {
          text: '丸・まる・2',
          targets: [{ source_id: 200, sense_position: 2 }],
        },
      ]}
    />,
  )

  const link = screen.getByRole('link')
  const url = new URL(
    link.getAttribute('href')!,
    window.location.origin,
  )

  expect(url.searchParams.get('q')).toBe('maru')
  expect(url.searchParams.getAll('languages')).toEqual(['eng', 'fre'])
  expect(url.searchParams.get('entry')).toBe('200')
  expect(url.hash).toBe('#entry-200-sense-2')
})

test('retains unresolved references without creating links', () => {
  render(
    <DictionaryReferences
      label="See also"
      references={[{ text: '存在しない語', targets: [] }]}
    />,
  )

  expect(screen.getByText('存在しない語')).toBeVisible()
  expect(screen.getByText('(target unavailable)')).toBeVisible()
  expect(screen.queryByRole('link')).not.toBeInTheDocument()
})

test('shows separate links for ambiguous targets', () => {
  render(
    <DictionaryReferences
      label="Antonyms"
      references={[
        {
          text: 'まる',
          targets: [
            { source_id: 200, sense_position: null },
            { source_id: 300, sense_position: 1 },
          ],
        },
      ]}
    />,
  )

  expect(screen.getAllByRole('link')).toHaveLength(2)
  expect(screen.getByRole('link', { name: 'Entry 200' }))
    .toHaveAttribute('href', expect.stringContaining('entry=200'))
  expect(screen.getByRole('link', { name: 'Entry 300 · sense 1' }))
    .toHaveAttribute(
      'href',
      expect.stringContaining('#entry-300-sense-1'),
    )
})