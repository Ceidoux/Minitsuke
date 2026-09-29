import HighlightedText from './HighlightedText'

type AnnotatedFormProps = {
  text: string
  query?: string
  info?: string[]
}

export default function AnnotatedForm({
  text,
  query = '',
  info = [],
}: AnnotatedFormProps) {
  const labels = Array.from(new Set(info))

  return (
    <span className="annotated-form">
      <span lang="ja">
        <HighlightedText text={text} query={query} />
      </span>

      {labels.length > 0 && (
        <>
          {' '}
          <span className="form-annotation" lang="en">
            ({labels.join(' · ')})
          </span>
        </>
      )}
    </span>
  )
}