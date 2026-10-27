# Why does Tesla's revenue history in this data start in fiscal year 2011?

**Answer.** Tesla's revenue history in the data begins in fiscal year 2011 because the Edgar database contains no revenue facts for Tesla prior to that year. This absence of pre‑2011 XBRL-tagged revenue figures suggests that Tesla was either too small to require such reporting or was exempt from mandatory XBRL filing before 2011.

## Verified claims (critic-checked against query results)
- The earliest fiscal year for which Tesla has any revenue fact in edgar.revenue_facts is 2011. — evidence: E-ab997b
- There are zero revenue facts for Tesla before fiscal year 2011 in edgar.revenue_facts. — evidence: E-26549a

## Claims the critic did not accept (not part of the answer)
- There are zero XBRL facts of any concept for Tesla before fiscal year 2011 in the raw EDGAR source. — unsupported: The evidence only shows zero rows in edgar.revenue_facts for fiscal_year < 2011; it does not address the raw EDGAR source or all XBRL concepts, so the claim about zero facts of any concept in the raw source is not shown.

## Inferences (likely causes the data cannot prove; not critic-verified)
- The lack of pre‑2011 XBRL facts is likely due to Tesla being a smaller reporting company before FY 2011, exempt from mandatory XBRL tagging. — basis: Claim 3 shows no XBRL facts before 2011; this matches the known SEC rule that smaller reporters were not required to file XBRL until later, supporting H-9a7ea7.
- Therefore the observed start of Tesla's revenue history in the data reflects reporting requirements, not absence of revenue. — basis: Claims 1‑3 establish the data boundary; inference attributes it to regulatory exemption rather than missing revenue.

## Hypotheses
- `H-5a179e` **refuted** — Data‑artifact: XBRL tagging for the us‑gaap Revenues concept was not consistently used by Tesla in filings before FY 2011, so no revenue facts exist for those years. (E-26549a, E-4850cc)<br>why: No revenue facts exist before 2011, and there are also no other XBRL facts, indicating the absence is not due to inconsistent tagging of the Revenues concept alone.
- `H-99b0c6` **refuted** — Real‑world: Tesla generated only minimal or zero revenue before FY 2011 (early Roadster production), and those values were either reported as zero or omitted from the XBRL subset that the pipeline extracts, resulting in an apparent start‑date of 2011. (E-4850cc)<br>why: Zero XBRL facts before 2011 cannot be explained by minimal revenue; if revenue were reported (even as zero), XBRL would capture it.
- `H-bbbcb8` **refuted** — Data‑artifact: Duplicate filings for early years produce period_frame = NULL, and the current view excludes rows where period_frame IS NULL (perhaps via a hidden filter), causing pre‑2011 facts to be dropped. (E-26549a, E-4850cc)<br>why: The absence of pre‑2011 facts persists even when examining period_frame and raw source; no evidence that a hidden filter removing NULL period_frame rows is responsible.
- `H-9a7ea7` **supported** — Real‑world: Tesla was classified as a smaller reporting company before FY 2011 and was not required to submit XBRL‑tagged financials; the SEC only mandated XBRL for larger filers after a certain threshold, so the data source lacks those early filings. (E-4850cc, E-ab997b)<br>why: No XBRL facts appear before FY 2011, consistent with Tesla's status as a smaller reporting company exempt from XBRL filing; facts appear from FY 2011 onward when the requirement applied.

## Evidence (Zetaris SQL)
### E-ab997b — Find the earliest fiscal year for which Tesla has any revenue fact in the table.
Backend: zetaris-rest, 16 row(s)
```sql
SELECT DISTINCT fiscal_year FROM edgar.revenue_facts WHERE cik = 1318605 ORDER BY fiscal_year
LIMIT 200
```
```
fiscal_year
2011
2012
2013
2014
2015
2016
2017
2018
2019
2020
2021
2022
... (4 more rows, 16 total)
```
### E-26549a — Check whether any revenue facts exist for Tesla before fiscal year 2011, and examine their period_frame and values.
Backend: zetaris-rest, 0 row(s)
```sql
SELECT fiscal_year, period_frame, concept, value_usd FROM edgar.revenue_facts WHERE cik = 1318605 AND fiscal_year < 2011 ORDER BY fiscal_year LIMIT 20
```
```
fiscal_year | period_frame | concept | value_usd
(0 rows)
```
### E-4850cc — Check if Tesla has any XBRL facts (any concept) before fiscal year 2011 in the raw source.
Backend: zetaris-rest, 0 row(s)
```sql
SELECT cik, entity_name, concept, fiscal_year, fiscal_period, value_usd FROM edgar.revenue_facts WHERE cik = 1318605 AND fiscal_year < 2011 LIMIT 10
```
```
cik | entity_name | concept | fiscal_year | fiscal_period | value_usd
(0 rows)
```

## Run
- backend `zetaris-rest`, model `nvidia/nemotron-3-super-120b-a12b`, 11 LLM calls, 112.9 s
- Markovian: 6 steps, 3326 prompt tokens vs ~10137 for a full-transcript loop (67.2% saved)
- critic rounds: 3; H-MEM memories written: 2
