export const DICTIONARY_LANGUAGES = [
  { code: 'eng', label: 'English', htmlLang: 'en' },
  { code: 'fre', label: 'Français', htmlLang: 'fr' },
  { code: 'ger', label: 'Deutsch', htmlLang: 'de' },
  { code: 'dut', label: 'Nederlands', htmlLang: 'nl' },
  { code: 'hun', label: 'Magyar', htmlLang: 'hu' },
  { code: 'rus', label: 'Русский', htmlLang: 'ru' },
  { code: 'spa', label: 'Español', htmlLang: 'es' },
  { code: 'slv', label: 'Slovenščina', htmlLang: 'sl' },
  { code: 'swe', label: 'Svenska', htmlLang: 'sv' },
] as const

export type DictionaryLanguageCode =
  (typeof DICTIONARY_LANGUAGES)[number]['code']