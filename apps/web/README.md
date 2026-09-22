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
- Supports Japanese spelling, kana, romaji, and English meanings through
  the backend search API.
- Waits for Japanese keyboard composition to finish before searching.
- Loads 30 results at a time, with a Load more button.
- Displays written forms, readings, commonness, grouped definitions,
  parts of speech, and restrictions.
- Cancels outdated requests and supports retrying failed requests.

English definitions are enabled by default. Language selection is not
yet available in the interface.

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