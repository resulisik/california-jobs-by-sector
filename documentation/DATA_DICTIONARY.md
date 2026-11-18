# Data dictionary

Every table and column in `data/sectors.db`. This file is written by `src/make_data_dictionary.py` from the database itself; rebuild the database and run the script to update it.

23 tables, 255,573 rows in total.

## Contents

- **Part 1-2 · Jobs and stocks:** [`series`](#series), [`employment`](#employment), [`stock_prices`](#stock_prices), [`stock_sectors`](#stock_sectors)
- **Part 3 · The last three months (hand-collected):** [`jolts`](#jolts), [`layoffs_monthly`](#layoffs_monthly), [`layoffs_ytd`](#layoffs_ytd), [`layoff_totals`](#layoff_totals), [`layoff_reasons`](#layoff_reasons)
- **Part 4 · Careers and college majors (hand-collected):** [`occupation_outlook`](#occupation_outlook), [`majors`](#majors)
- **Indeed job postings index (Parts 1, 3 and 7):** [`postings_state`](#postings_state), [`postings_metro`](#postings_metro), [`postings_occ`](#postings_occ)
- **Part 6 · Live job postings snapshot:** [`postings`](#postings), [`posting_skills`](#posting_skills), [`posting_companies`](#posting_companies), [`posting_platforms`](#posting_platforms)
- **Part 7 · Year by year:** [`fred_series`](#fred_series), [`fred_monthly`](#fred_monthly), [`indeed_trackers`](#indeed_trackers), [`layoffs_annual`](#layoffs_annual)
- **Sources:** [`research_sources`](#research_sources)

## Part 1-2 · Jobs and stocks

### series

One row per BLS payroll series used in the project. **34 rows.** Source: src/config.py (SERIES).

| Column | Type | Example | Description |
|---|---|---|---|
| `series_id` | TEXT | CANA | FRED series ID, e.g. CANA (California total nonfarm) or PAYEMS (U.S.) |
| `name` | TEXT | Total nonfarm | Sector or industry name |
| `level` | TEXT | total | total, sector (one of 11 supersectors), industry or county |
| `seasonally_adjusted` | INTEGER | 1 | 1 if seasonally adjusted, 0 if not |
| `region` | TEXT | CA | CA or US |

### employment

Monthly payroll jobs for every series, long format. **2,767 rows.** Source: BLS Current Employment Statistics via FRED.

| Column | Type | Example | Description |
|---|---|---|---|
| `month` | TEXT | 2020-01-01 | First day of the month (YYYY-MM-01) |
| `series_id` | TEXT | CACONS | Links to series.series_id |
| `jobs_k` | REAL | 904.1 | Payroll jobs, thousands |

### stock_prices

Month-end adjusted close of the 11 SPDR sector funds and SPY (dividends reinvested). **852 rows.** Source: Yahoo Finance.

| Column | Type | Example | Description |
|---|---|---|---|
| `month` | TEXT | 2020-12-01 | Month (YYYY-MM-01) of the month-end price |
| `ticker` | TEXT | SPY | Fund ticker, e.g. XLK, XLV, SPY |
| `adj_close` | REAL | 346.303 | Adjusted close in dollars |

### stock_sectors

Maps each fund to its sector and the closest jobs sector. **12 rows.** Source: src/config.py (STOCKS); the jobs-sector match is my own judgment.

| Column | Type | Example | Description |
|---|---|---|---|
| `ticker` | TEXT | SPY | Fund ticker |
| `sector` | TEXT | S&P 500 (all sectors) | S&P 500 sector name |
| `jobs_sector` | TEXT | Total nonfarm | Closest BLS jobs sector (approximate) |

## Part 3 · The last three months (hand-collected)

### jolts

Job openings, hires and separations by industry for the last three months. **51 rows.** Source: BLS JOLTS release, Table A (hand-collected).

| Column | Type | Example | Description |
|---|---|---|---|
| `industry` | TEXT | Total | JOLTS industry name, or Total |
| `jobs_sector` | TEXT | Total nonfarm | Matching jobs sector |
| `level` | TEXT | total | total, sector or industry |
| `month` | TEXT | 2025-09-01 | Month (YYYY-MM-01) |
| `openings_k` | INTEGER | 7169 | Job openings on the last business day of the month, thousands, seasonally adjusted |
| `hires_k` | INTEGER | 5244 | Hires during the month, thousands |
| `separations_k` | INTEGER | 5161 | Total separations during the month, thousands |

### layoffs_monthly

Announced job cuts by industry, last three months. **69 rows.** Source: Challenger, Gray & Christmas monthly report (hand-collected).

| Column | Type | Example | Description |
|---|---|---|---|
| `industry` | TEXT | Aerospace/Defense | Challenger industry name |
| `jobs_sector` | TEXT | Manufacturing | Closest BLS jobs sector (approximate) |
| `month` | TEXT | 2026-08-01 | Month (YYYY-MM-01) |
| `cuts` | INTEGER | 149 | Announced job cuts |

### layoffs_ytd

Announced job cuts by industry, January to October 2026 against the same months of 2025. **23 rows.** Source: Challenger, Gray & Christmas (hand-collected).

| Column | Type | Example | Description |
|---|---|---|---|
| `industry` | TEXT | Aerospace/Defense | Challenger industry name; TOTAL is the sum |
| `jobs_sector` | TEXT | Manufacturing | Closest BLS jobs sector (approximate) |
| `ytd_2026` | INTEGER | 6518 | Announced cuts, January-October 2026 |
| `ytd_2025` | INTEGER | 3278 | Announced cuts, January-October 2025 |

### layoff_totals

Monthly totals of announced job cuts and hiring plans. **3 rows.** Source: Challenger, Gray & Christmas (hand-collected).

| Column | Type | Example | Description |
|---|---|---|---|
| `month` | TEXT | 2026-08-01 | Month (YYYY-MM-01) |
| `job_cuts` | INTEGER | 52881 | Announced job cuts |
| `hiring_plans` | INTEGER | 12325 | Announced hiring plans |

### layoff_reasons

Reasons employers gave for announced cuts. **8 rows.** Source: Challenger, Gray & Christmas (hand-collected).

| Column | Type | Example | Description |
|---|---|---|---|
| `reason` | TEXT | Market/Economic Conditions | Reason as Challenger reports it |
| `oct_2026` | INTEGER | 16407 | Cuts attributed to the reason in October 2026 |
| `ytd_2026` | INTEGER | 130531 | Cuts attributed to the reason, January-October 2026 |

## Part 4 · Careers and college majors (hand-collected)

### occupation_outlook

BLS employment projections 2025-2035 for 64 occupations. **64 rows.** Source: BLS Employment Projections, Table 1.10 (hand-collected).

| Column | Type | Example | Description |
|---|---|---|---|
| `code` | TEXT | 17-2112 | SOC occupation code |
| `title` | TEXT | Industrial engineers | Occupation title |
| `emp_2025_k` | REAL | 365.1 | Employment in 2025, thousands |
| `emp_2035_k` | REAL | 410.6 | Projected employment in 2035, thousands |
| `change_pct` | REAL | 12.4 | Projected change 2025-2035, percent |
| `openings_k` | REAL | 23.1 | Average yearly openings 2025-2035, thousands (growth plus replacement) |
| `median_wage` | REAL | 102440.0 | Median annual wage in dollars, as published with the projections |
| `education` | TEXT | Bachelor's degree | Typical education needed for entry |
| `field` | TEXT | Engineering | Field in this project: engineering, health care, finance, computer & data, film & media, or growth lists |
| `bachelors` | INTEGER | 1 | 1 if the typical entry education is a bachelor's degree |

### majors

Labor-market outcomes of recent college graduates by major. **74 rows.** Source: Federal Reserve Bank of New York, The Labor Market for Recent College Graduates (hand-collected).

| Column | Type | Example | Description |
|---|---|---|---|
| `major` | TEXT | Accounting | College major |
| `unemployment_pct` | REAL | 2.6 | Unemployment rate of recent graduates (ages 22-27), percent |
| `underemployment_pct` | REAL | 21.2 | Share of recent graduates in jobs that do not need a degree, percent |
| `wage_early` | INTEGER | 68000 | Median wage, early career (ages 22-27), dollars |
| `wage_mid` | INTEGER | 97000 | Median wage, mid-career (ages 35-45), dollars |
| `grad_share_pct` | REAL | 33.7 | Share with a graduate degree, percent |
| `major_group` | TEXT | Business & finance | One of eight major families (my own grouping, src/config.py) |

## Indeed job postings index (Parts 1, 3 and 7)

### postings_state

Indeed job postings index for the U.S. and California, daily. **4,956 rows.** Source: Indeed Hiring Lab job_postings_tracker (CC BY 4.0).

| Column | Type | Example | Description |
|---|---|---|---|
| `date` | TEXT | 2020-02-01 | Date (YYYY-MM-DD) |
| `state` | TEXT | CA | US or CA |
| `postings_index` | REAL | 100.0 | Postings index, seasonally adjusted, 7-day average; February 1, 2020 = 100 |

### postings_metro

Indeed job postings index for California metro areas, daily. **74,340 rows.** Source: Indeed Hiring Lab job_postings_tracker (CC BY 4.0).

| Column | Type | Example | Description |
|---|---|---|---|
| `date` | TEXT | 2020-02-01 | Date (YYYY-MM-DD) |
| `metro` | TEXT | Bakersfield, CA | Metro area (CBSA) name |
| `cbsa_code` | INTEGER | 12540 | Census CBSA code |
| `postings_index` | REAL | 100.0 | Postings index, 7-day average; February 1, 2020 = 100 |

### postings_occ

Indeed job postings index for 47 occupational categories, U.S., daily. **116,466 rows.** Source: Indeed Hiring Lab job_postings_tracker (CC BY 4.0).

| Column | Type | Example | Description |
|---|---|---|---|
| `date` | TEXT | 2020-02-01 | Date (YYYY-MM-DD) |
| `occupation` | TEXT | Accounting | Indeed occupational category, e.g. Data & Analytics |
| `postings_index` | REAL | 100.0 | Postings index, seasonally adjusted, 7-day average; February 1, 2020 = 100 |

## Part 6 · Live job postings snapshot

### postings

One row per open job posting in the 17 November 2026 snapshot, classified by src/postings.py. **39,215 rows.** Source: Public job APIs of Greenhouse, Ashby, Lever, SmartRecruiters; Remotive, Remote OK, Jobicy.

| Column | Type | Example | Description |
|---|---|---|---|
| `posting_id` | INTEGER | 1 | Row ID within the snapshot |
| `snapshot_date` | TEXT | 2026-11-17 | Date the snapshot was collected |
| `source` | TEXT | greenhouse | Platform: greenhouse, ashby, lever, smartrecruiters, remotive, remoteok or jobicy |
| `company` | TEXT | Figma | Employer name |
| `sector` | TEXT | A | Employer sector code (T, H, F, A, M, C, R) |
| `sector_name` | TEXT | Technology & software | Employer sector name, e.g. Health care & life sciences |
| `title` | TEXT | Distribution Partner Manager | Job title as posted |
| `title_norm` | TEXT | Distribution Partner Manager | Title with seniority words and qualifiers removed (for counting titles) |
| `family` | TEXT | AI & machine learning | Job family from keyword rules, e.g. Data & analytics |
| `eng_type` | TEXT | Other engineering | Kind of engineer for engineering titles (Software, Mechanical, ...); empty otherwise |
| `seniority` | TEXT | Mid or not stated | Internship, Entry level, Mid or not stated, or Senior & management |
| `is_data_analyst` | INTEGER | 0 | 1 if the title is an analyst title in data, business intelligence or reporting |
| `department` | TEXT | Business Development | Department or team as posted |
| `location` | TEXT | San Francisco, CA • New York, NY • Unite… | Location text as posted |
| `loc_bucket` | TEXT | Other California | Los Angeles area, Other California, Other U.S., Remote (U.S.), Outside U.S., Remote (country not stated) or Not stated |
| `is_la` | INTEGER | 0 | 1 if in the Los Angeles area (incl. Orange County) |
| `is_ca` | INTEGER | 1 | 1 if in California |
| `is_us` | INTEGER | 1 | 1 if in the U.S. or remote within the U.S. |
| `is_remote` | INTEGER | 0 | 1 if the posting says remote |
| `employment_type` | TEXT | FullTime | Full-time, part-time, contract ... as posted |
| `posted_date` | TEXT | 2026-02-28 | Date first published (Greenhouse may report the last update) |
| `days_old` | INTEGER | 261 | Days between posted_date and the snapshot |
| `desc_fetched` | INTEGER | 0 | 1 if the description was read for skills and pay |
| `pay_min` | REAL | 153000.0 | Lower end of the first pay range stated in the posting |
| `pay_max` | REAL | 296000.0 | Upper end of that pay range |
| `pay_period` | TEXT | year | year or hour |
| `url` | TEXT | https://boards.greenhouse.io/figma/jobs/… | Link to the original posting |

### posting_skills

Skills named in data-related postings: one row per posting and skill. **8,629 rows.** Source: Keyword matches in posting descriptions.

| Column | Type | Example | Description |
|---|---|---|---|
| `posting_id` | INTEGER | 7 | Links to postings.posting_id |
| `skill` | TEXT | sql | Skill key: sql, python, r, excel, tableau, power_bi, looker, dbt, snowflake, bigquery, aws, spark, airflow, statistics, ab_testing, machine_learning |

### posting_companies

Employers in the snapshot that were collected through a hiring system. **283 rows.** Source: Derived from postings.

| Column | Type | Example | Description |
|---|---|---|---|
| `company` | TEXT | SpaceX | Employer name |
| `sector` | TEXT | A | Sector code |
| `sector_name` | TEXT | Aerospace, defense & hardware | Sector name |
| `source` | TEXT | greenhouse | Platform |
| `postings` | INTEGER | 2788 | Postings collected |

### posting_platforms

What each platform returned. **7 rows.** Source: Derived from postings.

| Column | Type | Example | Description |
|---|---|---|---|
| `source` | TEXT | ashby | Platform key |
| `companies` | INTEGER | 72 | Employers (or advertisers on boards) |
| `postings` | INTEGER | 5213 | Postings collected |
| `platform` | TEXT | Ashby | Platform name |
| `kind` | TEXT | Applicant tracking system: company caree… | Hiring system (ATS) or remote job board |
| `docs_url` | TEXT | https://developers.ashbyhq.com/docs/publ… | API documentation |

## Part 7 · Year by year

### fred_series

The FRED series behind the year-by-year view. **23 rows.** Source: src/config.py (FRED_YEARLY).

| Column | Type | Example | Description |
|---|---|---|---|
| `series_id` | TEXT | JTSJOL | FRED series ID, e.g. JTSJOL (job openings, total, seasonally adjusted) |
| `measure` | TEXT | openings | openings, hires, quits, layoffs, unemployed or fed_funds_rate |
| `industry` | TEXT | Total nonfarm | JOLTS industry, or what the series measures |
| `jobs_sector` | TEXT | Total nonfarm | Matching jobs sector |
| `seasonally_adjusted` | INTEGER | 1 | 1 if seasonally adjusted (FRED has JOLTS industry detail only without adjustment) |

### fred_monthly

Monthly values of every FRED series from January 2020. **1,864 rows.** Source: BLS JOLTS and CPS, Federal Reserve, via FRED.

| Column | Type | Example | Description |
|---|---|---|---|
| `series_id` | TEXT | FEDFUNDS | Links to fred_series.series_id |
| `month` | TEXT | 2020-01-01 | Month (YYYY-MM-01) |
| `value` | REAL | 1.55 | Thousands of people for JOLTS and UNEMPLOY; percent for FEDFUNDS |

### indeed_trackers

Indeed's AI, remote-work and posted-wage trackers for the U.S. **5,816 rows.** Source: Indeed Hiring Lab ai-tracker, remote-tracker, indeed-wage-tracker (CC BY 4.0).

| Column | Type | Example | Description |
|---|---|---|---|
| `date` | TEXT | 2019-01-01 | Date (daily for shares, first of month for wage growth) |
| `metric` | TEXT | ai_share_pct | ai_share_pct, remote_share_pct or posted_wage_growth_pct |
| `value` | REAL | 1.715 | Percent of postings, or year-over-year growth of advertised pay in percent |

### layoffs_annual

Announced job cuts per year, 2020 to October 2026. **7 rows.** Source: Challenger, Gray & Christmas year-end reports (hand-collected, one link per row).

| Column | Type | Example | Description |
|---|---|---|---|
| `year` | INTEGER | 2020 | Calendar year |
| `months_covered` | INTEGER | 12 | 12, or 10 for 2026 (January-October) |
| `job_cuts` | INTEGER | 2304755 | Announced job cuts |
| `tech_cuts` | REAL | 12975.0 | Announced cuts in technology (empty where not reported) |
| `top_industry` | TEXT | Technology | Industry with the most cuts (where reported) |
| `top_industry_cuts` | REAL | 97171.0 | Cuts in that industry |
| `prior_year_same_months` | REAL | 1099500.0 | Cuts in the same months of the year before (for the partial year) |
| `report` | TEXT | Final Job Cuts Report for 2020 | Report the figures come from |
| `url` | TEXT | https://www.challengergray.com/blog/job-… | Link to the report |

## Sources

### research_sources

Where every hand-collected table came from. **10 rows.** Source: data/research/sources.csv.

| Column | Type | Example | Description |
|---|---|---|---|
| `dataset` | TEXT | challenger_job_cuts | Table or file name |
| `report` | TEXT | Challenger Report August 2026 | Report title |
| `published` | TEXT | 2026-09 | Publication date or period |
| `url` | TEXT | https://www.challengergray.com/wp-conten… | Link |
| `collected_on` | TEXT | 2026-11-16 | Date collected |
| `notes` | TEXT | Industry table; announced job cuts by U.… | Notes |

