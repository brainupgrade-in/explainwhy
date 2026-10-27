# Why does IBM drop out when EDGAR company profiles are joined to the company_dns SIC reference list?

**Answer.** IBM's EDGAR profile lists sic_code 3570, but the company_dns SIC reference table contains no entry for 3570 or any zero‑padded variant of that code, so the join fails to find a match and IBM is dropped from the result. This missing match likely indicates that SIC code 3570 is not present in the reference list, possibly because it is obsolete or has been removed.

## Verified claims (critic-checked against query results)
- IBM's sic_code in edgar.company_profiles is 3570. — evidence: E-c38e8f
- The reference table contains zero‑padded sic_code values such as '0111', '0112', '0115', '0116', '0119'. — evidence: E-cbb22d
- A search for sic_code '3570' and zero‑padded variants (e.g., '03570') returns zero rows in company_dns.sic_codes_table. — evidence: E-1943cf, E-be1c50
- IBM has exactly one row in edgar.company_profiles with a non‑null sic_code. — evidence: E-84b0e6, E-c38e8f
- IBM's sic_code value has no leading or trailing whitespace (length 4 before and after trim). — evidence: E-a9171e

## Inferences (likely causes the data cannot prove; not critic-verified)
- The SIC code 3570 is likely obsolete or no longer included in the company_dns reference list, which explains the failed join. — basis: Claims that IBM's sic_code is 3570 and that this value yields zero matches in the reference table despite correct formatting.

## Hypotheses
- `H-fff46c` **refuted** — IBM's sic_code in edgar.company_profiles contains leading or trailing whitespace (or invisible characters) that prevents an exact match with the sic_code values in company_dns.sic_codes_table. (E-a9171e)<br>why: Trimmed and raw lengths are equal, showing no whitespace.
- `H-c38b45` **refuted** — IBM's sic_code is stored as a numeric value without leading zeros (e.g., 3571) while the reference table expects a zero‑padded string format (e.g., '03571'), causing a mismatch on equality join. (E-be1c50)<br>why: Zero‑padded search for '03570' returns no rows.
- `H-c948f3` **supported** — The SIC code reported for IBM in edgar.company_profiles is obsolete or no longer present in the company_dns.sic_codes_table reference list (which may only contain currently active SICs). (E-1943cf)<br>why: SIC code 3570 is absent from the reference table, indicating obsolescence.
- `H-6b1937` **refuted** — IBM's company_profiles row has a NULL or empty sic_code (perhaps because IBM reports primarily via NAICS and the SIC field is blank), so the join produces no matches. (E-84b0e6, E-c38e8f)<br>why: Single row with non‑null sic_code; not NULL or empty.
- `H-8b80ef` **refuted** — IBM appears multiple times in edgar.company_profiles (e.g., due to successive filings) with differing sic_code values, and none of those values match any entry in the reference table, resulting in zero rows after the join. (E-84b0e6)<br>why: Only one company_profiles row for IBM; no differing sic_code values.

## Evidence (Zetaris SQL)
### E-c38e8f — Retrieve IBM's sic_code(s) from company_profiles to examine its value and possible duplicates.
Backend: local-sqlite (SAMPLE_MODE mirror of the Zetaris views), 1 row(s)
```sql
SELECT cik, entity_name, sic_code FROM edgar.company_profiles WHERE cik = 51143
LIMIT 200
```
```
cik | entity_name | sic_code
51143 | INTERNATIONAL BUSINESS MACHINES CORP | 3570
```
### E-84b0e6 — Determine if IBM has multiple rows in company_profiles that could cause mismatched sic_code values
Backend: local-sqlite (SAMPLE_MODE mirror of the Zetaris views), 1 row(s)
```sql
SELECT COUNT(*) AS cnt FROM edgar.company_profiles WHERE cik = 51143
LIMIT 200
```
```
cnt
1
```
### E-1943cf — Check if IBM's sic_code 3570 exists in the reference SIC table
Backend: local-sqlite (SAMPLE_MODE mirror of the Zetaris views), 0 row(s)
```sql
SELECT sic_code FROM company_dns.sic_codes_table WHERE sic_code = '3570' LIMIT 1
```
```
sic_code
(0 rows)
```
### E-a9171e — Check for leading/trailing whitespace in IBM's sic_code
Backend: local-sqlite (SAMPLE_MODE mirror of the Zetaris views), 1 row(s)
```sql
select sic_code, length(sic_code) as len_raw, length(trim(sic_code)) as len_trim, trim(sic_code) as sic_trimmed from edgar.company_profiles where cik = 51143
LIMIT 200
```
```
sic_code | len_raw | len_trim | sic_trimmed
3570 | 4 | 4 | 3570
```
### E-be1c50 — Check if IBM's SIC code 3570 appears in the reference table with any zero-padding
Backend: local-sqlite (SAMPLE_MODE mirror of the Zetaris views), 0 row(s)
```sql
SELECT sic_code FROM company_dns.sic_codes_table WHERE sic_code LIKE '3570' OR sic_code LIKE '03570' OR sic_code LIKE '003570' LIMIT 5
```
```
sic_code
(0 rows)
```
### E-cbb22d — Sample sic_code values in reference table to see its format and range
Backend: local-sqlite (SAMPLE_MODE mirror of the Zetaris views), 5 row(s)
```sql
SELECT sic_code FROM company_dns.sic_codes_table LIMIT 5
```
```
sic_code
0111
0112
0115
0116
0119
```

## Run
- backend `local-sqlite (SAMPLE_MODE mirror of the Zetaris views)`, model `nvidia/nemotron-3-super-120b-a12b`, 13 LLM calls, 70.6 s
- Markovian: 9 steps, 5290 prompt tokens vs ~19548 for a full-transcript loop (72.9% saved)
- critic rounds: 2; H-MEM memories written: 5
