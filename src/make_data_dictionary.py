"""Write documentation/DATA_DICTIONARY.md from the database itself.

Every table and column in data/sectors.db is listed with its type, row count, an example value and a
description, so the dictionary cannot drift from the schema: a column without a description fails the run.

Usage:  python src/make_data_dictionary.py
"""
import sqlite3
import sys

from config import DB_PATH, ROOT

OUT = ROOT / "documentation" / "DATA_DICTIONARY.md"

# Parts of the project each table belongs to, in the order they appear in the README.
PARTS = [
    ("Part 1-2 · Jobs and stocks", ["series", "employment", "stock_prices", "stock_sectors"]),
    ("Part 3 · The last three months (hand-collected)", ["jolts", "layoffs_monthly", "layoffs_ytd", "layoff_totals", "layoff_reasons"]),
    ("Part 4 · Careers and college majors (hand-collected)", ["occupation_outlook", "majors"]),
    ("Indeed job postings index (Parts 1, 3 and 7)", ["postings_state", "postings_metro", "postings_occ"]),
    ("Part 6 · Live job postings snapshot", ["postings", "posting_skills", "posting_companies", "posting_platforms"]),
    ("Part 7 · Year by year", ["fred_series", "fred_monthly", "indeed_trackers", "layoffs_annual"]),
    ("Sources", ["research_sources"]),
]

