# Why does Apple have 13 revenue rows for fiscal year 2022 instead of one?

**Answer.** Apple’s FY2022 revenue appears in 13 separate rows because each filing—ten quarterly 10‑Qs and three annual 10‑Ks—contains its own revenue figure for the period it covers. The quarterly 10‑Qs report cumulative year‑to‑date totals, so each successive quarter adds another row that overlaps with prior quarters, leading to multiple rows for the same fiscal year rather than a single summed amount.

## Verified claims (critic-checked against query results)
- Apple FY2022 revenue rows total 13, all using the concept RevenueFromContractWithCustomerExcludingAssessedTax. — evidence: E-038ee2
- Of those 13 rows, 10 are from 10‑Q filings and 3 are from 10‑K filings. — evidence: E-db2094
- Each distinct fiscal period in the FY2022 revenue rows has exactly one accession number (no duplicate filings for the same period). — evidence: E-0a1c48

## Inferences (likely causes the data cannot prove; not critic-verified)
- The quarterly 10‑Q filings report cumulative year‑to‑date revenue, causing overlapping periods (e.g., Q1, Q2‑YTD, Q3‑YTD) and thus multiple rows for the same fiscal year. — basis: Claims show 10 quarterly rows and 3 annual rows; knowledge of 10‑Q reporting explains why quarters produce YTD figures.

## Hypotheses
- `H-23bf9a` **refuted** — Apple submits multiple filings (original 10-Qs, 10-K, and subsequent amendments/restatements) for FY2022, each filing contains a revenue fact, resulting in duplicate rows for the same fiscal period. (E-0d779b)<br>why: No fiscal period has more than one accession number, so there are no duplicate filings for the same period.
- `H-1418d9` **refuted** — Two different XBRL concepts are used for revenue: 'Revenues' and 'RevenueFromContractWithCustomerExcludingAssessedTax'. Both concepts are reported in each filing, effectively doubling the number of rows per filing. (E-038ee2, E-b4663b)<br>why: The 'Revenues' concept does not appear for Apple FY2022, so two concepts are not responsible for the row count.
- `H-6472ba` **refuted** — Apple reports revenue for each quarterly filing (10-Q) and the annual filing (10-K) for FY2022, giving four quarterly rows plus one annual row per concept, and when combined with amendments yields the observed count. (E-0d779b, E-db2094)<br>why: While there are 4 quarterly filings plus 1 annual filing per concept, the actual count is 10 quarterly and 3 annual rows due to year‑to‑date reporting, not simple quarterly + annual.
- `H-54ac2e` **refuted** — Revenue facts are tagged with dimensional information (e.g., geographic region or product segment) in the XBRL instance, causing a separate row for each dimension combination within the same filing; this reflects Apple's multi‑segment business rather than a data error. (E-16ee26, E-db2094)<br>why: Only one XBRL concept appears; no dimensional segmentation creates extra rows.

