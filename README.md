# ExplainWhy — an agent that explains *why* the data disagrees, with evidence

**Open Agent Hackathon 2026 · Track 2: The Agent That Can Explain Why · team gheware (solo)**

Ask a bounded "why" question about data spread across several sources. ExplainWhy plans competing
hypotheses, tests each one with SQL against **Zetaris**, has a critic check every claim against the rows the
queries returned, sends unsupported claims back for more evidence, and answers with **only the claims that
survived** — each linked to the exact query and rows behind it. Causes the data cannot prove (an accounting
standard change, say) are kept apart as labelled inferences, never mixed in with the facts.

```
$ python -m explainwhy "Why does IBM drop out when EDGAR company profiles are joined to the company_dns SIC reference list?"
...
IBM's EDGAR profile lists sic_code 3570, but the company_dns SIC reference table contains no entry for 3570 or
any zero‑padded variant of that code, so the join fails to find a match and IBM is dropped from the result.
This missing match likely indicates that SIC code 3570 is not present in the reference list, possibly because
it is obsolete or has been removed.
  ✓ IBM's sic_code in edgar.company_profiles is 3570.  [E-c38e8f]
  ✓ The reference table contains zero‑padded sic_code values such as '0111', '0112', '0115', '0116', '0119'.  [E-cbb22d]
  ✓ A search for sic_code '3570' and zero‑padded variants (e.g., '03570') returns zero rows in company_dns.sic_codes_table.  [E-1943cf, E-be1c50]
```

## Why this matters

Analysts and finance teams lose hours to "why don't these numbers line up?" — a series that stops, a join that
silently drops a row, two figures that should match and don't. A plain LLM answers confidently and is often
wrong. ExplainWhy behaves like a careful analyst: it states hypotheses, runs the checks, rules things out, and
refuses to assert what it did not see in the data.

The demo domain is SEC EDGAR financial data across two public sources (SEC XBRL APIs and the company_dns SIC
reference list) — and the disagreements are real, not planted:

| Sample question | What the agent finds (verified) |
|---|---|
| Why does Apple's revenue history under `us-gaap:Revenues` stop at FY2018? | `Revenues` facts end in FY2018; facts under the ASC 606 concept `RevenueFromContractWithCustomerExcludingAssessedTax` run from FY2019 on. ASC 606 adoption is reported as a *likely* cause (inference), not a fact. |
| Why does IBM drop out when company profiles are joined to the SIC reference list? | IBM's SIC code 3570 is absent from the 1,005-code reference list, so the inner join drops it. |
| Why does Tesla report revenue under two XBRL concepts? | Only `Revenues` in FY2011–2017; from FY2018 both concepts appear in the same filings, sometimes with identical values (duplicate tagging), sometimes not. |

Full reports, traces and event logs for each: [`samples/outputs/`](samples/outputs/).

## How it works

```
question
  │  H-MEM recall: prior verified findings (with source + confidence), injected as "re-check before relying"
  ▼
planner (Nemotron) ──► 3–5 competing hypotheses (≥1 data-artifact, ≥1 real-world)      → World Model events
  ▼
investigator (Nemotron), one bounded Markovian step at a time:
  prompt = goal + COMPLETED/REMAINING/DECISIONS/CONTEXT carryover + latest result     (never the full transcript)
  [NEEDS_TOOL] → read-only SQL guard → Zetaris → rows recorded as evidence E-xxxxxx    → World Model events
  [TASK_COMPLETE] → answer + claims citing evidence ids + a verdict for every hypothesis
  ▼
critic
  deterministic: every claim cites recorded evidence · every 4+-digit number/year appears in the cited rows or SQL
                 · a zero result from a multi-condition filter whose value matches nothing proves nothing
  LLM review (Nemotron): do the cited rows (only those) show the claim?  supported / partial / unsupported
  ▼ unsupported or partial → feedback to investigator, repair round (max 2)
writer (Nemotron): final 2–4 sentence answer from verified claims only; numbers checked against them
answer: verified claims · dropped claims with reasons · labelled inferences · hypothesis verdicts
  ▼
H-MEM write: verified claims stored with source = evidence ids, SQL refs, provenance; audit ledger entry
```

Safeguards required by the rules: whole-run deadline (`RUN_DEADLINE_S`, default 480 s), per-call timeouts,
capped LLM retries (2) and capped repair rounds (2), step budget with a forced final step, read-only SQL guard
(single SELECT/WITH, no write/admin keywords, row cap), repeated queries refused.

Sample runs: 3–9 Markovian steps, 7–13 model calls, 47–71 s each. The bounded prompts sent 1.4–5.3k
prompt tokens per run versus an estimated 2.4–19.5k for a loop that re-sends the whole transcript (42–73 %
less, growing with run length; see `markovian` in each `result.json`).

## Sponsor technology

