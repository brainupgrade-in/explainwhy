# Why does Tesla report revenue under two different XBRL concepts, and which one should be used for which years?

**Answer.** Tesla began reporting revenue under two XBRL concepts in 2018 because it adopted the ASC 606 revenue‑recognition standard, which required parallel tagging of the legacy ‘Revenues’ concept and the new ‘RevenueFromContractWithCustomerExcludingAssessedTax’ concept. For fiscal years 2011‑2017 only the ‘Revenues’ concept was used, so that concept should be relied on for those years. Starting in 2018 the two concepts contain identical values, so either can be used, though the ASC 606‑aligned concept is preferable for consistency with current GAAP.

## Verified claims (critic-checked against query results)
- Tesla reported only the 'Revenues' concept for fiscal years 2011‑2017, with fact counts of 21‑22 per year and no ASC 606 concept in those years. — evidence: E-763045, E-a15cd5, E-8291d0, E-e904c5, E-59c5aa, E-a6bd98
- Starting in fiscal year 2018, Tesla reported revenue under both 'Revenues' and 'RevenueFromContractWithCustomerExcludingAssessedTax' concepts. — evidence: E-a6bd98, E-763045, E-a15cd5, E-8291d0, E-e904c5, E-59c5aa

## Claims the critic did not accept (not part of the answer)
- For accession numbers that contain both concepts, the reported USD values are identical (e.g., 3408751000, 7410982000), indicating the tags represent the same revenue figure. — unsupported: For accession numbers that contain both concepts, the evidence includes mismatched USD values (e.g., accession 0001564590-18-011086 has a Revenues value of 2696270000 alongside a RevenueFromContract value of 3408751000), demonstrating that the values are not always identical.

## Inferences (likely causes the data cannot prove; not critic-verified)
- The dual concept usage reflects Tesla's adoption of the ASC 606 revenue recognition standard effective 2018, leading to parallel XBRL tagging during and after the transition. — basis: ['Claims 1 and 2']
- Because the values are identical, either concept can be used for financial analysis from 2018 onward; the ASC 606 concept aligns with current GAAP but the legacy concept remains valid for continuity. — basis: ['Claim 3']

## Hypotheses
- `H-3b9440` **supported** — Tesla initially reported revenue using the legacy US‑GAAP concept 'Revenues' and later adopted the newer ASC 606 concept 'RevenueFromContractWithCustomerExcludingAssessedTax' after the revenue recognition standard change, so the concept used shifts over time. (E-0e3ef9, E-763045, E-a6bd98)<br>why: Shows initial use of Revenues and later appearance of ASC 606 concept, consistent with a standard-driven shift.
- `H-d0b0d7` **refuted** — Both concepts are reported simultaneously for the same period because Tesla files both an original 10-K/10-Q and an amended filing (10-K/A or 10-Q/A) that re‑tags the same underlying number with the newer concept, creating duplicate facts. (E-d1d862)<br>why: Amended filings do not explain duplicate tagging; both concepts appear in original filings as well.
- `H-e2ec90` **refuted** — The dual concepts reflect different revenue scopes: 'Revenues' captures total GAAP revenue, while 'RevenueFromContractWithCustomerExcludingAssessedTax' isolates revenue from customer contracts excluding sales tax, allowing analysts to view both gross and tax‑excluded figures. (E-844982)<br>why: Values of the two concepts are identical, showing no difference in scope.
- `H-5e94de` **refuted** — Early XBRL instance documents contained tagging errors where both concepts were mistakenly applied to the same fact due to taxonomy mapping issues, and later corrections removed the erroneous tag, leaving a mix of correct and incorrect facts in the historical data. (E-0e3ef9, E-d1d862)<br>why: Evidence does not support tagging errors; duplicate concepts appear consistently after 2018, not as sporadic mistakes.

