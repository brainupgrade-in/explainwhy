"""Run the Zetaris showcase queries against the live instance and write zetaris/live_results.md.

Exploratory queries per source, queries showing the USL is active, and the data-quality results.

    python3 zetaris/showcase.py
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from explainwhy.data import ZetarisSource  # noqa: E402

USL = "lightning.metastore.explainwhy.explainwhy_usl"
SECTIONS = [
    ("Source 1 — SEC XBRL revenue facts (`edgar.revenue_facts`)", [
        "SELECT concept, COUNT(*) AS facts, MIN(fiscal_year) AS first_fy, MAX(fiscal_year) AS last_fy FROM edgar.revenue_facts GROUP BY concept",
        "SELECT entity_name, concept, MAX(fiscal_year) AS last_fy, COUNT(*) AS facts FROM edgar.revenue_facts GROUP BY entity_name, concept ORDER BY entity_name, concept",
        "SELECT form_type, COUNT(*) AS facts FROM edgar.revenue_facts GROUP BY form_type ORDER BY facts DESC",
    ]),
    ("Source 2 — SEC submissions (`edgar.company_profiles`)", [
        "SELECT cik, entity_name, sic_code, sic_description_edgar FROM edgar.company_profiles",
        "SELECT sic_code, COUNT(*) AS companies FROM edgar.company_profiles GROUP BY sic_code",
    ]),
    ("Source 3 — company_dns SIC list (`company_dns.sic_codes_table`)", [
        "SELECT COUNT(*) AS codes, MIN(sic_code) AS first_code, MAX(sic_code) AS last_code FROM company_dns.sic_codes_table",
        "SELECT sic_code, description FROM company_dns.sic_codes_table WHERE sic_code BETWEEN '3570' AND '3579' ORDER BY sic_code",
    ]),
    ("The USL is active (`explainwhy_usl`)", [
        f"SELECT COUNT(*) AS rows FROM {USL}.sic_code",
        f"SELECT c.entity_name, c.sic, s.description AS sic_reference FROM {USL}.company c LEFT JOIN {USL}.sic_code s ON c.sic = s.sic_code ORDER BY c.entity_name",
        f"SELECT c.entity_name, f.concept, COUNT(*) AS facts, MAX(f.fiscal_year) AS last_fy FROM {USL}.revenue_fact f JOIN {USL}.company c ON f.cik = c.cik GROUP BY c.entity_name, f.concept ORDER BY c.entity_name, f.concept",
    ]),
    ("Data quality: the USL's FK rule executed (`RUN DQ`, then `SHOW DQ ALL INVALID`)", [
        f"SHOW DQ ALL INVALID TABLE {USL}.company",
        f"SHOW DQ ALL INVALID TABLE {USL}.revenue_fact",
    ]),
]


def table(cols, rows, limit=20) -> str:
    if not rows:
        return "_(0 rows)_"
    out = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    out += ["| " + " | ".join("" if v is None else str(v).replace("|", "\\|")[:80] for v in r) + " |" for r in rows[:limit]]
    if len(rows) > limit:
        out.append(f"\n_{len(rows) - limit} more rows_")
    return "\n".join(out)


def main() -> None:
    z = ZetarisSource()
    md = ["# Zetaris live results", "",
          f"Run {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())} against a local Zetaris instance "
          f"(Docker, REST API `{z.base}`) by `zetaris/showcase.py`.", ""]
    for title, queries in SECTIONS:
        md += [f"## {title}", ""]
        for q in queries:
            t0 = time.time()
            try:
                cols, rows = z.query(q)
                result = table(cols, rows)
            except Exception as e:  # show the failure rather than hide it
                result = f"**Error:** `{str(e)[:300]}`"
            md += ["```sql", q, "```", result, f"\n_{time.time() - t0:.1f} s_", ""]
            print(f"{title[:30]:30} {time.time() - t0:5.1f}s {q[:70]}")
    out = Path(__file__).with_name("live_results.md")
    out.write_text("\n".join(md) + "\n")
    print("wrote", out)


if __name__ == "__main__":
    main()
