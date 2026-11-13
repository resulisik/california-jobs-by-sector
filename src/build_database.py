"""Clean the raw files and load them into one SQLite database (data/ca_jobs.db).

Tables
  series          one row per BLS series (id, name, level, seasonally_adjusted)
  employment      long format: series_id, month, jobs_k (thousands of jobs)
  postings_state  Indeed job postings index for California and the U.S. (daily)
  postings_metro  Indeed index for California metro areas (daily)
  postings_occ    Indeed index by occupational category, U.S. (daily)

The Indeed index is 100 on Feb 1, 2020: 110 means 10% more postings than then.
Small California-only extracts are also written to data/processed/ so the
dashboard can be rebuilt without the 60 MB metro file.
"""
import sqlite3

import pandas as pd

from config import DB_PATH, PROCESSED, RAW_BLS, RAW_INDEED, SERIES


def build_series() -> pd.DataFrame:
    return pd.DataFrame(
        [(sid, name, level, int(sa)) for sid, name, level, sa, _ in SERIES],
        columns=["series_id", "name", "level", "seasonally_adjusted"],
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


def main() -> None:
    tables = {
        "series": build_series(),
        "employment": build_employment(),
        "postings_state": build_postings_state(),
        "postings_metro": build_postings_metro(),
        "postings_occ": build_postings_occ(),
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
            """
        )
    tables["employment"].to_csv(PROCESSED / "employment.csv", index=False)
    tables["series"].to_csv(PROCESSED / "series.csv", index=False)
    # Postings are daily; the processed copies are monthly averages to stay small.
    for name, key in (("postings_state", "state"), ("postings_metro", "metro"), ("postings_occ", "occupation")):
        df = tables[name].copy()
        df["month"] = df["date"].str[:7] + "-01"
        monthly = df.groupby([key, "month"], as_index=False)["postings_index"].mean().round(2)
        monthly.to_csv(PROCESSED / f"{name}_monthly.csv", index=False)
    print(f"database: {DB_PATH}")


if __name__ == "__main__":
    main()
