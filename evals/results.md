# Eval results

Backend: local-sqlite (SAMPLE_MODE mirror of the Zetaris views). Model: nvidia/nemotron-3-super-120b-a12b. **5/6 passed.**

A question passes when at least one claim survives the critic and every expected pattern (see `questions.json`) matches a verified claim. Each question ran with an empty memory.

| question | result | verified | dropped | critic rounds | seconds | missing patterns |
|---|---|---|---|---|---|---|
| apple-tag-switch | PASS | 3 | 1 | 3 | 85.6 | - |
| ibm-sic-gap | PASS | 4 | 0 | 1 | 58.4 | - |
| tesla-two-concepts | FAIL | 1 | 1 | 3 | 107.7 | 2018 |
| ibm-no-asc606-concept | PASS | 7 | 0 | 1 | 57.5 | - |
| apple-many-rows-2022 | PASS | 3 | 0 | 1 | 41.8 | - |
| tesla-starts-2011 | PASS | 1 | 2 | 3 | 58.9 | - |

Full results: `evals/runs/<id>.json`.
