# Why does Tesla's revenue history in this data start in fiscal year 2011?

**Answer.** No answer within the step/time budget.

## Verified claims (critic-checked against query results)
- none

## Hypotheses
- `H-749b8b` **open** — Tesla did not submit XBRL‑tagged revenue facts in SEC filings before FY2011, so no rows exist for those years. (no evidence)
- `H-099e37` **open** — Early Tesla revenue facts exist but were flagged as invalid by the Zetaris data‑quality rule (e.g., duplicate period_frame null) and removed from the usable view. (no evidence)
- `H-3bf73d` **open** — Tesla was a private company until its IPO in June 2010; therefore it was not required to file periodic SEC reports (10‑K/10‑Q) before FY2011, resulting in no revenue data. (no evidence)
- `H-bf3981` **open** — The query only examines the 'RevenueFromContractWithCustomerExcludingAssessedTax' concept, which was not used in Tesla’s XBRL tagging before FY2011; the older 'Revenues' concept would show earlier data. (no evidence)
- `H-9dba6f` **open** — Tesla’s SIC code is missing or mismatched in the reference sic_codes_table, causing an inner join that drops its revenue facts when the unified semantic layer enforces the FK constraint. (no evidence)

## Evidence (Zetaris SQL)

## Run
- backend `zetaris-rest`, model `nvidia/nemotron-3-super-120b-a12b`, 10 LLM calls, 58.0 s
- Markovian: 8 steps, 3563 prompt tokens vs ~13392 for a full-transcript loop (73.4% saved)
- critic rounds: 0; H-MEM memories written: 0
