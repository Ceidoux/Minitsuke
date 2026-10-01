import { Fragment } from 'react'
import type { DictionaryGloss } from './dictionary-api'

const GLOSS_TYPE_LABELS: Record<string, string> = {
  lit: 'literal',
  fig: 'figurative',
  expl: 'explanation',
  tm: 'trademark',
}

const GENDER_LABELS: Record<string, string> = {
  m: 'masculine',
  f: 'feminine',
  n: 'neuter',
}

type GlossTextProps = {
  glosses: DictionaryGloss[]
}

export default function GlossText({ glosses }: GlossTextProps) {
  const hasQualifiers = glosses.some(
    (gloss) => gloss.gloss_type || gloss.gender,
  )

  if (!hasQualifiers) {
    return <>{glosses.map((gloss) => gloss.text).join('; ')}</>
  }

  return (
    <>
      {glosses.map((gloss, index) => {
        const qualifiers: string[] = []

        if (gloss.gloss_type) {
          qualifiers.push(
            GLOSS_TYPE_LABELS[gloss.gloss_type] ?? gloss.gloss_type,
          )
        }

        if (gloss.gender) {
          qualifiers.push(
            GENDER_LABELS[gloss.gender] ?? gloss.gender,
          )
        }

        return (
          <Fragment key={index}>
            {index > 0 && '; '}
            <span className="qualified-gloss">
              {qualifiers.length > 0 && (
                <span className="gloss-qualifier" lang="en">
                  ({qualifiers.join(', ')}){' '}
                </span>
              )}
              {gloss.text}
            </span>
          </Fragment>
        )
      })}
    </>
  )
}