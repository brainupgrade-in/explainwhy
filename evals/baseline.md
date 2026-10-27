# Baselines vs the agent

Same 6 questions, same pass rule (expected facts must appear in the answer's claims), same model (`nvidia/nemotron-3-super-120b-a12b`), same local data mirror.

| | passed | what it is |
|---|---|---|
| **ExplainWhy agent** | **5/6** | hypotheses → SQL steps → critic + repair; only critic-verified claims count ([results](results.md)) |
| B2 one-shot text-to-SQL | 4/6 | one query, answer from its rows, no critic |
| B1 Nemotron alone | 5/6 | schema only, no data access |

Per question. In brackets: claims stating a 4+-digit number (year, value, code) that no query result backs, out of all claims. B1 never sees data, so every such number is unbacked.

| question | B1 alone | B2 text-to-SQL |
|---|---|---|
| apple-tag-switch | PASS (3/3) | FAIL (0/2) |
| ibm-sic-gap | FAIL (1/3) | PASS (0/3) |
| tesla-two-concepts | PASS (3/3) | PASS (0/3) |
| ibm-no-asc606-concept | PASS (2/2) | FAIL (0/1) |
| apple-many-rows-2022 | PASS (3/4) | PASS (0/4) |
| tesla-starts-2011 | PASS (2/2) | PASS (0/1) |

The agent's answers contain no unbacked numbers by construction: its critic rejects any claim whose numbers are not in the cited rows. Raw baseline replies: `baseline_runs.json`.

## What the scores hide: an audit against the data

The keyword rule is lenient, so we checked each baseline answer against the data with SQL (queries below run on
the same mirror). Nemotron alone (B1) recalls many real SEC figures correctly — Apple FY2018 revenue
$265,595,000,000 and FY2019 $260,174,000,000, Tesla FY2018 $21,461,268,000 — but it also states
**confident explanations that the data contradicts**:

| question | B1 claim | the data | verdict |
|---|---|---|---|
| ibm-sic-gap | "The sic_code field for IBM … is NULL (or blank)" | `SELECT sic_code FROM edgar.company_profiles WHERE cik=51143` → `3570` | wrong root cause |
| apple-many-rows-2022 | 13 rows = "1 annual 10-K, 4 regular 10-Qs (Q1–Q4) and 8 amended/restated filings" | `… GROUP BY form_type, fiscal_period` → 10-K FY 3, 10-Q Q1 2, Q2 4, Q3 4 (no Q4, no amendments) | wrong, yet **passed** the keyword rule |
| tesla-starts-2011 | "The earliest revenue fact … has fiscal_year = 2011" | true, but the question already says 2011 | restates the question |

B2 (one query) stays within what its query returned, but answers only part of the question: for
apple-tag-switch it shows `Revenues` ends in FY2018 without finding the concept that replaced it; for
ibm-no-asc606-concept it returns a count of 0 with no explanation.

**Reading.** On these six questions the gap is not the keyword score but trust: the agent's answers contain only
claims whose numbers appear in rows it queried, and a critic that sent back unsupported claims; the baselines
give no way to tell their right sentences from their wrong ones. The set is small (6 questions); we report it as
evidence of behaviour, not as a benchmark.
