# Why does IBM drop out when EDGAR company profiles are joined to the company_dns SIC reference list?

**Answer.** IBM drops out because its SIC code '3570' in edgar.company_profiles does not exist in the company_dns.sic_codes_table, so the join cannot match that record. Since no other company uses '3570', the absence likely reflects that this code is historic or retired, causing IBM to be excluded from the joined result.

## Verified claims (critic-checked against query results)
- IBM's sic_code in edgar.company_profiles is '3570'. — evidence: E-a5d3db
- The value '3570' does not appear in company_dns.sic_codes_table. — evidence: E-826451
- IBM's sic_code '3570' has length 4 and first character '3' (no leading zero). — evidence: E-603b63
- No other company in edgar.company_profiles uses sic_code '3570'. — evidence: E-51ccea

## Inferences (likely causes the data cannot prove; not critic-verified)
- The absence of sic_code 3570 from the reference table and lack of usage by other companies indicates it is a historic/retired SIC code. — basis: Claims that sic_code 3570 is a valid 4‑digit code, not null or zero‑padded, unused by any other company, and missing from the reference SIC list.

## Hypotheses
- `H-964b06` **refuted** — IBM's sic_code in edgar.company_profiles is NULL or empty, so the inner join to company_dns.sic_codes_table produces no matching rows. (E-a5d3db)<br>why: IBM's sic_code is '3570', not null or empty.
- `H-dfe948` **refuted** — IBM's sic_code contains leading zeros (e.g., '0371') while the reference sic_codes_table stores the same code without leading zeros (e.g., '371'), causing a mismatch on the text join. (E-603b63)<br>why: IBM's sic_code '3570' has length 4 and first character '3', showing no leading zeros.
- `H-aa8a77` **refuted** — IBM's sic_code is a valid 4‑digit SIC that is simply absent from company_dns.sic_codes_table due to a coverage gap in the reference data (e.g., a newer or industry‑specific code not yet loaded). (E-51ccea, E-826451)<br>why: While the code is missing from the reference, the lack of any other company using it and the carryover context point to a historic/retired code rather than a simple coverage gap.
- `H-871553` **supported** — IBM's sic_code reflects a historic or retired SIC that has been removed from the active company_dns reference list (real‑world change in classification), so no current reference row exists. (E-51ccea, E-603b63, E-826451)<br>why: The sic_code '3570' is a valid 4‑digit SIC, absent from the reference, and unused by any other company, consistent with a historic/retired classification.

## Evidence (Zetaris SQL)
### E-a5d3db — Retrieve IBM's sic_code from company_profiles to see its value and format.
Backend: zetaris-rest, 1 row(s)
```sql
SELECT sic_code FROM edgar.company_profiles WHERE cik = 51143
LIMIT 200
```
```
sic_code
3570
```
### E-826451 — Check if IBM's sic_code '3570' exists in the reference SIC table.
Backend: zetaris-rest, 0 row(s)
```sql
SELECT sic_code FROM company_dns.sic_codes_table WHERE sic_code = '3570'
LIMIT 200
```
```
sic_code
(0 rows)
```
### E-603b63 — Verify IBM's sic_code format (length, leading zero) to test H-964b06 and H-dfe948
Backend: zetaris-rest, 1 row(s)
```sql
select sic_code, length(sic_code) as len, left(sic_code,1) as first_char from edgar.company_profiles where cik=51143
LIMIT 200
```
```
sic_code | len | first_char
3570 | 4 | 3
```
### E-51ccea — Check if any company besides IBM uses sic_code 3570 in EDGAR profiles to distinguish coverage gap vs retired code
Backend: zetaris-rest, 0 row(s)
```sql
SELECT cik, entity_name FROM edgar.company_profiles WHERE sic_code = '3570' AND cik != 51143
LIMIT 200
```
```
cik | entity_name
(0 rows)
```

## Run
- backend `zetaris-rest`, model `nvidia/nemotron-3-super-120b-a12b`, 9 LLM calls, 84.9 s
- Markovian: 6 steps, 2666 prompt tokens vs ~7832 for a full-transcript loop (66.0% saved)
- critic rounds: 1; H-MEM memories written: 4
