"""Clean the raw files and load them into one SQLite database (data/ca_jobs.db).

Tables
  series          one row per BLS series (id, name, level, seasonally_adjusted, region CA/US)
  employment      long format: series_id, month, jobs_k (thousands of jobs)
  stock_prices    month-end adjusted close for 11 sector funds and the S&P 500
  stock_sectors   ticker -> sector name and the closest jobs sector
  layoffs_*       announced job cuts by industry, last 3 months (hand-collected)
  jolts           job openings, hires, separations by industry (hand-collected)
  occupation_outlook  BLS 2025-35 projections for selected occupations (hand-collected)
  majors          New York Fed outcomes by college major (hand-collected)
  postings        job postings snapshot from public job APIs, one row per posting, classified
  posting_skills  skills named in data-related postings (one row per posting and skill)
  posting_companies / posting_platforms  employers and platforms in the snapshot
  research_sources where every hand-collected number came from
  postings_state  Indeed job postings index for California and the U.S. (daily)
  postings_metro  Indeed index for California metro areas (daily)
  postings_occ    Indeed index by occupational category, U.S. (daily)

The Indeed index is 100 on Feb 1, 2020: 110 means 10% more postings than then.
Small California-only extracts are also written to data/processed/ so the
dashboard can be rebuilt without the 60 MB metro file.
"""
import sqlite3

import pandas as pd

from config import (DB_PATH, MAJOR_GROUPS, OCCUPATION_FIELDS, OTHER_MAJOR_GROUP, POSTINGS_SNAPSHOT, PROCESSED, RAW_BLS,
                    RAW_INDEED, RAW_POSTINGS, RAW_STOCKS, RESEARCH, SERIES, STOCKS)
from postings import BOARD_SOURCES, clean as clean_postings, skills_long


def build_series() -> pd.DataFrame:
    return pd.DataFrame(
        [(sid, name, level, int(sa), region) for sid, name, level, sa, _, region in SERIES],
        columns=["series_id", "name", "level", "seasonally_adjusted", "region"],
    )


def build_employment() -> pd.DataFrame:
    frames = []
    for fname in sorted({s[4] for s in SERIES}):
        wide = pd.read_csv(RAW_BLS / fname)
        long = wide.melt(id_vars="date", var_name="series_id", value_name="jobs_k")
        frames.append(long)
    emp = pd.concat(frames).rename(columns={"date": "month"})
    known = {s[0] for s in SERIES}
    emp = emp[emp["series_id"].isin(known)].dropna(subset=["jobs_k"])
    emp["jobs_k"] = emp["jobs_k"].astype(float)
    dupes = emp.duplicated(["series_id", "month"]).sum()
    assert dupes == 0, f"{dupes} duplicate series/month rows"
    return emp.sort_values(["series_id", "month"]).reset_index(drop=True)


def build_postings_state() -> pd.DataFrame:
    st = pd.read_csv(RAW_INDEED / "state_job_postings_us.csv")
    st["state"] = st["state"].str.upper()
    ca = st[st["state"] == "CA"].rename(columns={"indeed_job_postings_index": "postings_index"})

    us = pd.read_csv(RAW_INDEED / "aggregate_job_postings_US.csv")
    us = us[us["variable"] == "total postings"]
    us = us.rename(columns={"indeed_job_postings_index_SA": "postings_index"})
    us["state"] = "US"
    cols = ["date", "state", "postings_index"]
    return pd.concat([ca[cols], us[cols]]).sort_values(["state", "date"]).reset_index(drop=True)


def build_postings_metro() -> pd.DataFrame:
    m = pd.read_csv(RAW_INDEED / "metro_job_postings_us.csv")
    m = m[m["metro"].str.endswith(", CA")]
    return m.rename(columns={"indeed_job_postings_index": "postings_index"})[
        ["date", "metro", "cbsa_code", "postings_index"]
    ].reset_index(drop=True)


def build_postings_occ() -> pd.DataFrame:
    s = pd.read_csv(RAW_INDEED / "job_postings_by_sector_US.csv")
    s = s[s["variable"] == "total postings"]
    return s.rename(
        columns={"display_name": "occupation", "indeed_job_postings_index": "postings_index"}
    )[["date", "occupation", "postings_index"]].reset_index(drop=True)


