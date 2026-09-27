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

## JMdict search API

`GET /api/v1/search` searches imported JMdict entries in PostgreSQL.

Supports Japanese written forms, kana readings, romaji (including unfinished syllables), and translations in enabled languages. Matching normalizes kana and character width, and ignores Latin capitalization while preserving original spellings for display.

| Parameter   | Default  | Description                                                             |
| ----------- | -------- | ----------------------------------------------------------------------- |
| `q`         | Required | Search text; surrounding whitespace is removed                          |
| `limit`     | `30`     | Results per page, from 1 to 100                                         |
| `offset`    | `0`      | Number of results to skip; must be nonnegative                          |
| `languages` | `eng`    | Gloss language codes; repeat the parameter to enable multiple languages |

Example requests:

```text
/api/v1/search?q=学校
/api/v1/search?q=tabe
/api/v1/search?q=school&limit=30&offset=30
/api/v1/search?q=école&languages=eng&languages=fre
```

Each result represents one JMdict entry, including its source ID, commonness flag, written forms, readings, senses, glosses, parts of speech, and restrictions.

Results are deduplicated and ranked before pagination. The response includes `query`, `results`, `limit`, `offset`, `has_more`, and nullable `inflection` metadata. When a conjugation is recognized, this metadata identifies matching source IDs and provides per-entry explanations.

Enabled languages control translation matching and returned glosses. Japanese matching remains available regardless of language selection. Senses are preserved even when they have no gloss in an enabled language.

Empty or whitespace-only queries return HTTP 400. Missing queries and invalid pagination parameters return HTTP 422.

Search uses PostgreSQL pg_trgm GIN indexes on gloss text, normalized readings, and normalized written forms, plus a B-tree index on lower(gloss text) for case-insensitive exact matching.

The Alembic migration enables pg_trgm and builds the indexes from existing data; no dictionary reimport is required. Downgrading removes the indexes but retains the shared extension.

On the local dataset of 218,785 entries, median search-service times improved from approximately 97 ms to 21 ms for school, 105 ms to 20 ms for tab, and 22 ms to 8 ms for たべる. Measurements used one warm-up and five measured runs per query, excluding HTTP and JSON serialization.

The four indexes occupied approximately 147 MB. Short, broad Latin queries remain slower. These are local measurements, not concurrent-load guarantees. Search ranking, deduplication, and pagination remain unchanged.

### Ranking

* Kana searches prioritize exact readings, then prefixes, then substrings.
* Written-form searches prioritize exact matches, then substrings.
* Latin input searches written forms, romaji interpretations, and enabled-language glosses together.
* Commonness, definition position, JMdict frequency bands, and stable tie-breakers refine the ordering.

For translation candidates, sense and gloss position take precedence over frequency bands.

Commonness and frequency bands describe the whole entry, not individual senses. Frequency bands come from newspaper data; lower bands receive preference, while missing bands mean unknown. They are not conversational-frequency estimates.

### Frequency data for existing installations

Apply migrations before importing:

```bash
uv run --locked alembic upgrade head
uv run --locked python import_jmdict.py ~/datasets/jmdict/JMdict
```

Run these commands from `apps/api` with `DATABASE_URL` set to the intended database.

New imports populate frequency bands automatically. For an existing dictionary, the frequency-column migration alone leaves bands unknown; reimporting JMdict populates them. 

Reading searches support limited approximate matching: kana queries and
complete romaji queries can suggest reading prefixes differing by one
voicing change, such as だべ → たべ. These suggestions appear after all
genuine matches.

Approximate matching requires at least two kana characters. It does not
handle arbitrary spelling mistakes, missing characters, or multiple
voicing changes.
General typo correction is not implemented; approximate matching currently
covers only one kana voicing change.

### Japanese sentence analysis

Paste Japanese text into the search bar to automatically display clickable word segments. Select a segment to view its ranked dictionary candidates, then select a candidate to open its details.

Analysis supports basic conjugation grouping, preserves the original tokens, and uses grammatical and spelling information to rank candidates. Suggested matches are not guaranteed interpretations; alternatives remain selectable.

Dictionary entries display sense-specific “Usually kana” labels and kana-first headings where appropriate. Kana and romaji searches also use reading order and applicable kana-usage annotations when ranking results.

The analysis API is available at `POST /api/v1/analyze`, accepting a JSON body such as `{"text":"昨日りんごを食べました。"}`. Returned offsets count Unicode code points.

Existing databases must apply the usage-tag migration and populate the new table through a backfill or dictionary reimport.

### Conjugation tables and lookup

Word details include conjugation tables for supported modern verb classes:
Ichidan, regular Godan, the Iku/Yuku exception, regular suru constructions,
and kuru. Tables preserve valid spelling/reading combinations and sense
restrictions.

Forms include basic affirmative, negative, past, and polite forms;
connecting, conditional, volitional, imperative, and prohibitive forms;
and potential, passive, causative, causative-passive, and te-iru groups.
Derived groups include negative, past, and polite variants.
Colloquial potential forms such as 出れる and 来れる are labeled separately.

Search accepts supported inflected forms in Japanese and complete romaji,
including 食べません, dekakerareru, 書ける, and dereru.
Reverse rules are derived from the conjugation generator. Proposed bases
are checked against JMdict, their verb classes, and their generated forms.
Ambiguous interpretations are retained.

Exact ordinary matches precede validated inflection matches, followed by
broader matches. Entries are deduplicated before pagination. Matching cards
show conjugation explanations, and recognized whole-query inflections do
not automatically open the sentence-analysis panel.

The existing Sudachi-based extractor remains a fallback for adjectives
and some constructions outside the verb generator.

Coverage is not exhaustive. Some special and historical verb classes,
contractions, and extended auxiliary combinations remain unsupported.
Generated forms describe grammatical patterns; their use depends on the
entry's meaning and context.

### Dictionary interface

Language preferences are available through the Options button beside
Minitsuke, then Languages. Multiple definition languages can be selected;
at least one must remain enabled.

Search previews show at most four senses with available definitions.
Word details show all available senses and conjugation tables.
Cards display usage badges and grammatical labels together, with compact
spacing and inline alternate spellings.