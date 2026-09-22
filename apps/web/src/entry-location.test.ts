import { expect, test } from 'vitest'
import { readSelectedEntry, writeSelectedEntry } from './entry-location'

test('reads a selected JMdict entry', () => {
  expect(readSelectedEntry('?q=school&entry=1206730')).toBe(1206730)
})

test.each([
  '',
  '?entry=',
  '?entry=abc',
  '?entry=0',
  '?entry=-1',
  '?entry=1.5',
  '?entry=2147483648',
])('ignores missing or invalid entry IDs: %s', (search) => {
  expect(readSelectedEntry(search)).toBeNull()
})

test('updates selection while preserving search parameters', () => {
  const search = writeSelectedEntry(
    '?q=school&languages=eng&languages=fre&entry=100',
    1206730,
  )

  const parameters = new URLSearchParams(search)

  expect(parameters.get('q')).toBe('school')
  expect(parameters.getAll('languages')).toEqual(['eng', 'fre'])
  expect(parameters.getAll('entry')).toEqual(['1206730'])
})

test('closing an entry removes only its selection parameter', () => {
  const search = writeSelectedEntry(
    '?q=school&languages=eng&entry=1206730',
    null,
  )

  const parameters = new URLSearchParams(search)

  expect(parameters.has('entry')).toBe(false)
  expect(parameters.get('q')).toBe('school')
  expect(parameters.get('languages')).toBe('eng')
})