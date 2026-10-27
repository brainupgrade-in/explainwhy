# Why does Apple's revenue history under the us-gaap Revenues concept stop at fiscal year 2018?

**Answer.** Apple stopped reporting revenue under the legacy 'Revenues' XBRL concept after fiscal year 2018 because it likely adopted ASC 606 beginning in FY 2019, which requires revenue to be tagged with the 'RevenueFromContractWithCustomerExcludingAssessedTax' concept instead. Consequently, there are zero revenue facts for the 'Revenues' concept for FY 2019 onward, while all post‑2018 revenue facts (117 of them) use the ASC 606 tag and retain valid CIK references.

## Verified claims (critic-checked against query results)
- Apple had 0 revenue facts under the 'Revenues' concept for fiscal years after 2018 (E-6f292e). — evidence: E-6f292e
- For fiscal year 2019 and later Apple reported 117 facts under the concept 'RevenueFromContractWithCustomerExcludingAssessedTax' (E-07af6a). — evidence: E-07af6a
- No revenue facts for Apple after 2018 use any variant of the 'Revenues' concept; only the ASC 606 concept appears (E-5c7052, E-d3de9f). — evidence: E-5c7052, E-d3de9f
- All Apple revenue_fact rows after 2018 have cik values that match a company row, showing no foreign‑key break (E-896ad4). — evidence: E-896ad4

## Inferences (likely causes the data cannot prove; not critic-verified)
- Apple adopted ASC 606 starting in FY2019, requiring revenue to be reported under the 'RevenueFromContractWithCustomerExcludingAssessedTax' concept instead of the legacy 'Revenues' concept. — basis: Claims showing zero Revenues facts after 2018 and exclusive use of the ASC 606 concept thereafter.

## Hypotheses
- `H-e4168e` **supported** — Apple adopted ASC 606 (Revenue from Contracts with Customers) starting FY 2019, so it stopped reporting under the legacy 'Revenues' concept and began using 'RevenueFromContractWithCustomerExcludingAssessedTax' instead. (E-07af6a, E-5c7052, E-6f292e, E-d3de9f)<br>why: Evidence shows cessation of Revenues facts and exclusive adoption of the ASC 606 concept after 2018.
- `H-faefb0` **refuted** — After 2018, Apple's filings for the 'Revenues' concept have period_frame = NULL (duplicate facts) and the edgar.revenue_facts table only retains rows where period_frame IS NOT NULL, causing those later values to be omitted. (E-364390, E-6f292e)<br>why: No Revenues facts exist after 2018, so a period_frame NULL filter cannot explain the absence.
- `H-bec1af` **refuted** — The concept tag for revenues changed after 2018 (e.g., a different namespace or local name), so the stored concept string no longer matches 'Revenues', making those facts invisible when filtering for that exact concept. (E-5c7052, E-d3de9f)<br>why: After 2018 Apple only uses the ASC 606 concept; no altered 'Revenues' string appears.
- `H-e968c5` **refuted** — A reference‑data gap exists: the unified semantic layer's foreign key from revenue_fact to company is broken for Apple after 2018 (e.g., missing or mismatched cik in the company table), so queries that rely on the layer return no rows for later years. (E-896ad4)<br>why: Zero mismatched cik rows prove the foreign key from revenue_fact to company remains intact for Apple after 2018.

## Evidence (Zetaris SQL)
### E-577f84 — Check presence of Apple revenue facts under 'Revenues' concept by fiscal year
Backend: zetaris-rest, 1 row(s)
```sql
SELECT fiscal_year, COUNT(*) AS cnt FROM edgar.revenue_facts WHERE cik = 320193 AND concept = 'Revenues' GROUP BY fiscal_year ORDER BY fiscal_year
LIMIT 200
```
```
fiscal_year | cnt
2018 | 11
```
### E-6f292e — Test whether Apple has any revenue facts under the 'Revenues' concept after fiscal year 2018.
Backend: zetaris-rest, 0 row(s)
```sql
SELECT fiscal_year, COUNT(*) AS cnt FROM edgar.revenue_facts WHERE cik = 320193 AND concept = 'Revenues' AND fiscal_year >= 2019 GROUP BY fiscal_year ORDER BY fiscal_year
LIMIT 200
```
```
fiscal_year | cnt
(0 rows)
```
### E-07af6a — Check which revenue concepts Apple uses for fiscal year 2019 and later to see if it switched to the ASC 606 concept.
Backend: zetaris-rest, 1 row(s)
```sql
SELECT concept, COUNT(*) AS cnt FROM edgar.revenue_facts WHERE cik = 320193 AND fiscal_year >= 2019 GROUP BY concept ORDER BY cnt DESC
LIMIT 200
```
```
concept | cnt
RevenueFromContractWithCustomerExcludingAssessedTax | 117
```
### E-364390 — Check if any Revenues facts exist for Apple after 2018 and whether they have period_frame NULL (testing duplicate/filter hypothesis)
Backend: zetaris-rest, 0 row(s)
```sql
SELECT fiscal_year, period_frame FROM edgar.revenue_facts WHERE cik=320193 AND concept='Revenues' AND fiscal_year>2018 LIMIT 5
```
```
fiscal_year | period_frame
(0 rows)
```
### E-d3de9f — Check if Apple uses any other revenue concept besides the two known after 2018
Backend: zetaris-rest, 1 row(s)
```sql
SELECT DISTINCT concept FROM edgar.revenue_facts WHERE cik = 320193 AND fiscal_year >= 2019 LIMIT 100
```
```
concept
RevenueFromContractWithCustomerExcludingAssessedTax
```
### E-5c7052 — Check if Apple uses any variant of the 'Revenues' concept after 2018 (testing H-bec1af)
Backend: zetaris-rest, 1 row(s)
```sql
SELECT DISTINCT concept FROM edgar.revenue_facts WHERE cik = 320193 AND fiscal_year > 2018 AND concept LIKE '%Revenue%'
LIMIT 200
```
```
concept
RevenueFromContractWithCustomerExcludingAssessedTax
```
### E-896ad4 — Test if any revenue_fact rows for Apple after 2018 have a cik that does not match a company row, indicating a broken foreign key (H-e968c5).
Backend: zetaris-rest, 0 row(s)
```sql
SELECT rf.cik FROM lightning.metastore.explainwhy.explainwhy_usl.revenue_fact rf WHERE rf.cik = '320193' AND rf.fiscal_year > 2018 AND rf.cik NOT IN (SELECT cik FROM lightning.metastore.explainwhy.explainwhy_usl.company)
LIMIT 200
```
```
cik
(0 rows)
```

## Run
- backend `zetaris-rest`, model `nvidia/nemotron-3-super-120b-a12b`, 11 LLM calls, 109.0 s
- Markovian: 8 steps, 4605 prompt tokens vs ~15594 for a full-transcript loop (70.5% saved)
- critic rounds: 1; H-MEM memories written: 4
