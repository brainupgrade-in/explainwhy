# Zetaris live results

Run 2026-10-27 18:27 UTC against a local Zetaris instance (Docker, REST API `http://localhost:8888/api/v1.0`) by `zetaris/showcase.py`.

## Source 1 — SEC XBRL revenue facts (`edgar.revenue_facts`)

```sql
SELECT concept, COUNT(*) AS facts, MIN(fiscal_year) AS first_fy, MAX(fiscal_year) AS last_fy FROM edgar.revenue_facts GROUP BY concept
```
| concept | facts | first_fy | last_fy |
|---|---|---|---|
| Revenues | 532 | 2009 | 2026 |
| RevenueFromContractWithCustomerExcludingAssessedTax | 166 | 2018 | 2026 |

_3.5 s_

```sql
SELECT entity_name, concept, MAX(fiscal_year) AS last_fy, COUNT(*) AS facts FROM edgar.revenue_facts GROUP BY entity_name, concept ORDER BY entity_name, concept
```
| entity_name | concept | last_fy | facts |
|---|---|---|---|
| Apple Inc. | RevenueFromContractWithCustomerExcludingAssessedTax | 2026 | 117 |
| Apple Inc. | Revenues | 2018 | 11 |
| INTERNATIONAL BUSINESS MACHINES CORPORATION | Revenues | 2026 | 235 |
| Tesla, Inc. | RevenueFromContractWithCustomerExcludingAssessedTax | 2026 | 49 |
| Tesla, Inc. | Revenues | 2026 | 286 |

_3.5 s_

```sql
SELECT form_type, COUNT(*) AS facts FROM edgar.revenue_facts GROUP BY form_type ORDER BY facts DESC
```
| form_type | facts |
|---|---|
| 10-Q | 458 |
| 10-K | 226 |
| 10-K/A | 11 |
| 8-K | 3 |

_3.7 s_

## Source 2 — SEC submissions (`edgar.company_profiles`)

```sql
SELECT cik, entity_name, sic_code, sic_description_edgar FROM edgar.company_profiles
```
| cik | entity_name | sic_code | sic_description_edgar |
|---|---|---|---|
| 320193 | Apple Inc. | 3571 | Electronic Computers |
| 51143 | INTERNATIONAL BUSINESS MACHINES CORP | 3570 | Computer & office Equipment |
| 1318605 | Tesla, Inc. | 3711 | Motor Vehicles & Passenger Car Bodies |

_3.4 s_

```sql
SELECT sic_code, COUNT(*) AS companies FROM edgar.company_profiles GROUP BY sic_code
```
| sic_code | companies |
|---|---|
| 3571 | 1 |
| 3570 | 1 |
| 3711 | 1 |

_2.5 s_

## Source 3 — company_dns SIC list (`company_dns.sic_codes_table`)

```sql
SELECT COUNT(*) AS codes, MIN(sic_code) AS first_code, MAX(sic_code) AS last_code FROM company_dns.sic_codes_table
```
| codes | first_code | last_code |
|---|---|---|
| 1005 | 0111 | 9999 |

_6.1 s_

```sql
SELECT sic_code, description FROM company_dns.sic_codes_table WHERE sic_code BETWEEN '3570' AND '3579' ORDER BY sic_code
```
| sic_code | description |
|---|---|
| 3571 | Electronic Computers |
| 3572 | Computer Storage Devices |
| 3575 | Computer Terminals |
| 3577 | Computer Peripheral Equipment, Not Elsewhere Classified |
| 3578 | Calculating and Accounting Machines, Except Electronic Computers |
| 3579 | Office Machines, Not Elsewhere Classified |

_4.5 s_

## The USL is active (`explainwhy_usl`)

```sql
SELECT COUNT(*) AS rows FROM lightning.metastore.explainwhy.explainwhy_usl.sic_code
```
| rows |
|---|
| 1005 |

_2.6 s_

```sql
SELECT c.entity_name, c.sic, s.description AS sic_reference FROM lightning.metastore.explainwhy.explainwhy_usl.company c LEFT JOIN lightning.metastore.explainwhy.explainwhy_usl.sic_code s ON c.sic = s.sic_code ORDER BY c.entity_name
```
| entity_name | sic | sic_reference |
|---|---|---|
| Apple Inc. | 3571 | Electronic Computers |
| INTERNATIONAL BUSINESS MACHINES CORP | 3570 |  |
| Tesla, Inc. | 3711 | Motor Vehicles and Passenger Car Bodies |

_9.8 s_

```sql
SELECT c.entity_name, f.concept, COUNT(*) AS facts, MAX(f.fiscal_year) AS last_fy FROM lightning.metastore.explainwhy.explainwhy_usl.revenue_fact f JOIN lightning.metastore.explainwhy.explainwhy_usl.company c ON f.cik = c.cik GROUP BY c.entity_name, f.concept ORDER BY c.entity_name, f.concept
```
| entity_name | concept | facts | last_fy |
|---|---|---|---|
| Apple Inc. | RevenueFromContractWithCustomerExcludingAssessedTax | 117 | 2026 |
| Apple Inc. | Revenues | 11 | 2018 |
| INTERNATIONAL BUSINESS MACHINES CORP | Revenues | 235 | 2026 |
| Tesla, Inc. | RevenueFromContractWithCustomerExcludingAssessedTax | 49 | 2026 |
| Tesla, Inc. | Revenues | 286 | 2026 |

_7.8 s_

## Data quality: the USL's FK rule executed (`RUN DQ`, then `SHOW DQ ALL INVALID`)

```sql
SHOW DQ ALL INVALID TABLE lightning.metastore.explainwhy.explainwhy_usl.company
```
| records |
|---|
| {"cik":"51143","entity_name":"INTERNATIONAL BUSINESS MACHINES CORP","sic":"3570" |

_21.9 s_

```sql
SHOW DQ ALL INVALID TABLE lightning.metastore.explainwhy.explainwhy_usl.revenue_fact
```
_(0 rows)_

_22.0 s_