def build_stock_prices() -> pd.DataFrame:
    """Month-end adjusted close (dividends reinvested), one row per fund and month."""
    wide = pd.read_csv(RAW_STOCKS / "sector_etf_monthly.csv")
    long = wide.melt(id_vars="month", var_name="ticker", value_name="adj_close")
    long["month"] = long["month"] + "-01"
    return long.sort_values(["ticker", "month"]).reset_index(drop=True)


def build_stock_sectors() -> pd.DataFrame:
    return pd.DataFrame(STOCKS, columns=["ticker", "sector", "jobs_sector"])


def build_layoffs():
    """Challenger announced job cuts, hand-collected from the monthly reports."""
    wide = pd.read_csv(RESEARCH / "challenger_job_cuts.csv")
    ytd = wide[["industry", "jobs_sector", "ytd_2026", "ytd_2025"]]
    monthly = wide.melt(id_vars=["industry", "jobs_sector"], value_vars=["aug_2026", "sep_2026", "oct_2026"],
                        var_name="m", value_name="cuts")
    monthly["month"] = monthly["m"].map({"aug_2026": "2026-08-01", "sep_2026": "2026-09-01", "oct_2026": "2026-10-01"})
    return monthly[["industry", "jobs_sector", "month", "cuts"]], ytd


def build_jolts() -> pd.DataFrame:
    """BLS JOLTS Table A, hand-collected: openings, hires, separations (thousands)."""
    wide = pd.read_csv(RESEARCH / "jolts_by_industry.csv")
    frames = []
    for suffix, month in (("sep2025", "2025-09-01"), ("aug2026", "2026-08-01"), ("sep2026", "2026-09-01")):
        f = wide[["industry", "jobs_sector", "level"]].copy()
        f["month"] = month
        for measure in ("openings", "hires", "separations"):
            f[f"{measure}_k"] = wide[f"{measure}_{suffix}"]
        frames.append(f)
    return pd.concat(frames).reset_index(drop=True)


def build_occupations() -> pd.DataFrame:
    """BLS Employment Projections 2025-35 for selected occupations (hand-collected)."""
    df = pd.read_csv(RESEARCH / "bls_occupation_outlook.csv", sep="|")
    tags = df["tags"].str.split(";")
    df["field"] = [next((OCCUPATION_FIELDS[x] for x in t if x in OCCUPATION_FIELDS), None) for t in tags]
    df["bachelors"] = (df["education"] == "Bachelor's degree").astype(int)
    return df.drop(columns="tags")


def build_majors() -> pd.DataFrame:
    """New York Fed outcomes by college major, figures for 2024 (hand-collected)."""
    df = pd.read_csv(RESEARCH / "nyfed_majors.csv", sep="|")
    lookup = {m: g for g, majors in MAJOR_GROUPS.items() for m in majors}
    df["major_group"] = [("All majors" if m == "OVERALL" else lookup.get(m, OTHER_MAJOR_GROUP)) for m in df["major"]]
    small = {"And", "Of", "&"}
    df["major"] = [" ".join(w if w in small else w.capitalize() for w in m.title().split()).replace("And", "and")
                   for m in df["major"]]
    return df


PLATFORMS = {
    "greenhouse": ("Greenhouse", "Applicant tracking system: company careers pages", "https://developers.greenhouse.io/job-board.html"),
    "ashby": ("Ashby", "Applicant tracking system: company careers pages", "https://developers.ashbyhq.com/docs/public-job-posting-api"),
    "lever": ("Lever", "Applicant tracking system: company careers pages", "https://github.com/lever/postings-api"),
    "smartrecruiters": ("SmartRecruiters", "Applicant tracking system: company careers pages", "https://developers.smartrecruiters.com/docs/posting-api"),
    "jobicy": ("Jobicy", "Remote job board", "https://jobicy.com/jobs-rss-feed"),
    "remoteok": ("Remote OK", "Remote job board", "https://remoteok.com"),
    "remotive": ("Remotive", "Remote job board", "https://remotive.com"),
}


