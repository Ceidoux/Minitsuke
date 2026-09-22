export function readSelectedEntry(search: string): number | null {
  const value = new URLSearchParams(search).get('entry')

  if (value === null || !/^[0-9]+$/.test(value)) {
    return null
  }

  const sourceId = Number(value)

  return Number.isInteger(sourceId) &&
    sourceId >= 1 &&
    sourceId <= 2_147_483_647
    ? sourceId
    : null
}

export function writeSelectedEntry(
  search: string,
  sourceId: number | null,
): string {
  const parameters = new URLSearchParams(search)

  parameters.delete('entry')

  if (sourceId !== null) {
    parameters.set('entry', String(sourceId))
  }

  const encoded = parameters.toString()
  return encoded === '' ? '' : `?${encoded}`
}