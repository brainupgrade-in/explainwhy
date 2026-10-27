# Sample data

Small snapshots of the three public sources the agent queries, fetched on 27 Oct 2026 by
`scripts/fetch_sample_data.py`. SAMPLE_MODE (and `--zetaris` when Zetaris is unreachable) loads them into an
in-memory SQLite database under the **same qualified names as the Zetaris views** built by
`zetaris/01_create.sql`, so the agent's SQL is identical in both modes.

| File | Zetaris view | Source | Rows |
|---|---|---|---|
| `edgar_revenue_facts.csv` | `edgar.revenue_facts` | SEC EDGAR XBRL companyconcept API (`data.sec.gov/api/xbrl/companyconcept/CIK…/us-gaap/{concept}.json`), concepts `Revenues` and `RevenueFromContractWithCustomerExcludingAssessedTax`, for Apple (320193), IBM (51143), Tesla (1318605). IBM has no facts under the second concept (404). | 698 |
| `edgar_company_profiles.csv` | `edgar.company_profiles` | SEC EDGAR submissions API (`data.sec.gov/submissions/CIK….json`): cik, name, sic, sicDescription | 3 |
| `company_dns_sic_codes.csv` | `company_dns.sic_codes_table` | company_dns V3 SIC list (`company-dns.mediumroast.io/V3.0/na/sic/code/%25`), the same source as Zetaris getting-started recipe 12 | 1,005 |

The disagreements between sources are real, not planted: Apple's `Revenues` facts stop at FY2018 while the
ASC 606 concept continues; IBM's SIC code 3570 is missing from the company_dns list; Tesla reports under
both revenue concepts from FY2018.

**Licensing.** SEC filings are filer-authored; the SEC asks for a declared User-Agent and at most 10
requests/s. The snapshot is kept small (three companies) for demo use, as the Zetaris recipe advises, and is
not a redistribution of the dataset. Refresh it with:

```bash
SEC_USER_AGENT="your_app you@example.com" python3 scripts/fetch_sample_data.py
```
