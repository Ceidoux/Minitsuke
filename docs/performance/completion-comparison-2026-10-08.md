# Conjugation completion comparison — 8 October 2026

Keep deferred normalization and remove the prefix index. Deferred normalization
provides a repeatable improvement with a few lines of code. The additional index
benefit is uncertain in this comparison and retains approximately 7.27 MiB of
allocations per API process.

## Method

The [runner](../../scripts/benchmark_conjugation_completions.py) compares three
implementations in temporary local API processes, using the same populated
PostgreSQL database and read-only transactions:

1. Original: eager normalization and the original reverse-prefix rule scan.
2. Normalization: defer normalization until a real dictionary match, retaining
   the original reverse-prefix rule scan.
3. Indexed: deferred normalization plus the merged prefix index.

All variants use the API sources from merged commit
`2813b475b8b04bbf484f920ce082dc5fcf631365`, except the two modules under comparison.
The original rule scan comes from `e10c00cbc97cb80550edbc57a5375621a3134855`.
Original lookup is derived from the merged lookup by restoring eager
normalization; the search-only lookup fixes remain enabled in all variants.
Uncommitted local edits are excluded from the source snapshots.

Each query receives three warmup requests per implementation, followed by 48
measured rounds. All six implementation orders occur eight times per query;
orders and query order are shuffled with seed `20261008`. Requests are sequential
over persistent loopback HTTP connections, using `limit=30`, `offset=0`, and
`languages=eng`. There are 432 measured requests in total.

HTTP timing includes the full response body. Server CPU timing uses the process
CPU clock around the ASGI request through response creation. No profiler runs
during requests. Index allocations are measured separately after warming the
shared reverse-rule caches, so allocation instrumentation does not affect HTTP
measurements.

Environment: Python 3.14.7, PostgreSQL 17.11, 218,785 dictionary entries, migration
`c0d76f963889`. Detailed platform metadata and every timing sample are in the
[raw results](completion-comparison-2026-10-08.json).

## Results

Median request times, in milliseconds:

| Query | Original HTTP | Normalization HTTP | Indexed HTTP | Original CPU | Normalization CPU | Indexed CPU |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 食べま | 62.4 | 60.3 | 58.6 | 43.7 | 40.4 | 39.7 |
| tabemas | 291.4 | 265.1 | 261.9 | 256.9 | 228.0 | 226.5 |
| takakun | 366.2 | 333.0 | 315.2 | 295.2 | 269.2 | 249.9 |

Paired HTTP savings compare implementations within each measured round.
Positive values mean the newer implementation is faster. The median paired
saving differs from the difference between the two overall medians above.

| Change | Query | Median paired saving | Faster rounds | Exploratory 95% bootstrap interval |
| --- | --- | ---: | ---: | ---: |
| Original → normalization | 食べま | 3.0 ms | 36/48 | 1.6 to 4.8 ms |
| Original → normalization | tabemas | 25.3 ms | 43/48 | 20.1 to 32.2 ms |
| Original → normalization | takakun | 33.5 ms | 43/48 | 27.3 to 39.4 ms |
| Normalization → indexed | 食べま | 2.2 ms | 28/48 | −0.9 to 4.4 ms |
| Normalization → indexed | tabemas | 4.7 ms | 29/48 | −7.1 to 13.4 ms |
| Normalization → indexed | takakun | 13.9 ms | 30/48 | −3.8 to 24.8 ms |

CPU comparisons show the same distinction: the normalization saving is
consistent, while all three intervals for the additional index saving include
zero. The index retains 7,624,036 bytes across 10,646 prefix buckets and 82,842
rule references, with a measured construction peak of 9,295,676 bytes. These are
tracked index allocations, not a measurement of total worker RSS.

These local measurements do not establish production capacity or tail latency.
The bootstrap intervals resample 48 paired rounds; they are exploratory, assume
independent rounds, and do not remove all machine variability. The results
support retaining the simpler normalization improvement. They do not prove that
an index could never be useful under a different workload.

## Resulting implementation and verification

The implementation uses deferred normalization with the original prefix scan.
The overridden duplicate `_reverse_rules()` definition remains removed, and
search-only lookup behavior remains enabled. Existing prefix regressions are
retained; two test names now describe prefix behavior without referring to an
index that is no longer present.

- All three variants returned identical canonical JSON for 12 cases covering the
  three timed queries, exact and complete conjugations, pagination, multilingual
  search, and entry details. Every measured response was checked again.
- 999 backend tests passed against `smartjisho_test`; the existing Starlette/AnyIO
  deprecation was the only warning.
- Backend lint and formatting checks for the changed files passed.
- The benchmark runner passed Ruff lint and formatting checks.
- The user's separate formatting edit in `conjugation.py` was preserved and is
  excluded from this change.

To reproduce the historical comparison from the repository root, with the API
environment installed and `DATABASE_URL` pointing to the populated local
`smartjisho` database:

```bash
apps/api/.venv/bin/python scripts/benchmark_conjugation_completions.py \
  --output /tmp/completion-comparison.json
```

The runner pins both source revisions, stops its own temporary servers on exit,
and does not require another dictionary import.