| Sponsor | How it is used | Where |
|---|---|---|
| **Zetaris** | The data harness. All evidence is Lightning SQL run through the Zetaris REST API (`POST /sql-editor/sqls/run`) against three views over live REST sources: `edgar.revenue_facts` (SEC XBRL, 5 REST tables unioned), `edgar.company_profiles` (SEC submissions), `company_dns.sic_codes_table` (getting-started recipe 12). Questions are answered by joining across sources inside Zetaris. | `zetaris/01_create.sql`, `explainwhy/data.py` (`ZetarisSource`) |
| **Meterless** | Minimal Python implementations of three Meterless engine specs (github.com/Meterless/Meterless, Apache-2.0): **World Model** — event-sourced investigation state (append-only log, stable content IDs, idempotent ingest, version check), which is also the trace; **H-MEM** — file-based memory with mandatory source + provenance, the spec's hybrid retrieval score, supersede-don't-delete, feedback deltas, audit ledger; **Markovian** — bounded steps with the canonical carryover block and `[NEEDS_TOOL]`/`[STATE_CHECKPOINT]`/`[TASK_COMPLETE]` markers, plus token-savings stats. | `explainwhy/engines/` |
| **NVIDIA** | Every role (planner, investigator, critic) runs on **NVIDIA Nemotron** — `nvidia/nemotron-3-super-120b-a12b` via an OpenAI-compatible endpoint (Nebius Token Factory). | `explainwhy/llm.py` |
| **Cursor** | Not used for this build: HackOS's Cursor access instructions were still "TBC" on 27 Oct; the code was written with Claude Code (allowed by the AI Usage Policy). See "Development". | — |

## Setup and usage

Requirements: Python 3.11+. No third-party packages at runtime (standard library only); `pytest` for tests.

```bash
git clone https://github.com/brainupgrade-in/explainwhy.git && cd explainwhy
cp .env.example .env            # add LLM_* (and ZETARIS_* for live Zetaris)

# 1. Offline, no keys: replays the three recorded sample runs on the local data mirror
SAMPLE_MODE=true python -m explainwhy --sample 1      # or 2, 3

# 2. Live Nemotron, local data mirror
python -m explainwhy "Why does Tesla report revenue under two different XBRL concepts?"

# 3. Live Nemotron + live Zetaris (falls back to the local mirror, and says so, if Zetaris is unreachable)
python -m explainwhy --zetaris --sample 2

# tests (offline, scripted model)
python -m pytest -q
```

Each run writes `runs/<id>/report.md` (answer, verified/dropped claims, hypotheses, every query with its
rows), `result.json`, `events.jsonl` (World Model event log = full agent trace) and `trace.log`.
H-MEM memory persists in `memory/` across runs.

**Zetaris setup.** Install Zetaris locally (Docker) per the
[getting-started guide](https://github.com/zetaris/getting-started), onboard the SIC list
(`python3 scripts/onboard.py run company_dns` in that repo), then run our script with its runner:
`python3 scripts/run_sql.py <path>/zetaris/01_create.sql --dry-run`, then without `--dry-run`. Put
`ZETARIS_REST_URL`, `ZETARIS_ORG_ID`, `ZETARIS_API_KEY` in `.env`.

**SAMPLE_MODE** = local SQLite mirror of the three Zetaris views (`data/`, same table names and columns) +
recorded Nemotron replies (`samples/llm_cache/`, keyed by request hash). It replays the three sample
questions exactly; other questions need the live model.

## Development

Built on 27 Oct 2026 (inside the build window) with **Claude Code** as the coding agent, which the Zetaris
getting-started repo supports alongside Cursor and Codex. The hackathon's Cursor access steps were never
published (the HackOS Cursor folder still read "TBC" on 27 Oct), so no Cursor-specific work is claimed.

**Pre-existing components: none.** All code in this repository was written during the build window. Used
as references only (not copied): the Meterless engine specs (`AGENTS.md` per engine, Apache-2.0) and the
Zetaris getting-started SQL recipes (Apache-2.0), whose REST-table pattern `zetaris/01_create.sql` follows.

## Limitations (honest)

- The live Zetaris path (`--zetaris`) is implemented against the documented REST API, but the recorded
  sample runs used the local mirror of the same views (see `backend` in each `result.json`).
- The critic is strict on numbers and citations but can still accept a weak inference phrased as a fact
  (e.g. in sample 3 it accepted "different values, so not duplicate tagging" based on yearly sums that
  include restated facts).
- The writer is told to hedge causes the data cannot show, and new numbers are rejected deterministically, but
  wording can still lean too hard on an inference (sample 3's summary says "after adopting ASC 606").
- Three companies and two revenue concepts: a small, bounded world by design (Track 2).

## Layout

```
explainwhy/   agent.py (planner/investigator/critic loop) · data.py (Zetaris + local harness, SQL guard)
              llm.py (Nemotron client, record/replay) · engines/ (world_model, hmem, markovian) · __main__.py (CLI)
zetaris/      01_create.sql — Zetaris REST tables + views the agent queries
data/         public snapshots for SAMPLE_MODE (see data/README.md)
samples/      outputs/sample{1,2,3}/ (report, result, events, trace) · llm_cache/ (recorded replies)
scripts/      fetch_sample_data.py
tests/        offline tests with a scripted model
```

License: MIT.
