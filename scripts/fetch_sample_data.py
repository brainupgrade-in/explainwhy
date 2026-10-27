"""Fetch the small public snapshots in data/ that SAMPLE_MODE runs against.

Same endpoints the Zetaris REST tables in zetaris/01_create.sql read, so the
local mirror and the live Zetaris instance answer the same SQL.

    SEC_USER_AGENT="app_name you@example.com" python scripts/fetch_sample_data.py
"""
import csv
import json
import os
import sys
import time
from pathlib import Path
from urllib.request import Request, urlopen

DATA = Path(__file__).resolve().parent.parent / "data"
COMPANIES = {"apple": "0000320193", "ibm": "0000051143", "tesla": "0001318605"}
CONCEPTS = ["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax"]
FACT_COLS = ["cik", "entity_name", "concept", "period_start", "period_end", "value_usd",
             "accession_number", "fiscal_year", "fiscal_period", "period_frame", "form_type", "filed_date"]


def get(url: str, ua: str):
    time.sleep(0.2)  # SEC asks for <10 req/s
    with urlopen(Request(url, headers={"User-Agent": ua}), timeout=30) as r:
        return json.loads(r.read())


def main() -> None:
    ua = os.environ.get("SEC_USER_AGENT", "")
    if "@" not in ua:
        sys.exit("Set SEC_USER_AGENT to 'app_name contact@email' (SEC blocks anonymous clients).")
    DATA.mkdir(exist_ok=True)

    with open(DATA / "edgar_revenue_facts.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(FACT_COLS)
        for name, cik in COMPANIES.items():
            for concept in CONCEPTS:
                try:
                    doc = get(f"https://data.sec.gov/api/xbrl/companyconcept/CIK{cik}/us-gaap/{concept}.json", ua)
                except Exception as e:  # a company may never have used a tag
                    print(f"{name} {concept}: {e}")
                    continue
                for fact in doc["units"].get("USD", []):
                    w.writerow([int(doc["cik"]), doc["entityName"], doc["tag"], fact.get("start"), fact["end"],
                                fact["val"], fact["accn"], fact.get("fy"), fact.get("fp"), fact.get("frame"),
                                fact.get("form"), fact.get("filed")])
                print(f"{name} {concept}: {len(doc['units'].get('USD', []))} facts")

    with open(DATA / "edgar_company_profiles.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["cik", "entity_name", "sic_code", "sic_description_edgar"])
        for cik in COMPANIES.values():
            s = get(f"https://data.sec.gov/submissions/CIK{cik}.json", ua)
            w.writerow([int(s["cik"]), s["name"], s["sic"], s["sicDescription"]])

    sics = get("https://company-dns.mediumroast.io/V3.0/na/sic/code/%25", ua)["data"]["sics"]
    with open(DATA / "company_dns_sic_codes.csv", "w", newline="") as f:
        w = csv.writer(f)
        cols = ["description", "division", "division_desc", "major_group", "major_group_desc",
                "industry_group", "industry_group_desc"]
        w.writerow(["sic_code", *cols])
        for code, v in sorted(sics.items()):
            w.writerow([code, *(v.get(c) for c in cols)])
    print(f"company_dns: {len(sics)} SIC codes")


if __name__ == "__main__":
    main()
