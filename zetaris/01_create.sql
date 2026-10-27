-- =============================================================================
-- ExplainWhy: Zetaris objects the agent queries (written for this hackathon, 2026-10-27).
-- Pattern follows zetaris/getting-started open_data/rest_apis recipes 01, 11 and 12.
--
-- Builds three views the agent's catalog names:
--   edgar.revenue_facts           union of SEC XBRL companyconcept facts, 2 concepts x 3 companies
--   edgar.company_profiles        SEC submissions: cik, name, sic, sicDescription
--   company_dns.sic_codes_table   SIC reference list (from the official recipe 12; run it first:
--                                 python3 scripts/onboard.py run company_dns  in zetaris/getting-started)
--
-- Run (from a zetaris/getting-started checkout, with its .env.local set):
--   python3 scripts/run_sql.py /path/to/explainwhy/zetaris/01_create.sql --dry-run
--   python3 scripts/run_sql.py /path/to/explainwhy/zetaris/01_create.sql --skip-exists
-- The runner replaces the user-agent placeholder with ZETARIS_USER_AGENT (SEC requires a contact).
-- If SEC_DATA or the edgar container already exist from recipe 01/11, --skip-exists skips them.
-- =============================================================================

CREATE LIGHTNING DATABASE SEC_DATA DESCRIBE BY "SEC EDGAR XBRL company facts REST source";

CREATE SCHEMASTORE CONTAINER edgar;

-- apple Revenues
CREATE LIGHTNING REST TABLE xw_apple_rev_facts FROM SEC_DATA REQUEST(
    endpoint "https://data.sec.gov/api/xbrl/companyconcept/CIK0000320193/us-gaap/Revenues.json",
    method "get",
    response_type "json",
    http_encoding "URLENCODED"
) HEADER (
    user-agent "YOUR_APP_NAME YOUR_CONTACT_EMAIL"
) BODY ();

-- apple RevenueFromContractWithCustomerExcludingAssessedTax
CREATE LIGHTNING REST TABLE xw_apple_rfcc_facts FROM SEC_DATA REQUEST(
    endpoint "https://data.sec.gov/api/xbrl/companyconcept/CIK0000320193/us-gaap/RevenueFromContractWithCustomerExcludingAssessedTax.json",
    method "get",
    response_type "json",
    http_encoding "URLENCODED"
) HEADER (
    user-agent "YOUR_APP_NAME YOUR_CONTACT_EMAIL"
) BODY ();

-- ibm Revenues
CREATE LIGHTNING REST TABLE xw_ibm_rev_facts FROM SEC_DATA REQUEST(
    endpoint "https://data.sec.gov/api/xbrl/companyconcept/CIK0000051143/us-gaap/Revenues.json",
    method "get",
    response_type "json",
    http_encoding "URLENCODED"
) HEADER (
    user-agent "YOUR_APP_NAME YOUR_CONTACT_EMAIL"
) BODY ();

-- tesla Revenues
CREATE LIGHTNING REST TABLE xw_tesla_rev_facts FROM SEC_DATA REQUEST(
    endpoint "https://data.sec.gov/api/xbrl/companyconcept/CIK0001318605/us-gaap/Revenues.json",
    method "get",
    response_type "json",
    http_encoding "URLENCODED"
) HEADER (
    user-agent "YOUR_APP_NAME YOUR_CONTACT_EMAIL"
) BODY ();

-- tesla RevenueFromContractWithCustomerExcludingAssessedTax
CREATE LIGHTNING REST TABLE xw_tesla_rfcc_facts FROM SEC_DATA REQUEST(
    endpoint "https://data.sec.gov/api/xbrl/companyconcept/CIK0001318605/us-gaap/RevenueFromContractWithCustomerExcludingAssessedTax.json",
    method "get",
    response_type "json",
    http_encoding "URLENCODED"
) HEADER (
    user-agent "YOUR_APP_NAME YOUR_CONTACT_EMAIL"
) BODY ();

CREATE LIGHTNING REST TABLE xw_apple_submissions FROM SEC_DATA REQUEST(
    endpoint "https://data.sec.gov/submissions/CIK0000320193.json",
    method "get",
    response_type "json",
    http_encoding "URLENCODED"
) HEADER (
    user-agent "YOUR_APP_NAME YOUR_CONTACT_EMAIL"
) BODY ();