## Evidence (Zetaris SQL)
### E-d47573 — See how revenue rows are distributed by concept, filing type, period, and accession to identify duplicates or multiple concepts/filings.
Backend: zetaris-rest, 13 row(s)
```sql
SELECT concept, form_type, period_start, period_end, accession_number, COUNT(*) AS dup_count FROM edgar.revenue_facts WHERE cik = 320193 AND fiscal_year = 2022 AND concept IN ('Revenues','RevenueFromContractWithCustomerExcludingAssessedTax') GROUP BY concept, form_type, period_start, period_end, accession_number ORDER BY dup_count DESC LIMIT 20
```
```
concept | form_type | period_start | period_end | accession_number | dup_count
RevenueFromContractWithCustomerExcludingAssessedTax | 10-Q | 2020-09-27 | 2021-03-27 | 0000320193-22-000059 | 1
RevenueFromContractWithCustomerExcludingAssessedTax | 10-Q | 2021-09-26 | 2022-06-25 | 0000320193-22-000070 | 1
RevenueFromContractWithCustomerExcludingAssessedTax | 10-K | 2020-09-27 | 2021-09-25 | 0000320193-22-000108 | 1
RevenueFromContractWithCustomerExcludingAssessedTax | 10-K | 2021-09-26 | 2022-09-24 | 0000320193-22-000108 | 1
RevenueFromContractWithCustomerExcludingAssessedTax | 10-Q | 2021-03-28 | 2021-06-26 | 0000320193-22-000070 | 1
RevenueFromContractWithCustomerExcludingAssessedTax | 10-Q | 2020-12-27 | 2021-03-27 | 0000320193-22-000059 | 1
RevenueFromContractWithCustomerExcludingAssessedTax | 10-Q | 2022-03-27 | 2022-06-25 | 0000320193-22-000070 | 1
RevenueFromContractWithCustomerExcludingAssessedTax | 10-Q | 2020-09-27 | 2020-12-26 | 0000320193-22-000007 | 1
RevenueFromContractWithCustomerExcludingAssessedTax | 10-Q | 2021-12-26 | 2022-03-26 | 0000320193-22-000059 | 1
RevenueFromContractWithCustomerExcludingAssessedTax | 10-Q | 2021-09-26 | 2022-03-26 | 0000320193-22-000059 | 1
RevenueFromContractWithCustomerExcludingAssessedTax | 10-K | 2019-09-29 | 2020-09-26 | 0000320193-22-000108 | 1
RevenueFromContractWithCustomerExcludingAssessedTax | 10-Q | 2021-09-26 | 2021-12-25 | 0000320193-22-000007 | 1
... (1 more rows, 13 total)
```
### E-db2094 — Check distribution of revenue rows by concept and filing type for Apple FY2022 to see if both concepts appear and how many rows per filing type.
Backend: zetaris-rest, 2 row(s)
```sql
SELECT concept, form_type, COUNT(*) AS row_count FROM edgar.revenue_facts WHERE cik = 320193 AND fiscal_year = 2022 AND concept IN ('Revenues','RevenueFromContractWithCustomerExcludingAssessedTax') GROUP BY concept, form_type ORDER BY concept, form_type
LIMIT 200
```
```
concept | form_type | row_count
RevenueFromContractWithCustomerExcludingAssessedTax | 10-K | 3
RevenueFromContractWithCustomerExcludingAssessedTax | 10-Q | 10
```
### E-16ee26 — Check whether both XBRL revenue concepts appear for Apple FY2022 and how many rows each filing type contributes.
Backend: zetaris-rest, 2 row(s)
```sql
SELECT concept, form_type, COUNT(*) AS cnt FROM edgar.revenue_facts WHERE cik=320193 AND fiscal_year=2022 AND concept IN ('Revenues','RevenueFromContractWithCustomerExcludingAssessedTax') GROUP BY concept, form_type ORDER BY concept, form_type
LIMIT 200
```
```
concept | form_type | cnt
RevenueFromContractWithCustomerExcludingAssessedTax | 10-K | 3
RevenueFromContractWithCustomerExcludingAssessedTax | 10-Q | 10
```
### E-038ee2 — Determine whether both XBRL revenue concepts ('Revenues' and 'RevenueFromContractWithCustomerExcludingAssessedTax') appear for Apple FY2022.
Backend: zetaris-rest, 1 row(s)
```sql
SELECT concept, COUNT(*) AS rows FROM edgar.revenue_facts WHERE cik=320193 AND fiscal_year=2022 GROUP BY concept
LIMIT 200
```
```
concept | rows
RevenueFromContractWithCustomerExcludingAssessedTax | 13
```
### E-71274f — List distinct filings (form type and period) for Apple FY2022 revenue to see quarterly vs annual and presence of amendments.
Backend: zetaris-rest, 13 row(s)
```sql
SELECT DISTINCT form_type, period_start, period_end, accession_number FROM edgar.revenue_facts WHERE cik = 320193 AND fiscal_year = 2022 AND concept = 'RevenueFromContractWithCustomerExcludingAssessedTax' ORDER BY form_type, period_start
LIMIT 200
```
```
form_type | period_start | period_end | accession_number
10-K | 2019-09-29 | 2020-09-26 | 0000320193-22-000108
10-K | 2020-09-27 | 2021-09-25 | 0000320193-22-000108
10-K | 2021-09-26 | 2022-09-24 | 0000320193-22-000108
10-Q | 2020-09-27 | 2021-06-26 | 0000320193-22-000070
10-Q | 2020-09-27 | 2021-03-27 | 0000320193-22-000059
10-Q | 2020-09-27 | 2020-12-26 | 0000320193-22-000007
10-Q | 2020-12-27 | 2021-03-27 | 0000320193-22-000059
10-Q | 2021-03-28 | 2021-06-26 | 0000320193-22-000070
10-Q | 2021-09-26 | 2021-12-25 | 0000320193-22-000007
10-Q | 2021-09-26 | 2022-06-25 | 0000320193-22-000070
10-Q | 2021-09-26 | 2022-03-26 | 0000320193-22-000059
10-Q | 2021-12-26 | 2022-03-26 | 0000320193-22-000059
... (1 more rows, 13 total)
```
### E-b4663b — Test whether the 'Revenues' XBRL concept appears for Apple FY2022, which would support hypothesis H-1418d9 (two concepts).
Backend: zetaris-rest, 0 row(s)
```sql
SELECT concept, COUNT(*) AS rows FROM edgar.revenue_facts WHERE cik = 320193 AND fiscal_year = 2022 AND concept = 'Revenues' GROUP BY concept
LIMIT 200
```
```
concept | rows
(0 rows)
```
### E-0d779b — Check if any fiscal period has more than one distinct accession number (indicating amendments/restatements) for Apple FY2022 revenue.
Backend: zetaris-rest, 13 row(s)
```sql
SELECT period_start, period_end, COUNT(DISTINCT accession_number) AS accession_count FROM edgar.revenue_facts WHERE cik = 320193 AND fiscal_year = 2022 AND concept = 'RevenueFromContractWithCustomerExcludingAssessedTax' GROUP BY period_start, period_end ORDER BY period_start
LIMIT 200
```
```
period_start | period_end | accession_count
2019-09-29 | 2020-09-26 | 1
2020-09-27 | 2020-12-26 | 1
2020-09-27 | 2021-03-27 | 1
2020-09-27 | 2021-09-25 | 1
2020-09-27 | 2021-06-26 | 1
2020-12-27 | 2021-03-27 | 1
2021-03-28 | 2021-06-26 | 1
2021-09-26 | 2022-03-26 | 1
2021-09-26 | 2022-09-24 | 1
2021-09-26 | 2021-12-25 | 1
2021-09-26 | 2022-06-25 | 1
2021-12-26 | 2022-03-26 | 1
... (1 more rows, 13 total)
```
### E-0a1c48 — Verify that each distinct fiscal period in Apple FY2022 revenue rows has exactly one accession number (no duplicate filings for the same period).
Backend: zetaris-rest, 13 row(s)
```sql
SELECT period_start, period_end, COUNT(DISTINCT accession_number) AS accession_count FROM lightning.metastore.explainwhy.explainwhy_usl.revenue_fact WHERE cik = '320193' AND fiscal_year = 2022 AND concept = 'RevenueFromContractWithCustomerExcludingAssessedTax' GROUP BY period_start, period_end ORDER BY period_start, period_end
LIMIT 200
```
```
period_start | period_end | accession_count
2019-09-29 | 2020-09-26 | 1
2020-09-27 | 2020-12-26 | 1
2020-09-27 | 2021-03-27 | 1
2020-09-27 | 2021-06-26 | 1
2020-09-27 | 2021-09-25 | 1
2020-12-27 | 2021-03-27 | 1
2021-03-28 | 2021-06-26 | 1
2021-09-26 | 2021-12-25 | 1
2021-09-26 | 2022-03-26 | 1
2021-09-26 | 2022-06-25 | 1
2021-09-26 | 2022-09-24 | 1
2021-12-26 | 2022-03-26 | 1
... (1 more rows, 13 total)
```

## Run
- backend `zetaris-rest`, model `nvidia/nemotron-3-super-120b-a12b`, 16 LLM calls, 175.4 s
- Markovian: 11 steps, 11674 prompt tokens vs ~48172 for a full-transcript loop (75.8% saved)
- critic rounds: 3; H-MEM memories written: 3
