# Zetaris in ExplainWhy

How ExplainWhy uses Zetaris, set out against the Zetaris evaluation criteria (Build a USL · Reflect on the USL).

## 1. Build a Unified Semantic Layer

### 1a. Use case and data sources

**Use case.** An analyst asks a bounded "why" question about financial data that disagrees across systems
("Why does Apple's revenue history stop at FY2018?", "Why does IBM drop out of the SIC join?"). ExplainWhy
answers with claims that a critic has checked against query results. Zetaris is where every query runs.

**Three sources, all live REST, registered in Zetaris:**

| # | Source | Zetaris objects | Created by |
|---|---|---|---|
| 1 | SEC EDGAR XBRL companyconcept API — revenue facts, 2 concepts × 3 companies | `sec_data.xw_*_facts` (5 REST tables) → view `edgar.revenue_facts` | `zetaris/01_create.sql` |
| 2 | SEC EDGAR submissions API — company profile incl. SIC code | `sec_data.xw_*_submissions` (3 REST tables) → view `edgar.company_profiles` | `zetaris/01_create.sql` |
| 3 | company_dns SIC reference list (1,005 codes) | `company_dns.sic_codes_raw` → `company_dns.sic_codes_table` | getting-started recipe 12 (`onboard.py run company_dns`) |

### 1b. Onboarding and exploratory queries

All three sources are registered in a local Zetaris instance (Docker, `zetaris-platform` 2.4.3) and were
queried live through the REST API on 27–28 Oct 2026. Full queries and outputs: [`zetaris/live_results.md`](zetaris/live_results.md)
(produced by `zetaris/showcase.py`). Highlights:

| Source | Exploratory query (live) | Result |
|---|---|---|
| SEC XBRL facts | facts per concept | `Revenues` 532 facts (FY2009–2026); ASC 606 concept 166 facts (FY2018–2026) |
| SEC XBRL facts | last fiscal year per company and concept | Apple `Revenues` ends FY2018 (11 facts) while its ASC 606 concept runs to FY2026 (117) |
| SEC XBRL facts | facts per form type | 10-Q 458 · 10-K 226 · 10-K/A 11 · 8-K 3 |
| SEC submissions | profiles | Apple 3571, IBM 3570, Tesla 3711 |
| SEC submissions | companies per SIC code | one company per code |
| company_dns | size and range | 1,005 codes, `0111`–`9999` |
| company_dns | codes 3570–3579 | 3571, 3572, 3575, 3577, … — **no 3570** |

