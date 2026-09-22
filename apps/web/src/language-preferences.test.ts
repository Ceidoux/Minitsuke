import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import {
  LANGUAGE_PREFERENCES_KEY,
  readLanguagePreferences,
  saveLanguagePreferences,
} from './language-preferences'

beforeEach(() => {
  window.localStorage.clear()
})

afterEach(() => {
  vi.restoreAllMocks()
  window.localStorage.clear()
})

test('defaults to English when no preference exists', () => {
  expect(readLanguagePreferences()).toEqual(['eng'])
})

test('saves and restores languages in the standard order', () => {
  saveLanguagePreferences(['fre', 'eng'])

  expect(readLanguagePreferences()).toEqual(['eng', 'fre'])
})

test('removes invalid and duplicate saved values', () => {
  window.localStorage.setItem(
    LANGUAGE_PREFERENCES_KEY,
    JSON.stringify(['fre', 123, null, 'unknown', 'fre', 'eng']),
  )

  expect(readLanguagePreferences()).toEqual(['eng', 'fre'])
})

test.each([
  'not valid JSON',
  'null',
  '{}',
  '"fre"',
  '[]',
  '["unknown"]',
])('falls back to English for unusable stored data: %s', (stored) => {
  window.localStorage.setItem(LANGUAGE_PREFERENCES_KEY, stored)

  expect(readLanguagePreferences()).toEqual(['eng'])
})

test('falls back to English when reading storage is blocked', () => {
  vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
    throw new DOMException('Storage blocked', 'SecurityError')
  })

  expect(readLanguagePreferences()).toEqual(['eng'])
})

test('does not throw when saving storage is blocked', () => {
  vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
    throw new DOMException('Storage blocked', 'SecurityError')
  })

  expect(() => saveLanguagePreferences(['fre'])).not.toThrow()
})