CREATE LIGHTNING REST TABLE xw_ibm_submissions FROM SEC_DATA REQUEST(
    endpoint "https://data.sec.gov/submissions/CIK0000051143.json",
    method "get",
    response_type "json",
    http_encoding "URLENCODED"
) HEADER (
    user-agent "YOUR_APP_NAME YOUR_CONTACT_EMAIL"
) BODY ();

CREATE LIGHTNING REST TABLE xw_tesla_submissions FROM SEC_DATA REQUEST(
    endpoint "https://data.sec.gov/submissions/CIK0001318605.json",
    method "get",
    response_type "json",
    http_encoding "URLENCODED"
) HEADER (
    user-agent "YOUR_APP_NAME YOUR_CONTACT_EMAIL"
) BODY ();

CREATE SCHEMASTORE VIEW revenue_facts WITH CONTAINER edgar AS
SELECT CAST(cik AS INT) AS cik, `entityName` AS entity_name, tag AS concept,
    fact.`start` AS period_start, fact.`end` AS period_end, CAST(fact.val AS BIGINT) AS value_usd,
    fact.accn AS accession_number, CAST(fact.fy AS INT) AS fiscal_year, fact.fp AS fiscal_period,
    fact.frame AS period_frame, fact.form AS form_type, fact.filed AS filed_date
FROM sec_data.xw_apple_rev_facts LATERAL VIEW explode(units.USD) AS fact
UNION ALL
SELECT CAST(cik AS INT) AS cik, `entityName` AS entity_name, tag AS concept,
    fact.`start` AS period_start, fact.`end` AS period_end, CAST(fact.val AS BIGINT) AS value_usd,
    fact.accn AS accession_number, CAST(fact.fy AS INT) AS fiscal_year, fact.fp AS fiscal_period,
    fact.frame AS period_frame, fact.form AS form_type, fact.filed AS filed_date
FROM sec_data.xw_apple_rfcc_facts LATERAL VIEW explode(units.USD) AS fact
UNION ALL
SELECT CAST(cik AS INT) AS cik, `entityName` AS entity_name, tag AS concept,
    fact.`start` AS period_start, fact.`end` AS period_end, CAST(fact.val AS BIGINT) AS value_usd,
    fact.accn AS accession_number, CAST(fact.fy AS INT) AS fiscal_year, fact.fp AS fiscal_period,
    fact.frame AS period_frame, fact.form AS form_type, fact.filed AS filed_date
FROM sec_data.xw_ibm_rev_facts LATERAL VIEW explode(units.USD) AS fact
UNION ALL
SELECT CAST(cik AS INT) AS cik, `entityName` AS entity_name, tag AS concept,
    fact.`start` AS period_start, fact.`end` AS period_end, CAST(fact.val AS BIGINT) AS value_usd,
    fact.accn AS accession_number, CAST(fact.fy AS INT) AS fiscal_year, fact.fp AS fiscal_period,
    fact.frame AS period_frame, fact.form AS form_type, fact.filed AS filed_date
FROM sec_data.xw_tesla_rev_facts LATERAL VIEW explode(units.USD) AS fact
UNION ALL
SELECT CAST(cik AS INT) AS cik, `entityName` AS entity_name, tag AS concept,
    fact.`start` AS period_start, fact.`end` AS period_end, CAST(fact.val AS BIGINT) AS value_usd,
    fact.accn AS accession_number, CAST(fact.fy AS INT) AS fiscal_year, fact.fp AS fiscal_period,
    fact.frame AS period_frame, fact.form AS form_type, fact.filed AS filed_date
FROM sec_data.xw_tesla_rfcc_facts LATERAL VIEW explode(units.USD) AS fact;

CREATE SCHEMASTORE VIEW company_profiles WITH CONTAINER edgar AS
SELECT CAST(cik AS INT) AS cik, name AS entity_name, sic AS sic_code, `sicDescription` AS sic_description_edgar
FROM sec_data.xw_apple_submissions
UNION ALL
SELECT CAST(cik AS INT) AS cik, name AS entity_name, sic AS sic_code, `sicDescription` AS sic_description_edgar
FROM sec_data.xw_ibm_submissions
UNION ALL
SELECT CAST(cik AS INT) AS cik, name AS entity_name, sic AS sic_code, `sicDescription` AS sic_description_edgar
FROM sec_data.xw_tesla_submissions;

-- Verify (compare with data/*.csv row counts: 698 facts, 3 profiles, 1005 SIC codes):
-- SELECT concept, COUNT(*) FROM edgar.revenue_facts GROUP BY concept
-- SELECT * FROM edgar.company_profiles
-- SELECT COUNT(*) FROM company_dns.sic_codes_table