def build_postings():
    """Job-postings snapshot from public job APIs, cleaned and classified (src/postings.py)."""
    raw = pd.read_csv(RAW_POSTINGS / f"postings_{POSTINGS_SNAPSHOT}.csv.gz", dtype=str, keep_default_na=False)
    df = clean_postings(raw, POSTINGS_SNAPSHOT)
    keep = ["posting_id", "snapshot_date", "source", "company", "sector", "sector_name", "title", "title_norm", "family",
            "eng_type", "seniority", "is_data_analyst", "department", "location", "loc_bucket", "is_la", "is_ca", "is_us",
            "is_remote", "employment_type", "posted_date", "days_old", "desc_fetched", "pay_min", "pay_max", "pay_period", "url"]
    postings = df[keep].copy()
    postings["desc_fetched"] = postings["desc_fetched"].astype(int)
    companies = (df.groupby(["company", "sector", "sector_name", "source"]).size().reset_index(name="postings")
                 .sort_values("postings", ascending=False))
    companies = companies[~companies["source"].isin(BOARD_SOURCES)]
    platforms = (df.groupby("source").agg(companies=("company", "nunique"), postings=("posting_id", "size"))
                 .reset_index())
    platforms["platform"] = platforms["source"].map(lambda s: PLATFORMS[s][0])
    platforms["kind"] = platforms["source"].map(lambda s: PLATFORMS[s][1])
    platforms["docs_url"] = platforms["source"].map(lambda s: PLATFORMS[s][2])
    return postings, skills_long(df), companies, platforms


def main() -> None:
    layoffs_monthly, layoffs_ytd = build_layoffs()
    postings, posting_skills, posting_companies, posting_platforms = build_postings()
    tables = {
        "series": build_series(),
        "employment": build_employment(),
        "postings_state": build_postings_state(),
        "postings_metro": build_postings_metro(),
        "postings_occ": build_postings_occ(),
        "stock_prices": build_stock_prices(),
        "stock_sectors": build_stock_sectors(),
        "layoffs_monthly": layoffs_monthly,
        "layoffs_ytd": layoffs_ytd,
        "layoff_totals": pd.read_csv(RESEARCH / "challenger_totals.csv"),
        "layoff_reasons": pd.read_csv(RESEARCH / "challenger_reasons.csv"),
        "jolts": build_jolts(),
        "occupation_outlook": build_occupations(),
        "majors": build_majors(),
        "postings": postings,
        "posting_skills": posting_skills,
        "posting_companies": posting_companies,
        "posting_platforms": posting_platforms,
        "research_sources": pd.read_csv(RESEARCH / "sources.csv"),
    }
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    PROCESSED.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        for name, df in tables.items():
            df.to_sql(name, conn, if_exists="replace", index=False)
            print(f"{name:15s} {len(df):>8,} rows")
        conn.executescript(
            """
            CREATE INDEX IF NOT EXISTS idx_emp ON employment(series_id, month);
            CREATE INDEX IF NOT EXISTS idx_ps ON postings_state(state, date);
            CREATE INDEX IF NOT EXISTS idx_pm ON postings_metro(metro, date);
            CREATE INDEX IF NOT EXISTS idx_po ON postings_occ(occupation, date);
            CREATE INDEX IF NOT EXISTS idx_sp ON stock_prices(ticker, month);
            CREATE INDEX IF NOT EXISTS idx_post_family ON postings(family, sector);
            CREATE INDEX IF NOT EXISTS idx_post_skill ON posting_skills(posting_id);
            """
        )
    tables["employment"].to_csv(PROCESSED / "employment.csv", index=False)
    tables["series"].to_csv(PROCESSED / "series.csv", index=False)
    tables["stock_prices"].to_csv(PROCESSED / "stock_prices.csv", index=False)
    tables["stock_sectors"].to_csv(PROCESSED / "stock_sectors.csv", index=False)
    tables["postings"].to_csv(PROCESSED / "postings.csv.gz", index=False)
    tables["posting_skills"].to_csv(PROCESSED / "posting_skills.csv", index=False)
    # Postings are daily; the processed copies are monthly averages to stay small.
    for name, key in (("postings_state", "state"), ("postings_metro", "metro"), ("postings_occ", "occupation")):
        df = tables[name].copy()
        df["month"] = df["date"].str[:7] + "-01"
        monthly = df.groupby([key, "month"], as_index=False)["postings_index"].mean().round(2)
        monthly.to_csv(PROCESSED / f"{name}_monthly.csv", index=False)
    print(f"database: {DB_PATH}")


if __name__ == "__main__":
    main()
