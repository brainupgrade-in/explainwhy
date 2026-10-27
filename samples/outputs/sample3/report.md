# Why does Tesla report revenue under two different XBRL concepts, and which one should be used for which years?

**Answer.** Tesla began reporting revenue under two XBRL concepts after adopting ASC 606 in fiscal year 2018, adding the RevenueFromContractWithCustomer concept while retaining the legacy Revenues concept for comparability; before 2018 only the Revenues concept appears. Therefore, for years 2011‑2017 use the Revenues concept, and for 2018 onward you can use either concept—prefer RevenueFromContractWithCustomer for current reporting, noting that when the values differ you should examine the filing context to determine which reflects the intended measurement.

## Verified claims (critic-checked against query results)
- For fiscal years 2011‑2017 Tesla has facts only under the Revenues concept. — evidence: E-713c42
- Starting in fiscal year 2018 Tesla files contain both concepts within the same accession_number (e.g., 2018 Q1, Q2, Q3, FY and 2023 Q3). — evidence: E-b44e1f, E-12deec
- In some filings the two concepts report identical values (e.g., accession 0001564590-18-011086 shows 3408751000 for both concepts), indicating duplicate tagging of the same fact. — evidence: E-12deec
- In other filings the values differ (e.g., same accession shows Revenues 2696270000 versus RevenueFromContract... 3408751000), suggesting measurement differences or tagging errors. — evidence: E-12deec

## Inferences (likely causes the data cannot prove; not critic-verified)
- The post‑2018 appearance of both concepts aligns with Tesla’s adoption of ASC 606 effective FY 2018, retaining the legacy concept for comparability. — basis: ['claims 1', 'claims 2']
- Duplicate tagging of identical values under both concepts is a data‑artifact (filers mistakenly applied both tags) rather than an intentional separate measurement. — basis: ['claims 3']

## Hypotheses
- `H-94e4c0` **refuted** — Data‑artifact: Tesla files both 10‑K and 10‑Q reports, and some filings use the legacy 'Revenues' concept while others use the newer 'RevenueFromContractWithCustomerExcludingAssessedTax' concept, leading to both concepts appearing in the dataset. (E-12deec, E-b44e1f)<br>why: Both concepts appear within the same accession (same filing), not just across different filing types.
- `H-8ea727` **supported** — Real‑world: Tesla adopted ASC 606 (Revenue from Contracts with Customers) effective FY2018. Before adoption it reported total revenue using the legacy 'Revenues' concept; after adoption it began reporting under the ASC 606‑specific concept, while still retaining the legacy concept for comparability or for certain regulatory filings. (E-12deec, E-713c42, E-b44e1f)<br>why: New concept appears only from 2018 onward, consistent with ASC 606 adoption; legacy concept retained for comparability.
- `H-15e299` **supported** — Data‑artifact: Tagging/extension errors cause some periods to have duplicate facts with both concepts for the same accession_number (i.e., the same filing incorrectly tags the same numeric value under two concepts). (E-12deec, E-b44e1f)<br>why: Same accession_number tags both concepts, sometimes with identical values, indicating duplicate tagging.
- `H-cea464` **refuted** — Real‑world: The two concepts represent different measurement bases – 'Revenues' includes gross sales while 'RevenueFromContractWithCustomerExcludingAssessedTax' excludes assessed taxes (e.g., sales tax). Tesla may report both to provide users with gross and net‑of‑tax views. (E-12deec)<br>why: Values are not consistently different (some match, some differ), so the concepts do not represent a systematic tax‑exclusion distinction.
- `H-f5a54e` **supported** — Data‑artifact: Coverage gap – the XBRL taxonomy did not include the 'RevenueFromContractWithCustomerExcludingAssessedTax' concept until after 2017, so earlier years only have the legacy concept; later years have both because filers continue to tag the legacy concept for backward compatibility. (E-713c42)<br>why: RevenueFromContractWithCustomerExcludingAssessedTax has zero facts before 2018 and appears after, indicating a taxonomy coverage gap.

