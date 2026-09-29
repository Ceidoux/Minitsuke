import type { DictionaryEntry, DictionarySense } from './dictionary-api'

export const USUALLY_KANA = 'word usually written using kana alone'
export const SEARCH_ONLY_WRITTEN = 'search-only kanji form'
export const SEARCH_ONLY_READING = 'search-only kana form'

export function isUsuallyKana(sense: DictionarySense): boolean {
  return sense.misc?.includes(USUALLY_KANA) ?? false
}

export function getEntryHeading(entry: DictionaryEntry): {
  title: string
  titleWrittenForms: string[]
  alternateWrittenForms: string[]
} {
  const firstSense = entry.senses[0]

  const ordinaryWrittenForms = entry.written_forms.filter(
    (form) =>
      !entry.written_form_info?.[form]?.includes(SEARCH_ONLY_WRITTEN),
  )

  const ordinaryReadings = entry.readings.filter(
    (reading) => !reading.info?.includes(SEARCH_ONLY_READING),
  )

  const preferredReading =
    firstSense &&
    isUsuallyKana(firstSense) &&
    firstSense.restricted_to_written_forms.length === 0
      ? ordinaryReadings.find(
          (reading) =>
            firstSense.restricted_to_readings.length === 0 ||
            firstSense.restricted_to_readings.includes(reading.text),
        )
      : undefined

  if (preferredReading) {
    return {
      title: preferredReading.text,
      titleWrittenForms: [],
      alternateWrittenForms: entry.written_forms.filter(
        (form) => form !== preferredReading.text,
      ),
    }
  }

  if (ordinaryWrittenForms.length > 0) {
    return {
      title: ordinaryWrittenForms.join(' / '),
      titleWrittenForms: ordinaryWrittenForms,
      alternateWrittenForms: entry.written_forms.filter(
        (form) => !ordinaryWrittenForms.includes(form),
      ),
    }
  }

  const ordinaryReading = ordinaryReadings[0]

  if (ordinaryReading) {
    return {
      title: ordinaryReading.text,
      titleWrittenForms: [],
      alternateWrittenForms: entry.written_forms.filter(
        (form) => form !== ordinaryReading.text,
      ),
    }
  }

  // Keep a usable, annotated heading even if every form is search-only.
  return {
    title:
      entry.written_forms.join(' / ') ||
      entry.readings[0]?.text ||
      'Entry',
    titleWrittenForms: [...entry.written_forms],
    alternateWrittenForms: [],
  }
}