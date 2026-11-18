# Roadmap: data that could be added next

Sources checked in November 2026 that would answer questions the project does not answer yet. Each entry says what it adds, how to get it, and what to watch out for.

## Open data, no key needed

| Source | What it adds | Access | Notes |
|---|---|---|---|
| **BLS Occupational Employment and Wage Statistics (OEWS), May 2025** | Employment and wages (median, 10th–90th percentile) for every occupation in the Los Angeles metro, California and the U.S. Answers "what does a data analyst, data scientist or BI analyst actually earn in LA?" next to the posted pay in the snapshot. | [bls.gov/oes](https://www.bls.gov/oes/) area files (XLSX); the [Los Angeles release](https://www.bls.gov/regions/west/news-release/occupationalemploymentandwages_losangeles.htm) for checks | Released May 15, 2026; data are May 2025. Data scientists are SOC 15-2051, business intelligence analysts are within 15-2051.01 in O*NET. |
| **California EDD WARN notices** | Company-level layoffs in California with city, county, date and number of workers, by fiscal year since 2014. Gives a California and Los Angeles County view of layoffs, year by year, to sit next to the national Challenger figures. | [EDD WARN page](https://edd.ca.gov/en/jobs_and_training/Layoff_Services_WARN): current report as XLSX, earlier years as PDF | Only notices that WARN requires (mass layoffs and closures); fiscal years run July–June. Older years need PDF table extraction. |
| **California EDD long-term projections 2023–2033** | Occupational projections for the Los Angeles County region, the local version of the BLS projections in Part 4. | [data.ca.gov CSV](https://data.ca.gov/dataset/long-term-occupational-employment-projections) (CC BY) | Regions, not cities; revised every two years. |
| **O\*NET technology skills** | The software each occupation uses, with "hot" and "in demand" flags from job postings. Can be compared with the skills counted in the live postings. | [O\*NET database](https://www.onetcenter.org/database.html) text files | Occupation-level lists, not counts per posting. |
| **BLS QCEW, Los Angeles County** | Quarterly employment and average weekly wage by industry for the county, 2020–2025. Adds pay by sector to the jobs view. | [QCEW open data CSV slices](https://www.bls.gov/cew/additional-resources/open-data/csv-data-slices.htm) | About five months behind; county totals can be suppressed for small industries. |
| **BLS state JOLTS, California** | Openings, hires, quits and layoffs for California, to compare with the U.S. figures in Part 7. | BLS JOLTS database (series JTS000000060000000JOL and related) | BLS moved the state release from monthly to annual after the December 2025 data. |

## Free key needed

| Source | What it adds | Access | Notes |
|---|---|---|---|
| **Adzuna API** | Monthly history of job counts and average advertised salary by category and location (e.g. IT jobs in Los Angeles), plus top hiring companies. | [developer.adzuna.com](https://developer.adzuna.com/), free tier about 1,000 calls a month | Adzuna estimates salary when a posting gives none; use only stated salaries. |
| **USAJOBS API** | Federal job postings, a sector the snapshot misses. | [developer.usajobs.gov](https://developer.usajobs.gov/) | Needs an API key and the account e-mail in each request. |

## Large files

| Source | What it adds | Access | Notes |
|---|---|---|---|
| **DOL H-1B labor condition applications (LCA)** | Offered pay by employer, job title and worksite for every certified application, e.g. data analyst salaries at Los Angeles employers. | [DOL OFLC performance data](https://www.dol.gov/agencies/eta/foreign-labor/performance), quarterly XLSX | Hundreds of MB per year; covers only employers that sponsor visas, so it describes them, not the whole market. |

## Project improvements

- **Automate the weekly Indeed refresh** with a scheduled GitHub Action that runs `download_data.py`, rebuilds the database and the dashboard, and opens a pull request.
- **Run the checks on every push** (tests and `validate.py`) in GitHub Actions.
- **A second postings snapshot** in a few months, so the live postings can be compared over time with `collect_postings.py`.
- **A licence file** stating the terms for the code (for example MIT) and pointing to each data source's own terms.
