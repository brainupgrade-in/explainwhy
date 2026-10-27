"""Data harness: read-only SQL over Zetaris (live) or a local SQLite mirror (SAMPLE_MODE).

Both backends expose the same qualified table names, so the agent's SQL is the
same either way. The Zetaris views are created by zetaris/01_create.sql.
"""
import csv
import json
import re
import sqlite3
import uuid
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from . import config

CATALOG = """\
edgar.revenue_facts -- SEC EDGAR XBRL company-concept facts, one row per reported value.
  Source: data.sec.gov companyconcept API, two us-gaap concepts: 'Revenues' and
  'RevenueFromContractWithCustomerExcludingAssessedTax'. Companies (filter on cik, not names):
  Apple Inc. = 320193, INTERNATIONAL BUSINESS MACHINES CORP = 51143, Tesla, Inc. = 1318605.
  Columns: cik (int), entity_name, concept, period_start, period_end, value_usd (int),
  accession_number, fiscal_year (int), fiscal_period ('FY','Q1'..'Q4'), period_frame
  (e.g. 'CY2019', 'CY2019Q1', null when duplicated), form_type ('10-K','10-Q',...), filed_date.
  Note: the same period is often reported again in later filings; one fact per filing.

edgar.company_profiles -- SEC EDGAR submissions API, one row per company.
  Columns: cik (int), entity_name, sic_code (text), sic_description_edgar.

company_dns.sic_codes_table -- SIC reference list from the company_dns API (separate source).
  Columns: sic_code (text), description, division, division_desc, major_group,
  major_group_desc, industry_group, industry_group_desc.
"""

FORBIDDEN = re.compile(r"\b(insert|update|delete|drop|create|alter|grant|revoke|truncate|merge|call|attach|pragma)\b", re.I)


class SQLRejected(ValueError):
    pass


def guard(sql: str, limit: int = 200) -> str:
    """Single read-only SELECT, with a row cap. Rejects anything else."""
    sql = sql.strip().rstrip(";").strip()
    if ";" in sql:
        raise SQLRejected("one statement only")
    if not re.match(r"(?is)^(select|with)\b", sql):
        raise SQLRejected("only SELECT / WITH queries are allowed")
    if FORBIDDEN.search(sql):
        raise SQLRejected("query contains a write or admin keyword")
    if not re.search(r"(?i)\blimit\s+\d+\s*$", sql):
        sql = f"{sql}\nLIMIT {limit}"
    return sql


class LocalSource:
    name = "local-sqlite (SAMPLE_MODE mirror of the Zetaris views)"

    TABLES = {
        ("edgar", "revenue_facts"): ("edgar_revenue_facts.csv", {"cik", "value_usd", "fiscal_year"}),
        ("edgar", "company_profiles"): ("edgar_company_profiles.csv", {"cik"}),
        ("company_dns", "sic_codes_table"): ("company_dns_sic_codes.csv", set()),
    }

    def __init__(self):
        self.db = sqlite3.connect(":memory:", check_same_thread=False)
        for schema in {s for s, _ in self.TABLES}:
            self.db.execute(f"ATTACH ':memory:' AS {schema}")
        for (schema, table), (fname, ints) in self.TABLES.items():
            with open(config.DATA_DIR / fname, newline="") as f:
                rows = list(csv.DictReader(f))
            cols = list(rows[0])
            decl = ", ".join(f"{c} {'INTEGER' if c in ints else 'TEXT'}" for c in cols)
            self.db.execute(f"CREATE TABLE {schema}.{table} ({decl})")
            self.db.executemany(f"INSERT INTO {schema}.{table} VALUES ({', '.join('?' * len(cols))})",
                                [[(r[c] or None) for c in cols] for r in rows])

    def query(self, sql: str) -> tuple[list[str], list[list]]:
        cur = self.db.execute(sql)
        return [d[0] for d in cur.description], [list(r) for r in cur.fetchall()]


class ZetarisSource:
    """Zetaris Lightning SQL over the REST API (POST /sql-editor/sqls/run)."""
    name = "zetaris-rest"

    def __init__(self):
        self.base = config.env("ZETARIS_REST_URL", "http://localhost:8888/api/v1.0").rstrip("/")
        self.org = config.env("ZETARIS_ORG_ID", "1")
        self._key = config.env("ZETARIS_API_KEY")
        if not self._key:
            raise ConnectionError("ZETARIS_API_KEY not set")

    def query(self, sql: str) -> tuple[list[str], list[list]]:
        body = {"queryId": str(uuid.uuid4()), "sql": sql, "source": "SqlEditor", "limit": 200}
        req = Request(f"{self.base}/sql-editor/sqls/run", data=json.dumps(body).encode(), method="POST",
                      headers={"Authorization": f"Bearer {self._key}", "X-Org-ID": self.org,
                               "X-Request-ID": str(uuid.uuid4()), "Content-Type": "application/json"})
        try:
            with urlopen(req, timeout=120) as r:
                out = json.loads(r.read() or b"null")
        except HTTPError as e:
            raise RuntimeError(f"Zetaris HTTP {e.code}: {e.read().decode(errors='replace')[:300]}") from e
        except (URLError, OSError) as e:
            raise ConnectionError(f"cannot reach Zetaris at {self.base}: {e}") from e
        return normalize_result(out)


def normalize_result(out) -> tuple[list[str], list[list]]:
    """Zetaris returns {data: rows} where rows are lists or dicts; columns may come separately."""
    data = out.get("data") if isinstance(out, dict) else out
    cols = (out.get("columns") or out.get("schema") or []) if isinstance(out, dict) else []
    if isinstance(data, dict):
        cols = data.get("columns") or cols
        data = data.get("rows") or data.get("data") or []
    rows = data or []
    if rows and isinstance(rows[0], dict):
        cols = list(rows[0])
        rows = [[r.get(c) for c in cols] for r in rows]
    cols = [c.get("name", str(c)) if isinstance(c, dict) else str(c) for c in cols]
    if not cols and rows:
        cols = [f"col{i}" for i in range(len(rows[0]))]
    return cols, [list(r) for r in rows]


def open_source(prefer_zetaris: bool) -> tuple[object, str]:
    """Zetaris if configured and reachable, else the local mirror. Returns (source, note)."""
    if prefer_zetaris and not config.SAMPLE_MODE:
        try:
            z = ZetarisSource()
            z.query("SELECT 1")
            return z, "connected to Zetaris"
        except Exception as e:  # unreachable or not configured: fall back, say so
            return LocalSource(), f"Zetaris unavailable ({e}); using local mirror"
    return LocalSource(), "SAMPLE_MODE: local mirror" if config.SAMPLE_MODE else "local mirror (Zetaris not requested)"
