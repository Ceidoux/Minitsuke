import { render, screen } from '@testing-library/react'
import { expect, test } from 'vitest'
import GlossText from './GlossText'

test('preserves the existing display for unqualified glosses', () => {
  render(
    <p>
      <GlossText
        glosses={[
          { text: 'school', language: 'eng' },
          { text: 'academy', language: 'eng' },
        ]}
      />
    </p>,
  )

  expect(screen.getByText('school; academy')).toBeVisible()
})

test('attaches qualifiers only to their individual gloss', () => {
  const { container } = render(
    <p>
      <GlossText
        glosses={[
          { text: 'ordinary meaning', language: 'eng' },
          {
            text: 'literal meaning',
            language: 'eng',
            gloss_type: 'lit',
          },
          {
            text: 'école',
            language: 'fre',
            gender: 'f',
          },
        ]}
      />
    </p>,
  )

  const glosses = container.querySelectorAll('.qualified-gloss')

  expect(glosses[0]).toHaveTextContent('ordinary meaning')
  expect(glosses[0].querySelector('.gloss-qualifier')).toBeNull()
  expect(glosses[1]).toHaveTextContent('(literal) literal meaning')
  expect(glosses[2]).toHaveTextContent('(feminine) école')
})

test('preserves unfamiliar qualifier values', () => {
  render(
    <GlossText
      glosses={[
        {
          text: 'definition',
          language: 'eng',
          gloss_type: 'unfamiliar',
        },
      ]}
    />,
  )

  expect(screen.getByText('(unfamiliar)')).toBeVisible()
})