# SmartJisho
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

Database data persists in a named Docker volume.
The credentials in the Compose file are for local development only.