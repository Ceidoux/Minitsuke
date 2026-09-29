import { expect, test } from 'vitest'
import type { DictionaryEntry } from './dictionary-api'
import {
  getEntryHeading,
  isUsuallyKana,
  USUALLY_KANA,
  SEARCH_ONLY_READING,
  SEARCH_ONLY_WRITTEN,
} from './entry-presentation'

function makeEntry(): DictionaryEntry {
  return {
    source_id: 1582920,
    is_common: true,
    written_forms: ['此の', '斯の'],
    readings: [
      { text: 'この', no_kanji: false, restricted_to: [] },
      { text: 'こん', no_kanji: true, restricted_to: [] },
    ],
    senses: [
      {
        glosses: [{ text: 'this', language: 'eng' }],
        parts_of_speech: [],
        restricted_to_written_forms: [],
        restricted_to_readings: [],
        misc: [USUALLY_KANA],
      },
    ],
  }
}

test('uses kana as the heading and preserves written alternatives', () => {
  expect(getEntryHeading(makeEntry())).toEqual({
    title: 'この',
    titleWrittenForms: [],
    alternateWrittenForms: ['此の', '斯の'],
  })
})

test('keeps the heading when selected languages hide the first glosses', () => {
  const entry = makeEntry()
  entry.senses[0].glosses = []

  expect(getEntryHeading(entry).title).toBe('この')
})

test('respects a kana-preferred sense restriction to a reading', () => {
  const entry = makeEntry()
  entry.senses[0].restricted_to_readings = ['こん']

  expect(getEntryHeading(entry).title).toBe('こん')
})

test('does not infer an entry heading from a later kana-preferred sense', () => {
  const entry = makeEntry()
  entry.senses.push({
    ...entry.senses[0],
    misc: [USUALLY_KANA],
  })
  entry.senses[0].misc = []

  expect(getEntryHeading(entry).title).toBe('此の / 斯の')
  expect(isUsuallyKana(entry.senses[0])).toBe(false)
  expect(isUsuallyKana(entry.senses[1])).toBe(true)
})

test('does not choose kana when the first sense restricts written forms', () => {
  const entry = makeEntry()
  entry.senses[0].restricted_to_written_forms = ['此の']

  expect(getEntryHeading(entry).title).toBe('此の / 斯の')
})

test('handles entries without usage annotations', () => {
  const entry = makeEntry()
  delete entry.senses[0].misc

  expect(getEntryHeading(entry).title).toBe('此の / 斯の')
  expect(isUsuallyKana(entry.senses[0])).toBe(false)
})

test('moves search-only spellings out of the heading', () => {
  const entry = makeEntry()
  entry.senses[0].misc = []
  entry.written_form_info = {
    此の: [SEARCH_ONLY_WRITTEN],
  }

  expect(getEntryHeading(entry)).toEqual({
    title: '斯の',
    titleWrittenForms: ['斯の'],
    alternateWrittenForms: ['此の'],
  })

  expect(entry.written_forms).toEqual(['此の', '斯の'])
})

test('skips search-only readings when choosing a kana-first heading', () => {
  const entry = makeEntry()
  entry.readings[0].info = [SEARCH_ONLY_READING]

  expect(getEntryHeading(entry).title).toBe('こん')
})

test('does not substitute an incompatible reading for a restricted kana preference', () => {
  const entry = makeEntry()
  entry.senses[0].restricted_to_readings = ['この']
  entry.readings[0].info = [SEARCH_ONLY_READING]

  expect(getEntryHeading(entry)).toEqual({
    title: '此の / 斯の',
    titleWrittenForms: ['此の', '斯の'],
    alternateWrittenForms: [],
  })
})

test('uses an ordinary reading when all spellings are search-only', () => {
  const entry = makeEntry()
  entry.senses[0].misc = []
  entry.written_form_info = {
    此の: [SEARCH_ONLY_WRITTEN],
    斯の: [SEARCH_ONLY_WRITTEN],
  }

  expect(getEntryHeading(entry)).toEqual({
    title: 'この',
    titleWrittenForms: [],
    alternateWrittenForms: ['此の', '斯の'],
  })
})

test('prefers an ordinary reading in a kana-only entry', () => {
  const entry = makeEntry()
  entry.written_forms = []
  entry.senses[0].misc = []
  entry.readings[0].info = [SEARCH_ONLY_READING]

  expect(getEntryHeading(entry)).toEqual({
    title: 'こん',
    titleWrittenForms: [],
    alternateWrittenForms: [],
  })
})

test('retains a heading when every available form is search-only', () => {
  const entry = makeEntry()
  entry.written_forms = []
  entry.readings = [
    {
      text: 'この',
      no_kanji: true,
      restricted_to: [],
      info: [SEARCH_ONLY_READING],
    },
  ]

  expect(getEntryHeading(entry)).toEqual({
    title: 'この',
    titleWrittenForms: [],
    alternateWrittenForms: [],
  })
})