Exploring also surfaced a disagreement we had not planted or noticed offline: the XBRL source names IBM
"INTERNATIONAL BUSINESS MACHINES CORPORATION", the submissions source "INTERNATIONAL BUSINESS MACHINES CORP" —
a reason to join on CIK, never on names (which is what our agent's catalog tells it to do).

Row counts match the independent SAMPLE_MODE snapshot exactly (698 facts, 3 profiles, 1,005 codes).

### 1c. The USL and its quality state

`explainwhy_usl` (namespace `lightning.metastore.explainwhy`) puts all three sources in one model:

```
sic_code (PK sic_code)  <──FK──  company (PK cik, FK sic)  <──FK──  revenue_fact (PK fact_id, FK cik)
   company_dns                      SEC submissions                    SEC XBRL facts
```

DDL: [`zetaris/02_usl.sql`](zetaris/02_usl.sql). The primary- and foreign-key constraints generate the data
quality rules; `RUN DQ` executes them.

**Queries showing the USL is active** (live, `zetaris/live_results.md`):

| Query | Result |
|---|---|
| `SELECT COUNT(*) FROM …explainwhy_usl.sic_code` | 1,005 |
| company ⟕ sic_code | Apple → Electronic Computers · Tesla → Motor Vehicles and Passenger Car Bodies · **IBM → (no match)** |
| revenue_fact ⋈ company, per concept | Apple `Revenues` 11 facts to FY2018 · Apple ASC 606 117 to FY2026 · IBM 235 · Tesla 286 + 49 |

**Data quality rule executed.** `RUN DQ TABLE …company` and `RUN DQ TABLE …revenue_fact` ran in `02_usl.sql`.
`SHOW DQ ALL INVALID TABLE …explainwhy_usl.company` returns exactly one invalid record:

```
{"cik":"51143","entity_name":"INTERNATIONAL BUSINESS MACHINES CORP","sic":"3570", ...}
```

— the FK rule `company.sic → sic_code.sic_code` catching IBM's missing SIC code. `SHOW DQ ALL INVALID TABLE
…revenue_fact` returns 0 rows: every fact's CIK resolves and every fact_id is unique. **Zetaris's own rule engine
and our agent reach the same answer by independent routes**: the agent by querying and ruling out whitespace,
NULLs, padding and duplicates (sample 2, and the live run in `samples/outputs/zetaris-live-ibm/`), Zetaris by the
constraint declared once in the USL DDL.

**The agent on live Zetaris.** `python -m explainwhy --zetaris --sample 2` ran against this instance: 4 Lightning
SQL queries over REST, 4 critic-verified claims, 85 s ([report](samples/outputs/zetaris-live-ibm/report.md)).

**What did not work (yet).** Asked directly "which companies break the semantic layer's data-quality rules?",
the agent did not rely on `SHOW DQ` and instead re-derived its own rules (e.g. counted repeated periods across
filings as "duplicates", which the USL's real key does not treat as violations). The USL's DQ output was right;
the agent's reading of the question was not. That is the motivation for the requirement in 2c.

## 2. Reflect on the USL

### 2a. Time saved versus a hand-coded approach (with the hand-coded part built)

We built both, because SAMPLE_MODE needs an offline copy of the same three sources:

| | Hand-coded (our SAMPLE_MODE mirror) | Zetaris |
|---|---|---|
| Getting the data | `scripts/fetch_sample_data.py`, 70 lines: HTTP, User-Agent, rate limit, JSON flattening per endpoint | `CREATE LIGHTNING REST TABLE` + `LATERAL VIEW explode(...)` per source (`01_create.sql`) |
| Making it queryable | `LocalSource`, ~30 lines: SQLite schemas, type coercion, CSV load | Views exist as soon as the REST tables do |
| Freshness | A snapshot: stale the day after it is fetched | Every query reads the live API (or its cache) |
| Relationships | None. The SIC join and its gap are re-discovered by every query that needs them | Declared once as FKs in the USL |
| Data quality | Hand-written: our critic's "vacuous filter" check and the agent's own join probes (~25 lines plus model calls) | `RUN DQ` on FK/PK rules generated from the DDL; invalid rows listed by `SHOW DQ ALL INVALID` |

Estimate for this project: the hand-coded path took about 1.5 hours to write and debug for 3 companies; the
Zetaris path about 1 hour, most of it learning Lightning SQL (one activation failed until NOT NULL columns were
wrapped in COALESCE; Zetaris's error message suggested the exact fix). The gap widens with scale: adding a fourth company
is one REST table and one `UNION ALL` line in Zetaris, versus re-fetching, re-snapshotting and re-validating by
hand. The bigger saving is not lines but *questions you no longer have to ask*: the USL's FK rule names IBM's
missing SIC code before anyone looks.

### 2b. How the USL helps (or not) in this kind of work

- **Helps:** an "explain why" agent spends most of its steps ruling out boring causes (whitespace, NULLs,
  padding, duplicates) before it reaches the real one. A USL with constraints answers several of those up front:
  the PK rule says there are no duplicates, the FK rule names the orphaned rows. Fewer agent steps, fewer model
  calls, and the agent can cite a Zetaris DQ result as independent evidence.
- **Helps:** one model over three systems means the agent queries business entities (company, sic_code,
  revenue_fact), not raw REST payloads with source-specific shapes.
- **Does not help (yet):** the agent still needs a written description of the tables to plan queries. We wrote
  ours by hand (`CATALOG` in `explainwhy/data.py`). The USL holds most of that information but not in a form an
  agent can fetch.
- **A project that would benefit:** month-end revenue reconciliation across an ERP, a billing system and a CRM.
  Today an analyst spends 1–2 days per close chasing mismatches; a USL with FK and value rules plus an agent like
  ExplainWhy could produce the first-pass explanation of every break in under an hour.

### 2c. A requirement for Zetaris (written as a PM)

**Make the USL agent-readable.** *As an engineer building an AI agent on Zetaris, I want one call that returns a
USL's tables, columns, descriptions, keys and the latest DQ results as JSON, so the agent can plan queries and
cite quality findings without a hand-written schema.*

- `GET /usl/{namespace}/{usl}/catalog` → tables, columns (type, description), PK/FK graph, row counts.
- `GET /usl/{namespace}/{usl}/dq` → per rule: rule id, table, total / valid / invalid, and the invalid keys.
- The same as SQL: `SELECT * FROM lightning.dq_results WHERE usl = '...'`, so a read-only agent can query it.
- Acceptance: an agent given only the catalog JSON writes correct joins across the three tables in this project
  on the first try, and quotes the FK rule's invalid row (IBM, 3570) as evidence.

Mock of the response we would want (`zetaris/usl_catalog_mock.json` shows the full shape):

```json
{"usl": "explainwhy_usl", "tables": [{"name": "company", "description": "One row per company ...",
  "primary_key": ["cik"], "foreign_keys": [{"column": "sic", "references": "sic_code.sic_code"}],
  "dq": {"rules": [{"id": "fk_company_sic", "total": 3, "valid": 2, "invalid": 1,
                    "invalid_keys": [{"cik": "51143", "sic": "3570"}]}]}}]}
```
