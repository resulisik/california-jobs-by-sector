# Methodology

How the numbers in Sector Pulse are collected, defined, checked and limited. For the tables and columns, see the [data dictionary](DATA_DICTIONARY.md); for what could be added next, see the [roadmap](ROADMAP.md).

## 1. Questions

1. **Jobs:** which sectors added jobs in five years, and is California keeping up with the U.S.?
2. **Stocks:** which sectors did investors reward, and which are gaining speed now?
3. **The last three months:** what do the latest hiring, openings and layoff figures show?
4. **Careers and majors:** which occupations have the most openings, and how do college majors compare?
5. **Live postings:** what are employers posting today, and what do they ask for?
6. **Year by year:** what happened to job postings in each year since 2020?

## 2. How the data is collected

| Kind | Sources | How | Refresh |
|---|---|---|---|
| **Downloaded** | BLS payrolls (FRED), Yahoo Finance, Indeed Hiring Lab, JOLTS and CPS (FRED), Indeed AI / remote / wage trackers | `src/download_data.py` | Monthly (BLS, FRED, stocks); weekly (Indeed) |
| **Hand-collected** | BLS JOLTS Table A, Challenger monthly and year-end reports, BLS Employment Projections Table 1.10, New York Fed majors | Typed from the published release into `data/research/*.csv`; every table has its report and link in `sources.csv` | When a new report comes out |
| **Collected snapshot** | Public job APIs of Greenhouse, Ashby, Lever, SmartRecruiters; Remotive, Remote OK, Jobicy | `src/collect_postings.py` (the committed snapshot was collected with the same requests from a browser) | On demand; one file per day in `data/raw/postings/` |

LinkedIn, Indeed, ZipRecruiter and Glassdoor are not collected: their terms forbid automated collection and they offer no open postings API.

## 3. Pipeline

```
download_data.py      -> data/raw/          downloaded files
collect_postings.py   -> data/raw/postings/ one-day postings snapshot
build_database.py     -> data/sectors.db    23 tables; postings classified by postings.py
validate.py                                 stops on any mismatch with published figures
run_queries.py        -> sql/results.md     52 SQL queries
make_charts.py        -> charts/            15 charts
build_dashboard.py    -> docs/index.html    the interactive dashboard (GitHub Pages)
make_data_dictionary.py -> documentation/DATA_DICTIONARY.md
```

Every step can be run again from the committed files except the Indeed daily files (about 60 MB), which `download_data.py` fetches from Indeed's GitHub repository.

## 4. Definitions

**Jobs and growth.** Payroll jobs from the BLS Current Employment Statistics, seasonally adjusted where available. Five-year growth compares September 2021 with September 2026 for California (the latest state month) and October 2021 with October 2026 for the U.S. *Momentum* is the change in the last 12 months minus the change in the 12 months before, in percentage points.

**Sectors.** The 11 BLS supersectors. Stock sectors (the 11 SPDR sector funds) group companies by what they sell, jobs sectors group employers by what they do; each fund is matched to the closest jobs sector by judgment (`stock_sectors`).

**Stock returns.** Total return from month-end adjusted closes, so dividends are reinvested. Five years run from October 2021 to October 2026. *Maximum drawdown* is the largest fall from a previous month-end high.

**Indeed job postings index.** Indeed's count of postings on its site, seasonally adjusted, as a 7-day average, set to 100 on February 1, 2020. 110 means 10% more postings than then. The index shows the trend, not the number of jobs, and Indeed revises it when it updates its seasonal adjustment. Yearly figures are averages of the daily index; 2020 starts on February 1.

**Job openings (JOLTS).** Positions open on the last business day of the month. The U.S. totals are seasonally adjusted. FRED carries industry detail only without seasonal adjustment, so industries are compared as yearly averages, and the partial year 2026 against the same months of 2025. *Openings per unemployed person* divides JOLTS openings by unemployed persons from the household survey (CPS) in the same month.

**Layoffs.** *Announced job cuts* (Challenger) are employers' stated plans and are counted when announced. *Layoffs and discharges* (JOLTS) are separations that happened. The two answer different questions and are shown side by side.

**AI and remote postings.** Indeed's share of U.S. postings that mention AI keywords (machine learning, data science, generative AI and similar) or offer remote or hybrid work.

**Projections and majors.** BLS projections are ten-year averages for the whole U.S. New York Fed figures describe recent graduates aged 22–27; *underemployment* is the share working in jobs that typically do not need a degree.

## 5. Classifying the live postings

`src/postings.py` turns raw postings into analysable rows. The rules are keyword rules on the title and location text, applied in a fixed order; `tests/test_postings.py` holds the cases they must pass.

- **Job family.** The first matching family wins, in this order: internship, data & analytics, AI & machine learning, product & design, clinical health care, science & research, software engineering & IT, finance & accounting, sales & customer success, marketing & communications, creative & media production, people/legal/admin, hardware & other engineering, operations & service. Two precedence rules prevent common mistakes: "Software Engineer, Data Platform" is software, not data, unless the title says data engineer, analytics engineer, data scientist or data analyst; "Engineer, Launch Operations" is engineering, not operations. Unmatched titles are "Other".
- **Seniority.** Internship, then senior and management words (senior, staff, principal, lead, director, head, II–V …), then entry words (junior, associate, new grad, entry level …), then manager titles, otherwise "Mid or not stated". Where a platform states the level (SmartRecruiters, Jobicy), it is used.
- **Location.** Los Angeles area (incl. Orange County) before other California, before other U.S., before outside the U.S.; remote postings are U.S. when the text or country says so.
- **Skills and pay.** For data-related titles the description is read once: a skill counts when its name appears; pay is the first range stated, as yearly or hourly. Descriptions are not stored.
- **Sample.** Postings are deduplicated by platform and ID; companies reached through a hiring system are dropped from the remote boards to avoid double counting; a few job boards that returned another company with the same name were removed or renamed by hand (listed in `postings.py`).

## 6. Validation

`src/validate.py` stops the build if any of these fail:

- California's 12-month change in all 11 sectors equals the state's (EDD) release; U.S. October figures equal the BLS release.
- Challenger industries add up to the monthly totals; JOLTS sectors add up to the total; the Challenger 2026 year-to-date figures match the year-end table.
- FRED's September 2026 job openings equal the hand-collected BLS release table (7,523 thousand).
- BLS projections and New York Fed spot checks (registered nurses 180.8K openings a year; all majors 4.2% unemployment, 39.4% underemployment).
- Every jobs, price and FRED series has all its months; all 47 Indeed occupations appear in every year.
- Postings: unique IDs, platform totals add up, every posting is classified, pay ranges run low to high, the classification tests pass.

## 7. Limits

- Jobs are counted by the employer's industry, not by occupation.
- The groupings of stock sectors to jobs sectors, Challenger industries to jobs sectors and majors to families are approximate and my own.
- The postings snapshot is one day, from employers whose hiring systems have an open API; it leans toward tech, aerospace and startups, and toward California (45% of its U.S. postings). Hospitals, studios, banks and governments mostly use systems without one.
- Keyword rules are close, not exact; "Mid or not stated" includes every posting without a level word.
- 2026 is a partial year in every source. BLS revises data; figures are as published in November 2026.
- Stock figures are past returns, not investment advice.