TABLES = {
    "series": ("One row per BLS payroll series used in the project.", "src/config.py (SERIES)", {
        "series_id": "FRED series ID, e.g. CANA (California total nonfarm) or PAYEMS (U.S.)",
        "name": "Sector or industry name",
        "level": "total, sector (one of 11 supersectors), industry or county",
        "seasonally_adjusted": "1 if seasonally adjusted, 0 if not",
        "region": "CA or US",
    }),
    "employment": ("Monthly payroll jobs for every series, long format.", "BLS Current Employment Statistics via FRED", {
        "month": "First day of the month (YYYY-MM-01)",
        "series_id": "Links to series.series_id",
        "jobs_k": "Payroll jobs, thousands",
    }),
    "stock_prices": ("Month-end adjusted close of the 11 SPDR sector funds and SPY (dividends reinvested).", "Yahoo Finance", {
        "month": "Month (YYYY-MM-01) of the month-end price",
        "ticker": "Fund ticker, e.g. XLK, XLV, SPY",
        "adj_close": "Adjusted close in dollars",
    }),
    "stock_sectors": ("Maps each fund to its sector and the closest jobs sector.", "src/config.py (STOCKS); the jobs-sector match is my own judgment", {
        "ticker": "Fund ticker",
        "sector": "S&P 500 sector name",
        "jobs_sector": "Closest BLS jobs sector (approximate)",
    }),
    "jolts": ("Job openings, hires and separations by industry for the last three months.", "BLS JOLTS release, Table A (hand-collected)", {
        "industry": "JOLTS industry name, or Total",
        "jobs_sector": "Matching jobs sector",
        "level": "total, sector or industry",
        "month": "Month (YYYY-MM-01)",
        "openings_k": "Job openings on the last business day of the month, thousands, seasonally adjusted",
        "hires_k": "Hires during the month, thousands",
        "separations_k": "Total separations during the month, thousands",
    }),
    "layoffs_monthly": ("Announced job cuts by industry, last three months.", "Challenger, Gray & Christmas monthly report (hand-collected)", {
        "industry": "Challenger industry name",
        "jobs_sector": "Closest BLS jobs sector (approximate)",
        "month": "Month (YYYY-MM-01)",
        "cuts": "Announced job cuts",
    }),
    "layoffs_ytd": ("Announced job cuts by industry, January to October 2026 against the same months of 2025.", "Challenger, Gray & Christmas (hand-collected)", {
        "industry": "Challenger industry name; TOTAL is the sum",
        "jobs_sector": "Closest BLS jobs sector (approximate)",
        "ytd_2026": "Announced cuts, January-October 2026",
        "ytd_2025": "Announced cuts, January-October 2025",
    }),
    "layoff_totals": ("Monthly totals of announced job cuts and hiring plans.", "Challenger, Gray & Christmas (hand-collected)", {
        "month": "Month (YYYY-MM-01)",
        "job_cuts": "Announced job cuts",
        "hiring_plans": "Announced hiring plans",
    }),
    "layoff_reasons": ("Reasons employers gave for announced cuts.", "Challenger, Gray & Christmas (hand-collected)", {
        "reason": "Reason as Challenger reports it",
        "oct_2026": "Cuts attributed to the reason in October 2026",
        "ytd_2026": "Cuts attributed to the reason, January-October 2026",
    }),
    "occupation_outlook": ("BLS employment projections 2025-2035 for 64 occupations.", "BLS Employment Projections, Table 1.10 (hand-collected)", {
        "code": "SOC occupation code",
        "title": "Occupation title",
        "emp_2025_k": "Employment in 2025, thousands",
        "emp_2035_k": "Projected employment in 2035, thousands",
        "change_pct": "Projected change 2025-2035, percent",
        "openings_k": "Average yearly openings 2025-2035, thousands (growth plus replacement)",
        "median_wage": "Median annual wage in dollars, as published with the projections",
        "education": "Typical education needed for entry",
        "field": "Field in this project: engineering, health care, finance, computer & data, film & media, or growth lists",
        "bachelors": "1 if the typical entry education is a bachelor's degree",
    }),
    "majors": ("Labor-market outcomes of recent college graduates by major.", "Federal Reserve Bank of New York, The Labor Market for Recent College Graduates (hand-collected)", {
        "major": "College major",
        "unemployment_pct": "Unemployment rate of recent graduates (ages 22-27), percent",
        "underemployment_pct": "Share of recent graduates in jobs that do not need a degree, percent",
        "wage_early": "Median wage, early career (ages 22-27), dollars",
        "wage_mid": "Median wage, mid-career (ages 35-45), dollars",
        "grad_share_pct": "Share with a graduate degree, percent",
        "major_group": "One of eight major families (my own grouping, src/config.py)",
    }),
    "postings_state": ("Indeed job postings index for the U.S. and California, daily.", "Indeed Hiring Lab job_postings_tracker (CC BY 4.0)", {
        "date": "Date (YYYY-MM-DD)",
        "state": "US or CA",
        "postings_index": "Postings index, seasonally adjusted, 7-day average; February 1, 2020 = 100",
    }),
    "postings_metro": ("Indeed job postings index for California metro areas, daily.", "Indeed Hiring Lab job_postings_tracker (CC BY 4.0)", {
        "date": "Date (YYYY-MM-DD)",
        "metro": "Metro area (CBSA) name",
        "cbsa_code": "Census CBSA code",
        "postings_index": "Postings index, 7-day average; February 1, 2020 = 100",
    }),
    "postings_occ": ("Indeed job postings index for 47 occupational categories, U.S., daily.", "Indeed Hiring Lab job_postings_tracker (CC BY 4.0)", {
        "date": "Date (YYYY-MM-DD)",
        "occupation": "Indeed occupational category, e.g. Data & Analytics",
        "postings_index": "Postings index, seasonally adjusted, 7-day average; February 1, 2020 = 100",
    }),
    "postings": ("One row per open job posting in the 17 November 2026 snapshot, classified by src/postings.py.",
                 "Public job APIs of Greenhouse, Ashby, Lever, SmartRecruiters; Remotive, Remote OK, Jobicy", {
        "posting_id": "Row ID within the snapshot",
        "snapshot_date": "Date the snapshot was collected",
        "source": "Platform: greenhouse, ashby, lever, smartrecruiters, remotive, remoteok or jobicy",
        "company": "Employer name",
        "sector": "Employer sector code (T, H, F, A, M, C, R)",
        "sector_name": "Employer sector name, e.g. Health care & life sciences",
        "title": "Job title as posted",
        "title_norm": "Title with seniority words and qualifiers removed (for counting titles)",
        "family": "Job family from keyword rules, e.g. Data & analytics",
        "eng_type": "Kind of engineer for engineering titles (Software, Mechanical, ...); empty otherwise",
        "seniority": "Internship, Entry level, Mid or not stated, or Senior & management",
        "is_data_analyst": "1 if the title is an analyst title in data, business intelligence or reporting",
        "department": "Department or team as posted",
        "location": "Location text as posted",
        "loc_bucket": "Los Angeles area, Other California, Other U.S., Remote (U.S.), Outside U.S., Remote (country not stated) or Not stated",
        "is_la": "1 if in the Los Angeles area (incl. Orange County)",
        "is_ca": "1 if in California",
        "is_us": "1 if in the U.S. or remote within the U.S.",
        "is_remote": "1 if the posting says remote",
        "employment_type": "Full-time, part-time, contract ... as posted",
        "posted_date": "Date first published (Greenhouse may report the last update)",
        "days_old": "Days between posted_date and the snapshot",
        "desc_fetched": "1 if the description was read for skills and pay",
        "pay_min": "Lower end of the first pay range stated in the posting",
        "pay_max": "Upper end of that pay range",
        "pay_period": "year or hour",
        "url": "Link to the original posting",
    }),
    "posting_skills": ("Skills named in data-related postings: one row per posting and skill.", "Keyword matches in posting descriptions", {
        "posting_id": "Links to postings.posting_id",
        "skill": "Skill key: sql, python, r, excel, tableau, power_bi, looker, dbt, snowflake, bigquery, aws, spark, airflow, statistics, ab_testing, machine_learning",
    }),
    "posting_companies": ("Employers in the snapshot that were collected through a hiring system.", "Derived from postings", {
        "company": "Employer name",
        "sector": "Sector code",
        "sector_name": "Sector name",
        "source": "Platform",
        "postings": "Postings collected",
    }),
    "posting_platforms": ("What each platform returned.", "Derived from postings", {
        "source": "Platform key",
        "companies": "Employers (or advertisers on boards)",
        "postings": "Postings collected",
        "platform": "Platform name",
        "kind": "Hiring system (ATS) or remote job board",
        "docs_url": "API documentation",
    }),
    "fred_series": ("The FRED series behind the year-by-year view.", "src/config.py (FRED_YEARLY)", {
        "series_id": "FRED series ID, e.g. JTSJOL (job openings, total, seasonally adjusted)",
        "measure": "openings, hires, quits, layoffs, unemployed or fed_funds_rate",
        "industry": "JOLTS industry, or what the series measures",
        "jobs_sector": "Matching jobs sector",
        "seasonally_adjusted": "1 if seasonally adjusted (FRED has JOLTS industry detail only without adjustment)",
    }),
    "fred_monthly": ("Monthly values of every FRED series from January 2020.", "BLS JOLTS and CPS, Federal Reserve, via FRED", {
        "series_id": "Links to fred_series.series_id",
        "month": "Month (YYYY-MM-01)",
        "value": "Thousands of people for JOLTS and UNEMPLOY; percent for FEDFUNDS",
    }),
    "indeed_trackers": ("Indeed's AI, remote-work and posted-wage trackers for the U.S.", "Indeed Hiring Lab ai-tracker, remote-tracker, indeed-wage-tracker (CC BY 4.0)", {
        "date": "Date (daily for shares, first of month for wage growth)",
        "metric": "ai_share_pct, remote_share_pct or posted_wage_growth_pct",
        "value": "Percent of postings, or year-over-year growth of advertised pay in percent",
    }),
    "layoffs_annual": ("Announced job cuts per year, 2020 to October 2026.", "Challenger, Gray & Christmas year-end reports (hand-collected, one link per row)", {
        "year": "Calendar year",
        "months_covered": "12, or 10 for 2026 (January-October)",
        "job_cuts": "Announced job cuts",
        "tech_cuts": "Announced cuts in technology (empty where not reported)",
        "top_industry": "Industry with the most cuts (where reported)",
        "top_industry_cuts": "Cuts in that industry",
        "prior_year_same_months": "Cuts in the same months of the year before (for the partial year)",
        "report": "Report the figures come from",
        "url": "Link to the report",
    }),
    "research_sources": ("Where every hand-collected table came from.", "data/research/sources.csv", {
        "dataset": "Table or file name",
        "report": "Report title",
        "published": "Publication date or period",
        "url": "Link",
        "collected_on": "Date collected",
        "notes": "Notes",
    }),
}