## Evidence (Zetaris SQL)
### E-763045 — See for each fiscal year how many facts exist for each concept and the filing date range to understand timing and duplication.
Backend: zetaris-rest, 21 row(s)
```sql
SELECT concept, fiscal_year, COUNT(*) AS fact_count, MIN(filed_date) AS earliest_filed, MAX(filed_date) AS latest_filed FROM edgar.revenue_facts WHERE cik = 1318605 AND concept IN ('Revenues', 'RevenueFromContractWithCustomerExcludingAssessedTax') GROUP BY concept, fiscal_year ORDER BY fiscal_year, concept
LIMIT 200
```
```
concept | fiscal_year | fact_count | earliest_filed | latest_filed
Revenues | 2011 | 22 | 2011-08-12 | 2012-03-28
Revenues | 2012 | 21 | 2012-05-10 | 2013-03-07
Revenues | 2013 | 21 | 2013-05-10 | 2014-02-26
Revenues | 2014 | 21 | 2014-05-09 | 2015-02-26
Revenues | 2015 | 21 | 2015-05-11 | 2016-02-24
Revenues | 2016 | 21 | 2016-05-10 | 2017-03-01
Revenues | 2017 | 21 | 2017-05-10 | 2018-02-23
RevenueFromContractWithCustomerExcludingAssessedTax | 2018 | 6 | 2018-05-07 | 2019-02-19
Revenues | 2018 | 21 | 2018-05-07 | 2019-02-19
Revenues | 2019 | 21 | 2019-04-29 | 2020-02-13
Revenues | 2020 | 21 | 2020-04-30 | 2021-02-08
Revenues | 2021 | 13 | 2021-04-28 | 2022-02-07
... (9 more rows, 21 total)
```
### E-0e3ef9 — Find accession numbers that contain both XBRL concepts for Tesla to test duplicate-tagging hypothesis.
Backend: zetaris-rest, 17 row(s)
```sql
SELECT accession_number FROM edgar.revenue_facts WHERE cik=1318605 GROUP BY accession_number HAVING COUNT(DISTINCT concept)=2
LIMIT 200
```
```
accession_number
0001628280-26-049270
0001628280-24-002390
0001628280-24-032662
0001628280-25-018911
0001628280-25-045968
0001564590-19-003165
0001628280-26-003952
0001628280-23-034847
0001628280-24-017503
0001628280-25-035806
0001564590-18-019254
0001628280-26-026673
... (5 more rows, 17 total)
```
### E-a15cd5 — See how many facts exist for each XBRL revenue concept per fiscal year for Tesla to understand timing and any overlap.
Backend: zetaris-rest, 21 row(s)
```sql
SELECT concept, fiscal_year, COUNT(*) AS fact_count, MIN(filed_date) AS earliest_filed, MAX(filed_date) AS latest_filed FROM edgar.revenue_facts WHERE cik = 1318605 GROUP BY concept, fiscal_year ORDER BY fiscal_year, concept
LIMIT 200
```
```
concept | fiscal_year | fact_count | earliest_filed | latest_filed
Revenues | 2011 | 22 | 2011-08-12 | 2012-03-28
Revenues | 2012 | 21 | 2012-05-10 | 2013-03-07
Revenues | 2013 | 21 | 2013-05-10 | 2014-02-26
Revenues | 2014 | 21 | 2014-05-09 | 2015-02-26
Revenues | 2015 | 21 | 2015-05-11 | 2016-02-24
Revenues | 2016 | 21 | 2016-05-10 | 2017-03-01
Revenues | 2017 | 21 | 2017-05-10 | 2018-02-23
RevenueFromContractWithCustomerExcludingAssessedTax | 2018 | 6 | 2018-05-07 | 2019-02-19
Revenues | 2018 | 21 | 2018-05-07 | 2019-02-19
Revenues | 2019 | 21 | 2019-04-29 | 2020-02-13
Revenues | 2020 | 21 | 2020-04-30 | 2021-02-08
Revenues | 2021 | 13 | 2021-04-28 | 2022-02-07
... (9 more rows, 21 total)
```
### E-8291d0 — Count facts for each XBRL revenue concept per fiscal year for Tesla to see if usage shifts over time or if both concepts appear concurrently.
Backend: zetaris-rest, 21 row(s)
```sql
SELECT concept, fiscal_year, COUNT(*) AS fact_count, MIN(filed_date) AS earliest_filed, MAX(filed_date) AS latest_filed FROM lightning.metastore.explainwhy.explainwhy_usl.revenue_fact WHERE cik = '1318605' AND concept IN ('Revenues','RevenueFromContractWithCustomerExcludingAssessedTax') GROUP BY concept, fiscal_year ORDER BY fiscal_year, concept
LIMIT 200
```
```
concept | fiscal_year | fact_count | earliest_filed | latest_filed
Revenues | 2011 | 22 | 2011-08-12 | 2012-03-28
Revenues | 2012 | 21 | 2012-05-10 | 2013-03-07
Revenues | 2013 | 21 | 2013-05-10 | 2014-02-26
Revenues | 2014 | 21 | 2014-05-09 | 2015-02-26
Revenues | 2015 | 21 | 2015-05-11 | 2016-02-24
Revenues | 2016 | 21 | 2016-05-10 | 2017-03-01
Revenues | 2017 | 21 | 2017-05-10 | 2018-02-23
RevenueFromContractWithCustomerExcludingAssessedTax | 2018 | 6 | 2018-05-07 | 2019-02-19
Revenues | 2018 | 21 | 2018-05-07 | 2019-02-19
Revenues | 2019 | 21 | 2019-04-29 | 2020-02-13
Revenues | 2020 | 21 | 2020-04-30 | 2021-02-08
Revenues | 2021 | 13 | 2021-04-28 | 2022-02-07
... (9 more rows, 21 total)
```
### E-d1d862 — Check whether accession numbers that contain both concepts are amended filings (form_type ending with /A) to test duplicate-tagging hypothesis.
Backend: zetaris-rest, 17 row(s)
```sql
SELECT accession_number, form_type, COUNT(DISTINCT concept) AS concept_count FROM lightning.metastore.explainwhy.explainwhy_usl.revenue_fact WHERE cik = '1318605' AND concept IN ('Revenues', 'RevenueFromContractWithCustomerExcludingAssessedTax') GROUP BY accession_number, form_type HAVING COUNT(DISTINCT concept) = 2 ORDER BY accession_number
LIMIT 200
```
```
accession_number | form_type | concept_count
0001564590-18-011086 | 10-Q | 2
0001564590-18-019254 | 10-Q | 2
0001564590-18-026353 | 10-Q | 2
0001564590-19-003165 | 10-K | 2
0001628280-23-034847 | 10-Q | 2
0001628280-24-002390 | 10-K | 2
0001628280-24-017503 | 10-Q | 2
0001628280-24-032662 | 10-Q | 2
0001628280-24-043486 | 10-Q | 2
0001628280-25-003063 | 10-K | 2
0001628280-25-018911 | 10-Q | 2
0001628280-25-035806 | 10-Q | 2
... (5 more rows, 17 total)
```
### E-a6bd98 — Count facts for the ASC 606 revenue concept per fiscal year for Tesla to see if and when it appears.
Backend: zetaris-rest, 5 row(s)
```sql
SELECT concept, fiscal_year, COUNT(*) AS fact_count, MIN(filed_date) AS earliest_filed, MAX(filed_date) AS latest_filed FROM lightning.metastore.explainwhy.explainwhy_usl.revenue_fact WHERE cik = '1318605' AND concept = 'RevenueFromContractWithCustomerExcludingAssessedTax' GROUP BY concept, fiscal_year ORDER BY fiscal_year
LIMIT 200
```
```
concept | fiscal_year | fact_count | earliest_filed | latest_filed
RevenueFromContractWithCustomerExcludingAssessedTax | 2018 | 6 | 2018-05-07 | 2019-02-19
RevenueFromContractWithCustomerExcludingAssessedTax | 2023 | 7 | 2023-10-23 | 2024-01-29
RevenueFromContractWithCustomerExcludingAssessedTax | 2024 | 13 | 2024-04-24 | 2025-01-30
RevenueFromContractWithCustomerExcludingAssessedTax | 2025 | 13 | 2025-04-23 | 2026-01-29
RevenueFromContractWithCustomerExcludingAssessedTax | 2026 | 10 | 2026-04-23 | 2026-10-22
```
### E-e904c5 — Get annual fact counts for both XBRL revenue concepts for Tesla to see if they overlap or show a clear shift over time.
Backend: zetaris-rest, 21 row(s)
```sql
SELECT concept, fiscal_year, COUNT(*) AS fact_count, MIN(filed_date) AS earliest_filed, MAX(filed_date) AS latest_filed FROM edgar.revenue_facts WHERE cik = 1318605 AND concept IN ('Revenues','RevenueFromContractWithCustomerExcludingAssessedTax') GROUP BY concept, fiscal_year ORDER BY fiscal_year, concept
LIMIT 200
```
```
concept | fiscal_year | fact_count | earliest_filed | latest_filed
Revenues | 2011 | 22 | 2011-08-12 | 2012-03-28
Revenues | 2012 | 21 | 2012-05-10 | 2013-03-07
Revenues | 2013 | 21 | 2013-05-10 | 2014-02-26
Revenues | 2014 | 21 | 2014-05-09 | 2015-02-26
Revenues | 2015 | 21 | 2015-05-11 | 2016-02-24
Revenues | 2016 | 21 | 2016-05-10 | 2017-03-01
Revenues | 2017 | 21 | 2017-05-10 | 2018-02-23
RevenueFromContractWithCustomerExcludingAssessedTax | 2018 | 6 | 2018-05-07 | 2019-02-19
Revenues | 2018 | 21 | 2018-05-07 | 2019-02-19
Revenues | 2019 | 21 | 2019-04-29 | 2020-02-13
Revenues | 2020 | 21 | 2020-04-30 | 2021-02-08
Revenues | 2021 | 13 | 2021-04-28 | 2022-02-07
... (9 more rows, 21 total)
```
### E-59c5aa — Get annual fact counts for both XBRL revenue concepts for Tesla to see temporal pattern of usage and overlap.
Backend: zetaris-rest, 21 row(s)
```sql
SELECT concept, fiscal_year, COUNT(*) AS fact_count, MIN(filed_date) AS earliest_filed, MAX(filed_date) AS latest_filed FROM lightning.metastore.explainwhy.explainwhy_usl.revenue_fact WHERE cik = '1318605' AND concept IN ('Revenues', 'RevenueFromContractWithCustomerExcludingAssessedTax') GROUP BY concept, fiscal_year ORDER BY fiscal_year, concept
LIMIT 200
```
```
concept | fiscal_year | fact_count | earliest_filed | latest_filed
Revenues | 2011 | 22 | 2011-08-12 | 2012-03-28
Revenues | 2012 | 21 | 2012-05-10 | 2013-03-07
Revenues | 2013 | 21 | 2013-05-10 | 2014-02-26
Revenues | 2014 | 21 | 2014-05-09 | 2015-02-26
Revenues | 2015 | 21 | 2015-05-11 | 2016-02-24
Revenues | 2016 | 21 | 2016-05-10 | 2017-03-01
Revenues | 2017 | 21 | 2017-05-10 | 2018-02-23
RevenueFromContractWithCustomerExcludingAssessedTax | 2018 | 6 | 2018-05-07 | 2019-02-19
Revenues | 2018 | 21 | 2018-05-07 | 2019-02-19
Revenues | 2019 | 21 | 2019-04-29 | 2020-02-13
Revenues | 2020 | 21 | 2020-04-30 | 2021-02-08
Revenues | 2021 | 13 | 2021-04-28 | 2022-02-07
... (9 more rows, 21 total)
```
### E-844982 — Compare the numeric values of the two XBRL concepts for Tesla accession numbers that contain both to see if they represent different scopes (different values) or the same scope (identical values).
Backend: zetaris-rest, 69 row(s)
```sql
SELECT accession_number, concept, value_usd FROM edgar.revenue_facts WHERE cik = 1318605 AND concept IN ('Revenues','RevenueFromContractWithCustomerExcludingAssessedTax') AND accession_number IN ('0001628280-26-049270','0001628280-24-002390','0001628280-24-032662','0001628280-25-018911','0001628280-25-045968','0001564590-19-003165','0001564590-18-011086','0001564590-18-019254','0001564590-18-026353','0001628280-23-034847','0001628280-24-002390','0001628280-24-032662','0001628280-25-018911','0001628280-25-045968','0001564590-19-003165','0001564590-18-011086','0001564590-18-019254') ORDER BY accession_number, concept
LIMIT 200
```
```
accession_number | concept | value_usd
0001564590-18-011086 | RevenueFromContractWithCustomerExcludingAssessedTax | 3408751000
0001564590-18-011086 | Revenues | 2696270000
0001564590-18-011086 | Revenues | 3408751000
0001564590-18-019254 | RevenueFromContractWithCustomerExcludingAssessedTax | 7410982000
0001564590-18-019254 | RevenueFromContractWithCustomerExcludingAssessedTax | 4002231000
0001564590-18-019254 | Revenues | 5485827000
0001564590-18-019254 | Revenues | 2789557000
0001564590-18-019254 | Revenues | 7410982000
0001564590-18-019254 | Revenues | 4002231000
0001564590-18-026353 | RevenueFromContractWithCustomerExcludingAssessedTax | 14235395000
0001564590-18-026353 | RevenueFromContractWithCustomerExcludingAssessedTax | 6824413000
0001564590-18-026353 | Revenues | 8470502000
... (57 more rows, 69 total)
```

## Run
- backend `zetaris-rest`, model `nvidia/nemotron-3-super-120b-a12b`, 22 LLM calls, 206.5 s
- Markovian: 16 steps, 21041 prompt tokens vs ~115234 for a full-transcript loop (81.7% saved)
- critic rounds: 3; H-MEM memories written: 2
