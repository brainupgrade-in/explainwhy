# Why does IBM have no revenue rows under the RevenueFromContractWithCustomerExcludingAssessedTax concept?

**Answer.** IBM shows zero rows for the RevenueFromContractWithCustomerExcludingAssessedTax concept because it does not use that XBRL tag for its revenue data. Instead, IBM reports all revenue through the legacy Revenues concept, which has 235 rows spanning fiscal years 2009‑2026. This pattern is likely due to IBM not having adopted ASC 606‑based contract‑revenue tagging in its filings.

## Verified claims (critic-checked against query results)
- IBM has 0 rows for the concept RevenueFromContractWithCustomerExcludingAssessedTax. — evidence: E-51bc1b
- IBM has 235 rows for the concept Revenues. — evidence: E-f8e3dd
- The only revenue‑related concept IBM uses is Revenues (235 rows). — evidence: E-a756b4, E-e5ce09
- IBM’s Revenues concept spans fiscal years 2009 through 2026. — evidence: E-4a41de
- IBM has 0 rows with NULL period_frame for the RevenueFromContractWithCustomerExcludingAssessedTax concept. — evidence: E-6e13ca

## Inferences (likely causes the data cannot prove; not critic-verified)
- The absence of the ASC 606 tag suggests IBM has not adopted ASC 606 reporting in its XBRL filings. — basis: ['Claim 1', 'Claim 3']
- IBM continues to tag revenue with the legacy Revenues concept rather than updating to the newer contract‑revenue concept. — basis: ['Claim 2', 'Claim 3', 'Claim 4']

## Hypotheses
- `H-5700b4` **supported** — Data‑artifact: IBM’s XBRL filings tag revenue only with the legacy 'Revenues' concept; the newer 'RevenueFromContractWithCustomerExcludingAssessedTax' concept is absent because IBM has not updated its taxonomy tagging. (E-4a41de, E-51bc1b, E-a756b4, E-e5ce09)<br>why: IBM tags revenue only with the legacy Revenues concept; the newer concept is absent.
- `H-3b6fe1` **refuted** — Data‑artifact: IBM’s rows for that concept exist but are filtered out because they have a NULL period_frame (indicating duplicate/follow‑on filings) and the view excludes NULL period_frame values. (E-6e13ca)<br>why: There are zero rows with NULL period_frame for the concept, so hiding due to NULL period_frame does not apply.
- `H-2ff39e` **supported** — Real‑world: IBM has not adopted ASC 606 (Revenue from Contracts with Customers) reporting, so it does not populate the RevenueFromContractWithCustomerExcludingAssessedTax concept in its XBRL submissions. (E-51bc1b, E-a756b4, E-e5ce09)<br>why: No ASC 606 concept appears, indicating IBM has not adopted ASC 606 reporting.
- `H-0dcf41` **refuted** — Real‑world: IBM reports revenue using other US‑GAAP elements (e.g., RevenueFromLicensingArrangements, ServiceRevenue) rather than the generic contract‑revenue concept, so the specific concept is intentionally omitted. (E-a756b4, E-e5ce09)<br>why: IBM does not use other revenue concepts; it relies solely on Revenues.

## Evidence (Zetaris SQL)
### E-51bc1b — Check if IBM has any rows for the RevenueFromContractWithCustomerExcludingAssessedTax concept.
Backend: zetaris-rest, 0 row(s)
```sql
SELECT cik, concept, COUNT(*) AS row_count FROM edgar.revenue_facts WHERE cik = 51143 AND concept = 'RevenueFromContractWithCustomerExcludingAssessedTax' GROUP BY cik, concept
LIMIT 200
```
```
cik | concept | row_count
(0 rows)
```
### E-f8e3dd — Check whether IBM reports revenue using the legacy Revenues concept.
Backend: zetaris-rest, 1 row(s)
```sql
SELECT COUNT(*) AS rev_count FROM edgar.revenue_facts WHERE cik=51143 AND concept='Revenues'
LIMIT 200
```
```
rev_count
235
```
### E-6e13ca — Check if IBM has any rows for the concept with NULL period_frame (possible duplicate/follow-on filings that might be excluded)
Backend: zetaris-rest, 1 row(s)
```sql
SELECT COUNT(*) AS null_frame_count FROM edgar.revenue_facts WHERE cik = 51143 AND concept = 'RevenueFromContractWithCustomerExcludingAssessedTax' AND period_frame IS NULL
LIMIT 200
```
```
null_frame_count
0
```
### E-a756b4 — List all XBRL concepts IBM uses and their frequencies to see if alternative revenue concepts appear.
Backend: zetaris-rest, 1 row(s)
```sql
SELECT concept, COUNT(*) AS row_count FROM edgar.revenue_facts WHERE cik = 51143 GROUP BY concept ORDER BY row_count DESC LIMIT 20
```
```
concept | row_count
Revenues | 235
```
### E-e5ce09 — Check if IBM uses any other revenue-related XBRL concepts besides 'Revenues'
Backend: zetaris-rest, 1 row(s)
```sql
select concept, count(*) as cnt from edgar.revenue_facts where cik = 51143 and concept like '%Revenue%' group by concept order by cnt desc
LIMIT 200
```
```
concept | cnt
Revenues | 235
```
### E-4a41de — Determine the range of fiscal years for which IBM reports revenue using the legacy Revenues concept.
Backend: zetaris-rest, 1 row(s)
```sql
select min(fiscal_year) as min_fy, max(fiscal_year) as max_fy from edgar.revenue_facts where cik = 51143 and concept = 'Revenues'
LIMIT 200
```
```
min_fy | max_fy
2009 | 2026
```

## Run
- backend `zetaris-rest`, model `nvidia/nemotron-3-super-120b-a12b`, 13 LLM calls, 122.6 s
- Markovian: 9 steps, 5080 prompt tokens vs ~20280 for a full-transcript loop (75.0% saved)
- critic rounds: 2; H-MEM memories written: 5
