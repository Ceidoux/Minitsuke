import { Fragment } from 'react'
import type { DictionaryLoanSource } from './dictionary-api'

const SOURCE_LANGUAGES: Record<string, string> = {
  eng: 'English',
  fre: 'French',
  fra: 'French',
  ger: 'German',
  deu: 'German',
  dut: 'Dutch',
  nld: 'Dutch',
  por: 'Portuguese',
  spa: 'Spanish',
  ita: 'Italian',
  rus: 'Russian',
  chi: 'Chinese',
  zho: 'Chinese',
  kor: 'Korean',
  lat: 'Latin',
  gre: 'Greek',
  ell: 'Greek',
  ara: 'Arabic',
  san: 'Sanskrit',
  ain: 'Ainu',
}

type LoanSourcesProps = {
  sources: DictionaryLoanSource[]
}

export default function LoanSources({ sources }: LoanSourcesProps) {
  if (sources.length === 0) {
    return null
  }

  return (
    <p className="entry-note loan-sources" lang="en">
      Origin:{' '}
      {sources.map((source, index) => (
        <Fragment key={index}>
          {index > 0 && '; '}
          <span className="loan-source">
            {SOURCE_LANGUAGES[source.language] ?? source.language}

            {source.text && (
              <>
                {': '}
                <span className="loan-source-text">{source.text}</span>
              </>
            )}

            {source.source_type === 'part' && ' (partial source)'}

            {source.source_type !== 'full' &&
              source.source_type !== 'part' && (
                <> (source type: {source.source_type})</>
              )}

            {source.wasei && ' (Japanese-coined expression)'}
          </span>
        </Fragment>
      ))}
    </p>
  )
}