def example(conn, table, col):
    """Value from the table's first row, or the first non-empty value when that row has none."""
    v = conn.execute(f'SELECT "{col}" FROM "{table}" LIMIT 1').fetchone()
    if v is None or v[0] in (None, ""):
        v = conn.execute(f'SELECT "{col}" FROM "{table}" WHERE "{col}" IS NOT NULL AND "{col}" <> \'\' LIMIT 1').fetchone()
    if not v:
        return ""
    s = str(v[0])
    return (s[:40] + "…") if len(s) > 40 else s


def main() -> int:
    conn = sqlite3.connect(DB_PATH)
    tables = {n for (n,) in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    listed = {t for _, ts in PARTS for t in ts}
    problems = sorted(tables ^ listed)
    lines = ["# Data dictionary", "",
             "Every table and column in `data/sectors.db`. This file is written by `src/make_data_dictionary.py` from the database itself; "
             "rebuild the database and run the script to update it.", "",
             f"{len(tables)} tables, {sum(conn.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0] for t in tables):,} rows in total.", ""]
    lines += ["## Contents", ""] + [f"- **{p}:** " + ", ".join(f"[`{t}`](#{t})" for t in ts) for p, ts in PARTS] + [""]
    for part, ts in PARTS:
        lines += [f"## {part}", ""]
        for t in ts:
            desc, source, cols = TABLES[t]
            n = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            lines += [f"### {t}", "", f"{desc} **{n:,} rows.** Source: {source}.", "", "| Column | Type | Example | Description |", "|---|---|---|---|"]
            for _, col, ctype, *_ in conn.execute(f"PRAGMA table_info({t})"):
                if col not in cols:
                    problems.append(f"{t}.{col} has no description")
                ex = example(conn, t, col).replace("|", "/")
                lines.append(f"| `{col}` | {ctype or 'TEXT'} | {ex} | {cols.get(col, '')} |")
            lines.append("")
    if problems:
        print("Data dictionary is out of date:", *problems, sep="\n  ")
        return 1
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text("\n".join(lines) + "\n")
    print(f"wrote {OUT.relative_to(ROOT)} ({len(tables)} tables)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
