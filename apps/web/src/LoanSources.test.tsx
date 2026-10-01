import { render, screen } from '@testing-library/react'
import { expect, test } from 'vitest'
import LoanSources from './LoanSources'

test('displays ordered sources and their individual attributes', () => {
  const { container } = render(
    <LoanSources
      sources={[
        {
          text: 'Arbeit',
          language: 'ger',
          source_type: 'full',
          wasei: false,
        },
        {
          text: 'travail',
          language: 'fre',
          source_type: 'part',
          wasei: false,
        },
        {
          text: null,
          language: 'eng',
          source_type: 'full',
          wasei: true,
        },
      ]}
    />,
  )

  const sources = container.querySelectorAll('.loan-source')

  expect(sources).toHaveLength(3)
  expect(sources[0]).toHaveTextContent('German: Arbeit')
  expect(sources[1]).toHaveTextContent('French: travail (partial source)')
  expect(sources[2]).toHaveTextContent(
    'English (Japanese-coined expression)',
  )
  expect(sources[2].querySelector('.loan-source-text')).toBeNull()
})

test('preserves an unfamiliar language code and source type', () => {
  render(
    <LoanSources
      sources={[
        {
          text: null,
          language: 'xyz',
          source_type: 'other',
          wasei: false,
        },
      ]}
    />,
  )

  expect(
    screen.getByText('xyz (source type: other)'),
  ).toBeVisible()
})

test('renders nothing when no origins are available', () => {
  const { container } = render(<LoanSources sources={[]} />)

  expect(container).toBeEmptyDOMElement()
})