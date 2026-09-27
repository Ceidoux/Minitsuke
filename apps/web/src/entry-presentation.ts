import type { DictionaryEntry, DictionarySense } from './dictionary-api'

export const USUALLY_KANA = 'word usually written using kana alone'

export function isUsuallyKana(sense: DictionarySense): boolean {
  return sense.misc?.includes(USUALLY_KANA) ?? false
}

export function getEntryHeading(entry: DictionaryEntry): {
  title: string
  alternateWrittenForms: string[]
} {
  const firstSense = entry.senses[0]

  const preferredReading =
    firstSense &&
    isUsuallyKana(firstSense) &&
    firstSense.restricted_to_written_forms.length === 0
      ? entry.readings.find(
          (reading) =>
            firstSense.restricted_to_readings.length === 0 ||
            firstSense.restricted_to_readings.includes(reading.text),
        )
      : undefined

  if (preferredReading) {
    return {
      title: preferredReading.text,
      alternateWrittenForms: entry.written_forms.filter(
        (form) => form !== preferredReading.text,
      ),
    }
  }

  return {
    title:
      entry.written_forms.join(' / ') ||
      entry.readings[0]?.text ||
      'Entry',
    alternateWrittenForms: [],
  }
}