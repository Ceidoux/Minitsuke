import { useState } from 'react'
import type { ConjugationTable } from './dictionary-api'
import ConjugatedText from './ConjugatedText'

type ConjugationSectionProps = {
  tables: ConjugationTable[]
  incomplete: boolean
}

const GROUP_LABELS: Record<string, string> = {
  basic: 'Basic forms',
  potential: 'Potential — ability',
  potential_colloquial: 'Potential — colloquial (ら-dropping)',
  passive: 'Passive',
  causative: 'Causative — make or let',
  causative_passive: 'Causative-passive',
  te_iru: 'ている — ongoing action or resulting state',
}

const FORM_LABELS: Record<string, string> = {
  nonpast: 'Non-past',
  attributive: 'Before a noun',
  adverbial: 'Adverbial form',
  negative: 'Negative',
  past: 'Past',
  negative_past: 'Negative past',
  polite: 'Polite non-past',
  polite_negative: 'Polite negative',
  polite_past: 'Polite past',
  polite_negative_past: 'Polite negative past',
  te: 'て-form',
  negative_te: 'Negative て-form',
  without_doing: 'Without doing — ないで',
  conditional_ba: 'Conditional — ば',
  conditional_ba_alternative: 'Alternative conditional — ば',
  negative_conditional_ba: 'Negative conditional — ば',
  conditional_tara: 'Conditional — たら',
  negative_conditional_tara: 'Negative conditional — たら',
  volitional: 'Volitional',
  polite_volitional: 'Polite volitional',
  imperative: 'Imperative',
  imperative_formal: 'Formal imperative',
  imperative_alternative: 'Alternative imperative',
  prohibitive: 'Prohibitive — do not',
  negative_colloquial: 'Negative — colloquial',
  negative_past_colloquial: 'Negative past — colloquial',
  polite_negative_colloquial: 'Polite negative — contracted',
  polite_negative_alternative: 'Polite negative — alternative',
  polite_negative_colloquial_alternative:
    'Polite negative — contracted alternative',
  polite_negative_past_colloquial: 'Polite negative past — contracted',
  polite_negative_past_alternative: 'Polite negative past — alternative',
  polite_negative_past_colloquial_alternative:
    'Polite negative past — contracted alternative',
  negative_te_colloquial: 'Negative て-form — colloquial',
  conditional_nara: 'Conditional — なら',
  presumptive: 'Presumptive',
  polite_presumptive: 'Polite presumptive',
}

export default function ConjugationSection({
  tables,
  incomplete,
}: ConjugationSectionProps) {
  const [selectedIndex, setSelectedIndex] = useState(0)
  const table = tables[selectedIndex] ?? tables[0]

  if (!table && !incomplete) {
    return null
  }

  return (
    <section
      className="conjugation-section"
      aria-labelledby="conjugation-heading"
    >
      <h3 id="conjugation-heading">Conjugations</h3>

      {incomplete && (
        <p className="entry-note">
          Conjugation coverage is partial. Some forms, grammatical classes,
          or spellings in this entry are not supported yet.
        </p>
      )}

      {table && (
        <>
          {tables.length > 1 ? (
            <label className="conjugation-selector">
              Dictionary form
              <select
                value={selectedIndex}
                onChange={(event) => {
                  setSelectedIndex(Number(event.target.value))
                }}
              >
                {tables.map((item, index) => (
                  <option
                    key={`${item.written}:${item.reading}:${item.verb_class}`}
                    value={index}
                  >
                    {item.written}【{item.reading}】
                  </option>
                ))}
              </select>
            </label>
          ) : (
            <p lang="ja">
              {table.written}【{table.reading}】
            </p>
          )}

          <p className="entry-note">
            Applies to source senses {table.sense_positions.join(', ')}.
            {' '}These are grammatical forms; their use depends on the meaning
            and context.
            {table.verb_class === 'cop' && (
              ' Copula tables include related forms across registers of politeness.'
            )}
            {table.verb_class.startsWith('adj-') && (
              ' Includes forms used before nouns and to modify predicates.'
            )}
            {table.verb_class !== 'cop' &&
              !table.verb_class.startsWith('adj-') && (
                ' Potential and passive forms can be identical.'
              )}
          </p>

          {Object.entries(GROUP_LABELS).map(([group, label]) => {
            const forms = table.forms.filter((item) => item.group === group)

            if (forms.length === 0) {
              return null
            }

            return (
              <details
                className="conjugation-group"
                key={group}
                open={group === 'basic'}
              >
                <summary>{label}</summary>

                <div className="conjugation-table-scroll">
                  <table className="conjugation-table">
                    <caption className="conjugation-caption">
                      {label} of <span lang="ja">{table.written}</span>
                    </caption>
                    <thead>
                      <tr>
                        <th scope="col">Form</th>
                        <th scope="col">Japanese</th>
                        <th scope="col">Reading</th>
                      </tr>
                    </thead>
                    <tbody>
                      {forms.map((item) => (
                        <tr key={item.form}>
                          <th scope="row">
                            {FORM_LABELS[item.form] ?? item.form}
                          </th>
                          <td lang="ja">
                            <ConjugatedText
                              dictionaryForm={table.written}
                              text={item.written}
                              wordClass={table.verb_class}
                            />
                          </td>
                          <td lang="ja">
                            <ConjugatedText
                              dictionaryForm={table.reading}
                              text={item.reading}
                              wordClass={table.verb_class}
                            />
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </details>
            )
          })}
        </>
      )}
    </section>
  )
}