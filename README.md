# Minitsuke
Japanese Kanji Search Engine: Application allowing to search up Kanji, displaying info about it and the most common Japanese words using it based on daily world frequency, and using LLM Based definition and translation + exporting Anki card to boost productivity

**Why**

I wanted to create something useful to aid my Japanese learning adventure with Anki. Most current japanese dictionnaries don't use a frequency-based word list, and LLMs used for language are usually very accurate in describing how certain words are used in real life. Combining these two things + anki export option will make for a much more enjoyable and productive japanese learning experience !


First Milestone -> Display a Kanji retrieved through FastAPI.

Workflow -> Trunk-based development, using short-lived branches merged into main through pull requests, aswell as feature flags when needed. CI will also be configured and used.


## Local database

Prerequisites: Docker Desktop with WSL integration enabled.

Run these commands from the repository root.

Start PostgreSQL:

```bash
docker compose -f infra/compose.yaml up -d --wait
```

Open the SQL terminal:

```bash
docker compose -f infra/compose.yaml exec db psql -U smartjisho -d smartjisho
```

Exit the SQL terminal with `\q`.

Stop PostgreSQL:

```bash
docker compose -f infra/compose.yaml stop
```

Remove the PostgreSQL container (preserves the Volume)

```bash
docker compose -f infra/compose.yaml down
```

Database data persists in a named Docker volume.
The credentials in the Compose file are for local development only.

Apply database migrations after starting PostgreSQL.

From `apps/api`:

```bash
uv sync
uv run alembic upgrade head
```

Check the current migration revision:

```bash
uv run alembic current
```


## Run the API

Start PostgreSQL using the instructions above.

From `apps/api`:

```bash
uv sync --locked --dev
export DATABASE_URL='postgresql+psycopg://smartjisho:local_dev_only@127.0.0.1:5432/smartjisho'
uv run alembic upgrade head
uv run fastapi dev main.py
```

Open http://127.0.0.1:8000/docs to try the API.

Search reads vocabulary from PostgreSQL. A newly migrated database
contains no vocabulary, so searches return empty results until data
is inserted.

## Run tests

Tests use a separate PostgreSQL database.

With PostgreSQL running, create the test database once from the
repository root:

```bash
docker compose -f infra/compose.yaml exec db createdb -U smartjisho smartjisho_test
```

From `apps/api`:

```bash
export DATABASE_URL='postgresql+psycopg://smartjisho:local_dev_only@127.0.0.1:5432/smartjisho'
export TEST_DATABASE_URL='postgresql+psycopg://smartjisho:local_dev_only@127.0.0.1:5432/smartjisho_test'
DATABASE_URL="$TEST_DATABASE_URL" uv run alembic upgrade head
uv run pytest
```

The fixtures insert known vocabulary and roll back each test's changes.
Environment variables must be set again when opening a new terminal.


## Import JMdict

The file imported must be uncompressed XML, and migrations must already be applied
To import JMdict,the command must be run from 'apps/api' directory.
DATABASE_URL selects the target db.
The whole import uses one transaction; progress remains uncommitted until completion.
Re-importing updates matching source IDs; it doesn’t remove entries absent from the file.

Here's the command:

```bash
uv run --locked python import_jmdict.py ~/datasets/jmdict/JMdict
```

Note: search API still uses the original vocabulary tables for now