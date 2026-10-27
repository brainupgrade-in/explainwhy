# Eval results

Backend: zetaris-rest. Model: nvidia/nemotron-3-super-120b-a12b. **5/6 passed.**

A question passes when at least one claim survives the critic and every expected pattern (see `questions.json`) matches a verified claim. Each question ran with an empty memory.

| question | result | verified | dropped | critic rounds | seconds | missing patterns |
|---|---|---|---|---|---|---|
| apple-tag-switch | PASS | 4 | 0 | 1 | 109.0 | - |
| ibm-sic-gap | PASS | 4 | 0 | 3 | 93.7 | - |
| tesla-two-concepts | PASS | 2 | 1 | 3 | 206.5 | - |
| ibm-no-asc606-concept | PASS | 5 | 0 | 2 | 122.6 | - |
| apple-many-rows-2022 | PASS | 3 | 0 | 3 | 175.4 | - |
| tesla-starts-2011 | FAIL | 0 | 0 | 0 | 58.0 | 2011 |

Full results: `evals/runs-zetaris/<id>/`.

**Note on the failure.** `tesla-starts-2011` failed because every query in that run hit a DNS outage on the build
machine (Zetaris could not resolve `data.sec.gov`; see `runs-zetaris/tesla-starts-2011/trace.log`). After the resolver
was restarted and the SEC REST tables were cached in Zetaris (`zetaris/03_cache.sql`), the same question was rerun
once, live: **PASS**, 2 verified claims, 113 s (`runs-zetaris/tesla-starts-2011-rerun/`). We report both; the score
above stays 5/6.
