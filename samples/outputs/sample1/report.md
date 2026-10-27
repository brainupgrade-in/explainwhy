# Why does Apple's revenue history under the us-gaap Revenues concept stop at fiscal year 2018?

**Answer.** Apple reported no data for the traditional 'Revenues' concept after fiscal year 2018, while it began filing figures for the 'RevenueFromContractWithCustomerExcludingAssessedTax' concept starting in FY 2019. This change is likely because Apple adopted ASC 606, which required companies to recognize revenue using the new contract‑based concept rather than the older generic revenues line item.

## Verified claims (critic-checked against query results)
- Apple has 0 rows for the 'Revenues' concept after fiscal year 2018. — evidence: E-bdbb98
- Apple has rows for the 'RevenueFromContractWithCustomerExcludingAssessedTax' concept for fiscal years 2019, 2020, 2021, 2022, and 2023. — evidence: E-53fe1d

## Inferences (likely causes the data cannot prove; not critic-verified)
- The switch aligns with ASC 606 adoption, which required entities to use the new revenue recognition concept. — basis: Claims show cessation of old concept and start of new concept after 2018.

## Hypotheses
- `H-ec70e6` **supported** — After fiscal year 2018 Apple stopped filing under the legacy us‑gaap 'Revenues' concept and began using the newer 'RevenueFromContractWithCustomerExcludingAssessedTax' concept due to ASC 606 adoption, so the old concept simply has no rows after 2018. (E-53fe1d, E-bdbb98)<br>why: Old concept disappears exactly when new concept appears, consistent with a standard-driven change.
- `H-2811fd` **refuted** — The EDGAR ingestion pipeline experienced a coverage gap for Apple’s filings after a certain date (e.g., due to a temporary API throttling or CIK‑match failure), so no facts—including those under 'Revenues'—were loaded for periods beyond FY 2018. (E-53fe1d)<br>why: New concept rows exist after 2018, proving data were loaded for that period.
- `H-dee925` **refuted** — Duplicate filing handling logic inadvertently removed older 'Revenues' facts when a later filing (e.g., an amended 10‑K/A) with the same period but a later filed_date was ingested, leaving only the newest version which may have omitted the legacy concept. (E-53fe1d, E-bdbb98)<br>why: If duplicate removal had occurred, some 'Revenues' rows would remain; instead there are none after 2018.
- `H-cb2288` **refuted** — Apple reclassified a portion of its revenue (e.g., services, licensing) into separate line items that are no longer captured under the aggregate 'Revenues' concept, causing the reported total under that concept to appear flat or missing after 2018 while overall revenue continues to rise. (E-bdbb98)<br>why: A partial reclassification would still leave some 'Revenues' values; the concept shows zero rows after 2018.

## Evidence (Zetaris SQL)
### E-bdbb98 — Find the latest fiscal year for which Apple has a fact under the us-gaap Revenues concept.
Backend: local-sqlite (SAMPLE_MODE mirror of the Zetaris views), 1 row(s)
```sql
SELECT MAX(fiscal_year) AS max_fy FROM edgar.revenue_facts WHERE cik = 320193 AND concept = 'Revenues'
LIMIT 200
```
```
max_fy
2018
```
### E-53fe1d — Test if Apple uses the newer revenue concept after FY2018, supporting H-ec70e6.
Backend: local-sqlite (SAMPLE_MODE mirror of the Zetaris views), 5 row(s)
```sql
select distinct fiscal_year from edgar.revenue_facts where cik=320193 and concept='RevenueFromContractWithCustomerExcludingAssessedTax' and fiscal_year>2018 order by fiscal_year limit 5
```
```
fiscal_year
2019
2020
2021
2022
2023
```

## Run
- backend `local-sqlite (SAMPLE_MODE mirror of the Zetaris views)`, model `nvidia/nemotron-3-super-120b-a12b`, 7 LLM calls, 59.6 s
- Markovian: 3 steps, 1375 prompt tokens vs ~2382 for a full-transcript loop (42.3% saved)
- critic rounds: 1; H-MEM memories written: 2
