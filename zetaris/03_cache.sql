-- Cache the SEC REST tables inside Zetaris so queries do not re-fetch from data.sec.gov every time
-- (as recipe 12 does for company_dns). Added after a DNS outage made live SEC calls fail mid-eval.

CACHE TABLE sec_data.xw_apple_rev_facts;

CACHE TABLE sec_data.xw_apple_rfcc_facts;

CACHE TABLE sec_data.xw_ibm_rev_facts;

CACHE TABLE sec_data.xw_tesla_rev_facts;

CACHE TABLE sec_data.xw_tesla_rfcc_facts;

CACHE TABLE sec_data.xw_apple_submissions;

CACHE TABLE sec_data.xw_ibm_submissions;

CACHE TABLE sec_data.xw_tesla_submissions;
