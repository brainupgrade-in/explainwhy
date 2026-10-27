-- =============================================================================
-- ExplainWhy Unified Semantic Layer (USL): one model over all three sources.
-- Written for this hackathon, 2026-10-27. Pattern follows zetaris/getting-started
-- open_data/usl/sql/02_sic_edgar_usl_create.sql, extended to a third, fact-level table.
--
--   sic_code       <- company_dns REST source (company_dns.sic_codes_raw, recipe 12)
--   company        <- SEC submissions REST source (sec_data.xw_*_submissions, 01_create.sql)
--                     FK sic -> sic_code
--   revenue_fact   <- SEC XBRL companyconcept REST source (sec_data.xw_*_facts, 01_create.sql)
--                     FK cik -> company
--
-- The FK rules Zetaris generates are the data quality rules: RUN DQ flags every company whose
-- SIC code is missing from the reference list (IBM, 3570) -- the same anomaly ExplainWhy explains
-- from first principles in sample 2. Run after 01_create.sql, with the getting-started runner:
--   python3 scripts/run_sql.py <path>/zetaris/02_usl.sql --dry-run
--   python3 scripts/run_sql.py <path>/zetaris/02_usl.sql --skip-exists
-- COMPILE USL is one statement; run_sql.py keeps it whole.
-- =============================================================================

CREATE NAMESPACE IF NOT EXISTS lightning.metastore;

CREATE NAMESPACE IF NOT EXISTS lightning.metastore.explainwhy;

COMPILE USL IF NOT EXISTS explainwhy_usl DEPLOY NAMESPACE lightning.metastore.explainwhy DDL
CREATE TABLE sic_code (
    sic_code varchar(4) NOT NULL PRIMARY KEY,
    description varchar(200),
    division varchar(1),
    division_desc varchar(200),
    major_group varchar(2),
    major_group_desc varchar(200),
    industry_group varchar(3),
    industry_group_desc varchar(200)
);
CREATE TABLE company (
    cik varchar(10) NOT NULL PRIMARY KEY,
    entity_name varchar(200) NOT NULL,
    sic varchar(4) NOT NULL FOREIGN KEY REFERENCES sic_code(sic_code),
    sic_description_edgar varchar(200)
);
CREATE TABLE revenue_fact (
    fact_id varchar(200) NOT NULL PRIMARY KEY,
    cik varchar(10) NOT NULL FOREIGN KEY REFERENCES company(cik),
    concept varchar(100) NOT NULL,
    period_start varchar(10),
    period_end varchar(10) NOT NULL,
    value_usd bigint,
    accession_number varchar(30) NOT NULL,
    fiscal_year int,
    fiscal_period varchar(4),
    period_frame varchar(12),
    form_type varchar(12),
    filed_date varchar(10)
);

UPDATE USL lightning.metastore.explainwhy.explainwhy_usl SET DESCRIPTION 'ExplainWhy semantic layer - SEC XBRL revenue facts, SEC company profiles and the company_dns SIC hierarchy in one FK-linked model.';

UPDATE USL lightning.metastore.explainwhy.explainwhy_usl.revenue_fact SET TABLE DESCRIPTION 'One row per reported revenue value - us-gaap Revenues and RevenueFromContractWithCustomerExcludingAssessedTax, Apple, IBM and Tesla.';

ACTIVATE USL TABLE lightning.metastore.explainwhy.explainwhy_usl.sic_code AS
SELECT
    sic_code,
    sic_val.description AS description,
    sic_val.division AS division,
    sic_val.division_desc AS division_desc,
    sic_val.major_group AS major_group,
    sic_val.major_group_desc AS major_group_desc,
    sic_val.industry_group AS industry_group,
    sic_val.industry_group_desc AS industry_group_desc
FROM company_dns.sic_codes_raw
LATERAL VIEW explode(
    from_json(to_json(data.sics), 'map<string, struct<description:string, division:string, division_desc:string, major_group:string, major_group_desc:string, industry_group:string, industry_group_desc:string>>')
) AS sic_code, sic_val;

ACTIVATE USL TABLE lightning.metastore.explainwhy.explainwhy_usl.company AS
SELECT CAST(cik AS STRING) AS cik, entity_name, COALESCE(sic_code, '') AS sic, sic_description_edgar
FROM edgar.company_profiles;

ACTIVATE USL TABLE lightning.metastore.explainwhy.explainwhy_usl.revenue_fact AS
SELECT
    concat_ws('|', accession_number, concept, COALESCE(period_start, ''), period_end) AS fact_id,
    CAST(cik AS STRING) AS cik, concept, period_start, period_end, value_usd, accession_number,
    fiscal_year, fiscal_period, period_frame, form_type, filed_date
FROM edgar.revenue_facts;

RUN DQ TABLE lightning.metastore.explainwhy.explainwhy_usl.company;

RUN DQ TABLE lightning.metastore.explainwhy.explainwhy_usl.revenue_fact;

-- Show the quality state (run in the SQL editor or with run_sql.py):
-- SHOW DQ ALL INVALID TABLE lightning.metastore.explainwhy.explainwhy_usl.company
-- SELECT COUNT(*) FROM lightning.metastore.explainwhy.explainwhy_usl.revenue_fact
-- SELECT c.entity_name, c.sic, s.description FROM lightning.metastore.explainwhy.explainwhy_usl.company c
--   LEFT JOIN lightning.metastore.explainwhy.explainwhy_usl.sic_code s ON c.sic = s.sic_code
