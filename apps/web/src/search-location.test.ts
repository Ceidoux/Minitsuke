import { expect, test } from 'vitest'
import {
  normalizeLanguages,
  readSearchLocation,
  writeSearchLocation,
} from './search-location'

test('uses preferences when the URL does not specify languages', () => {
  expect(readSearchLocation('?q=school', ['fre'])).toEqual({
    query: 'school',
    languages: ['fre'],
  })
})

test('explicit URL languages override saved preferences', () => {
  expect(
    readSearchLocation(
      '?q=school&languages=fre&languages=eng',
      ['ger'],
    ),
  ).toEqual({
    query: 'school',
    languages: ['eng', 'fre'],
  })
})

test('deduplicates languages and removes unsupported codes', () => {
  expect(
    normalizeLanguages(['fre', 'unknown', 'eng', 'fre']),
  ).toEqual(['eng', 'fre'])
})

test('invalid explicit languages fall back to English', () => {
  expect(
    readSearchLocation('?languages=unknown', ['fre']).languages,
  ).toEqual(['eng'])

  expect(
    readSearchLocation('?languages=', ['fre']).languages,
  ).toEqual(['eng'])
})

test('round-trips Japanese and special characters safely', () => {
  const state = {
    query: '学校 & ?認',
    languages: normalizeLanguages(['fre', 'eng']),
  }

  expect(readSearchLocation(writeSearchLocation(state))).toEqual(state)
})

test('removes a blank query while preserving unrelated parameters', () => {
  const search = writeSearchLocation(
    { query: '   ', languages: ['fre'] },
    '?q=old&languages=eng&view=compact',
  )

  const parameters = new URLSearchParams(search)

  expect(parameters.has('q')).toBe(false)
  expect(parameters.getAll('languages')).toEqual(['fre'])
  expect(parameters.get('view')).toBe('compact')
})