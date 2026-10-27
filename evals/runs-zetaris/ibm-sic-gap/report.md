# Why does IBM drop out when EDGAR company profiles are joined to the company_dns SIC reference list?

**Answer.** IBM drops out because its SIC code '3570' in edgar.company_profiles has no matching row in company_dns.sic_codes_table, so an inner join on sic_code finds no match for IBM. Since the reference table lacks that sic_code value, IBM’s record is excluded from the join result. This absence likely reflects a gap in the reference SIC list rather than any issue with IBM’s data.

## Verified claims (critic-checked against query results)
- IBM's SIC code in edgar.company_profiles is '3570'. — evidence: E-a5d3db
- The reference table company_dns.sic_codes_table contains no row with sic_code = '3570'. — evidence: E-826451
- IBM has exactly one SIC code row in edgar.company_profiles. — evidence: E-99c342
- Sample sic_code values in the reference table are four‑character strings without zero padding (e.g., '3011', '3021'). — evidence: E-ac3c81

## Inferences (likely causes the data cannot prove; not critic-verified)
- The join drops IBM because the reference SIC list is incomplete for IBM's industry classification. — basis: Claims that IBM's SIC is '3570' and absent from the reference table.
- This absence likely reflects a reference‑data gap rather than any formatting or duplication issue in IBM's data. — basis: Claims showing IBM's SIC is clean, singular, and matches no reference entry.

## Hypotheses
- `H-adec46` **refuted** — IBM's SIC code in edgar.company_profiles contains leading or trailing whitespace, so it does not exactly match any sic_code in company_dns.sic_codes_table. (E-a5d3db, E-e22cb2)<br>why: IBM's sic_code '3570' shows no leading/trailing whitespace; length is 4 and character codes are digits.
- `H-7ce83a` **refuted** — IBM's SIC code is stored as a numeric value without leading zeros, whereas the reference table expects a zero‑padded 4‑character string (e.g., '0357' vs 357). (E-a5d3db, E-ac3c81)<br>why: IBM's sic_code is already a 4‑character string; reference sic_codes are also 4‑character strings without zero padding, so no numeric vs padded mismatch.
- `H-f7ff3b` **refuted** — IBM's SIC code is missing or NULL in edgar.company_profiles, causing the join to drop the row. (E-a5d3db)<br>why: IBM's sic_code is present and not NULL in edgar.company_profiles.
- `H-137f3b` **supported** — The company_dns.sic_codes_table lacks coverage for IBM's specific SIC code (e.g., a newer or industry‑specific code) due to a reference‑data gap. (E-826451, E-ac3c81)<br>why: The reference table lacks the exact sic_code '3570', confirming a coverage gap.
- `H-90a48c` **refuted** — IBM reports multiple SIC codes over time (different lines of business), but edgar.company_profiles stores only one (perhaps an outdated primary code) that does not match the current reference list, while the true activity spans several SICs present in the reference. (E-99c342)<br>why: IBM has only one SIC code row in company_profiles, so multiple historic codes are not stored there.

## Evidence (Zetaris SQL)
### E-a5d3db — Retrieve IBM's SIC code from EDGAR company profiles
Backend: zetaris-rest, 1 row(s)
```sql
SELECT sic_code FROM edgar.company_profiles WHERE cik = 51143
LIMIT 200
```
```
sic_code
3570
```
### E-826451 — Check if the reference table contains IBM's SIC code exactly as '3570'
Backend: zetaris-rest, 0 row(s)
```sql
SELECT sic_code FROM company_dns.sic_codes_table WHERE sic_code = '3570'
LIMIT 200
```
```
sic_code
(0 rows)
```
### E-e22cb2 — Examine IBM's SIC code value for hidden characters or length
Backend: zetaris-rest, 1 row(s)
```sql
select sic_code, length(sic_code) as len, ascii(substring(sic_code from 1 for 1)) as first_char_code, ascii(substring(sic_code from length(sic_code) for 1)) as last_char_code from edgar.company_profiles where cik = 51143
LIMIT 200
```
```
sic_code | len | first_char_code | last_char_code
3570 | 4 | 51 | 48
```
### E-ac3c81 — Inspect the format of sic_code values in the reference table, especially those starting with '3', to see if they are zero-padded or have varying lengths.
Backend: zetaris-rest, 20 row(s)
```sql
SELECT sic_code, LENGTH(sic_code) AS len FROM company_dns.sic_codes_table WHERE sic_code LIKE '3%' LIMIT 20
```
```
sic_code | len
3011 | 4
3021 | 4
3052 | 4
3053 | 4
3061 | 4
3069 | 4
3081 | 4
3082 | 4
3083 | 4
3084 | 4
3085 | 4
3086 | 4
... (8 more rows, 20 total)
```
### E-99c342 — Check if IBM has multiple SIC code rows in company_profiles
Backend: zetaris-rest, 1 row(s)
```sql
SELECT COUNT(*) AS rows FROM edgar.company_profiles WHERE cik = 51143
LIMIT 200
```
```
rows
1
```

## Run
- backend `zetaris-rest`, model `nvidia/nemotron-3-super-120b-a12b`, 13 LLM calls, 93.7 s
- Markovian: 8 steps, 4433 prompt tokens vs ~16385 for a full-transcript loop (72.9% saved)
- critic rounds: 3; H-MEM memories written: 4
