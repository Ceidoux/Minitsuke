# Minitsuke frontend

React and TypeScript frontend for the Minitsuke Japanese dictionary.

## Local development

Requires Node.js 24 and npm.

From `apps/web`:

```bash
npm ci
npm run dev
```

Open the local URL printed by Vite, normally http://localhost:5173.

For dictionary searches, PostgreSQL and the FastAPI backend must also be
running, with FastAPI listening at http://127.0.0.1:8000.

During development, Vite forwards `/api` requests to FastAPI.
This proxy does not configure production hosting.

## Search

- Searches automatically after a 200 ms typing pause.
- Supports Japanese spelling, kana, romaji, and meanings in the selected languages through the backend search API.
- Waits for Japanese keyboard composition to finish before searching.
- Loads 30 results at a time, with a Load more button.
- Displays written forms, readings, commonness, grouped definitions,
  parts of speech, and restrictions.
- Cancels outdated requests and supports retrying failed requests.

English definitions are enabled by default. Multiple definition languages
can be selected simultaneously: English, French, German, Dutch, Hungarian,
Russian, Spanish, Slovenian, and Swedish.

Selected languages control translation matching and displayed definitions.
Japanese and romaji searches remain available regardless of the selection.

Each entry groups definitions by language while preserving separate senses
and their restrictions. Changing languages resets pagination and cancels
outdated requests. At least one language must remain selected.

## Search URLs and preferences

Search URLs include the query and selected definition languages, so they
can be bookmarked, shared, and restored after refreshing.

After a 200 ms typing pause, a changed search is added to browser history.
Back and Forward restore the query and language selection. Pausing during
typing can also record a partial query.

Language preferences are saved in this browser when the language checkboxes
change. Explicit languages in a URL override saved preferences without
overwriting them. English is the fallback when no valid preference exists.

Loading a search from a URL starts with the first 30 results; additional
loaded pages are not stored in the URL.

## Checks

```bash
npm run lint
npm run test
npm run build
```

Run tests continuously while editing:

```bash
npm run test:watch
```

Frontend tests simulate API responses and do not require a running
backend or database. GitHub Actions runs lint, tests, and the production
build automatically.