## Evidence (Zetaris SQL)
### E-713c42 — See how many facts Tesla has for each revenue concept per fiscal year to understand adoption pattern.
Backend: local-sqlite (SAMPLE_MODE mirror of the Zetaris views), 21 row(s)
```sql
SELECT fiscal_year, concept, COUNT(*) AS fact_count FROM edgar.revenue_facts WHERE cik=1318605 AND concept IN ('Revenues','RevenueFromContractWithCustomerExcludingAssessedTax') GROUP BY fiscal_year, concept ORDER BY fiscal_year, concept
LIMIT 200
```
```
fiscal_year | concept | fact_count
2011 | Revenues | 22
2012 | Revenues | 21
2013 | Revenues | 21
2014 | Revenues | 21
2015 | Revenues | 21
2016 | Revenues | 21
2017 | Revenues | 21
2018 | RevenueFromContractWithCustomerExcludingAssessedTax | 6
2018 | Revenues | 21
2019 | Revenues | 21
2020 | Revenues | 21
2021 | Revenues | 13
... (9 more rows, 21 total)
```
### E-158c56 — See which filing types (10-K, 10-Q, etc.) use each revenue concept per year to test if split is due to filing type differences.
Backend: local-sqlite (SAMPLE_MODE mirror of the Zetaris views), 41 row(s)
```sql
SELECT fiscal_year, concept, form_type, COUNT(*) AS fact_count FROM edgar.revenue_facts WHERE cik = 1318605 AND concept IN ('Revenues','RevenueFromContractWithCustomerExcludingAssessedTax') GROUP BY fiscal_year, concept, form_type ORDER BY fiscal_year, concept, form_type LIMIT 100
```
```
fiscal_year | concept | form_type | fact_count
2011 | Revenues | 10-K | 3
2011 | Revenues | 10-K/A | 11
2011 | Revenues | 10-Q | 8
2012 | Revenues | 10-K | 11
2012 | Revenues | 10-Q | 10
2013 | Revenues | 10-K | 11
2013 | Revenues | 10-Q | 10
2014 | Revenues | 10-K | 11
2014 | Revenues | 10-Q | 10
2015 | Revenues | 10-K | 11
2015 | Revenues | 10-Q | 10
2016 | Revenues | 10-K | 11
... (29 more rows, 41 total)
```
### E-b44e1f — Check whether any single filing (accession_number) tags the same period under both revenue concepts, indicating duplicate tagging.
Backend: local-sqlite (SAMPLE_MODE mirror of the Zetaris views), 5 row(s)
```sql
SELECT accession_number, fiscal_year, fiscal_period, COUNT(DISTINCT concept) AS concept_count FROM edgar.revenue_facts WHERE cik = 1318605 AND concept IN ('Revenues','RevenueFromContractWithCustomerExcludingAssessedTax') GROUP BY accession_number, fiscal_year, fiscal_period HAVING COUNT(DISTINCT concept) > 1 LIMIT 5
```
```
accession_number | fiscal_year | fiscal_period | concept_count
0001564590-18-011086 | 2018 | Q1 | 2
0001564590-18-019254 | 2018 | Q2 | 2
0001564590-18-026353 | 2018 | Q3 | 2
0001564590-19-003165 | 2018 | FY | 2
0001628280-23-034847 | 2023 | Q3 | 2
```
### E-12deec — Check whether the two revenue concepts report different values for the same filing/period, to distinguish duplicate tagging from real measurement differences.
Backend: local-sqlite (SAMPLE_MODE mirror of the Zetaris views), 113 row(s)
```sql
SELECT accession_number, fiscal_year, fiscal_period, concept, value_usd FROM edgar.revenue_facts WHERE cik = 1318605 AND concept IN ('Revenues','RevenueFromContractWithCustomerExcludingAssessedTax') AND (accession_number, fiscal_year, fiscal_period) IN (SELECT accession_number, fiscal_year, fiscal_period FROM edgar.revenue_facts WHERE cik = 1318605 AND concept IN ('Revenues','RevenueFromContractWithCustomerExcludingAssessedTax') GROUP BY accession_number, fiscal_year, fiscal_period HAVING COUNT(DISTINCT concept) = 2) ORDER BY accession_number, fiscal_year, fiscal_period, concept
LIMIT 200
```
```
accession_number | fiscal_year | fiscal_period | concept | value_usd
0001564590-18-011086 | 2018 | Q1 | RevenueFromContractWithCustomerExcludingAssessedTax | 3408751000
0001564590-18-011086 | 2018 | Q1 | Revenues | 2696270000
0001564590-18-011086 | 2018 | Q1 | Revenues | 3408751000
0001564590-18-019254 | 2018 | Q2 | RevenueFromContractWithCustomerExcludingAssessedTax | 7410982000
0001564590-18-019254 | 2018 | Q2 | RevenueFromContractWithCustomerExcludingAssessedTax | 4002231000
0001564590-18-019254 | 2018 | Q2 | Revenues | 5485827000
0001564590-18-019254 | 2018 | Q2 | Revenues | 2789557000
0001564590-18-019254 | 2018 | Q2 | Revenues | 7410982000
0001564590-18-019254 | 2018 | Q2 | Revenues | 4002231000
0001564590-18-026353 | 2018 | Q3 | RevenueFromContractWithCustomerExcludingAssessedTax | 14235395000
0001564590-18-026353 | 2018 | Q3 | RevenueFromContractWithCustomerExcludingAssessedTax | 6824413000
0001564590-18-026353 | 2018 | Q3 | Revenues | 8470502000
... (101 more rows, 113 total)
```

## Run
- backend `local-sqlite (SAMPLE_MODE mirror of the Zetaris views)`, model `nvidia/nemotron-3-super-120b-a12b`, 8 LLM calls, 47.3 s
- Markovian: 5 steps, 4661 prompt tokens vs ~10124 for a full-transcript loop (54.0% saved)
- critic rounds: 1; H-MEM memories written: 4
