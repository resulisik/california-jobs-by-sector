"""Check the database against figures published elsewhere.

1. California: the 12-month change by sector must match the EDD news release
   for September 2026 (Sep 2025 -> Sep 2026, seasonally adjusted, in jobs).
2. United States: October 2026 monthly changes must match the BLS
   Employment Situation release.
3. Hand-collected tables: monthly totals must match the published headline
   numbers (Challenger job cuts, JOLTS job openings).
4. Every series must have one value per month with no gaps.
Run after build_database.py; exits with code 1 on any mismatch.
"""
import sqlite3
import sys

import pandas as pd

from config import DB_PATH

# EDD, "Unemployment Rate ... September 2026" news release, year-over change.
EDD_SEP_2026 = {
    "Private education & health services": 125_600,
    "Leisure & hospitality": 28_700,
    "Trade, transportation & utilities": 25_200,
    "Government": 9_300,
    "Other services": 4_400,
    "Mining & logging": -200,
    "Construction": -4_800,
    "Professional & business services": -7_400,
    "Manufacturing": -10_700,
    "Financial activities": -16_600,
    "Information": -24_200,
}
# BLS Employment Situation, October 2026: change from September, in jobs.
BLS_OCT_2026 = {
    "Total nonfarm": 165_000,
    "Professional & business services": 70_000,
    "Manufacturing": 19_000,
}
CHALLENGER_TOTALS = {"2026-08-01": 52_881, "2026-09-01": 43_281, "2026-10-01": 43_994}
JOLTS_OPENINGS_SEP_2026_K = 7_523


def check(ok: bool, label: str) -> int:
    print(f"{'ok ' if ok else 'BAD'} {label}")
    return 0 if ok else 1


def main() -> int:
    errors = 0
    with sqlite3.connect(DB_PATH) as conn:
        ca = pd.read_sql_query("""
            SELECT s.name,
                   1000 * (MAX(CASE WHEN month = '2026-09-01' THEN jobs_k END)
                         - MAX(CASE WHEN month = '2025-09-01' THEN jobs_k END)) AS chg
            FROM employment e JOIN series s USING (series_id)
            WHERE s.region = 'CA' AND s.level = 'supersector' GROUP BY s.name""", conn)
        for name, expected in EDD_SEP_2026.items():
            got = round(float(ca.loc[ca["name"] == name, "chg"].iloc[0]))
            errors += check(got == expected, f"CA 12-month  {name:38s} db={got:>+9,}  EDD={expected:>+9,}")

        us = pd.read_sql_query("""
            SELECT s.name,
                   1000 * (MAX(CASE WHEN month = '2026-10-01' THEN jobs_k END)
                         - MAX(CASE WHEN month = '2026-09-01' THEN jobs_k END)) AS chg
            FROM employment e JOIN series s USING (series_id)
            WHERE s.region = 'US' GROUP BY s.name""", conn)
        for name, expected in BLS_OCT_2026.items():
            got = round(float(us.loc[us["name"] == name, "chg"].iloc[0]))
            errors += check(got == expected, f"US October   {name:38s} db={got:>+9,}  BLS={expected:>+9,}")

        cuts = dict(conn.execute("SELECT month, cuts FROM layoffs_monthly WHERE industry = 'TOTAL'").fetchall())
        totals = dict(conn.execute("SELECT month, job_cuts FROM layoff_totals").fetchall())
        for month, expected in CHALLENGER_TOTALS.items():
            errors += check(cuts.get(month) == expected == totals.get(month),
                            f"Challenger total {month[:7]}: {cuts.get(month):,} (published {expected:,})")
        parts = conn.execute("""SELECT month, SUM(cuts) FROM layoffs_monthly
                                WHERE industry <> 'TOTAL' GROUP BY month""").fetchall()
        for month, s in parts:
            errors += check(s <= cuts[month], f"Challenger industries {month[:7]} sum {s:,} <= total {cuts[month]:,}")

        jo = conn.execute("SELECT openings_k FROM jolts WHERE industry = 'Total' AND month = '2026-09-01'").fetchone()[0]
        errors += check(jo == JOLTS_OPENINGS_SEP_2026_K, f"JOLTS openings Sep 2026: {jo:,}K")
        sup = conn.execute("""SELECT SUM(openings_k) FROM jolts
                              WHERE level = 'supersector' AND month = '2026-09-01'""").fetchone()[0]
        errors += check(abs(sup - jo) <= 3, f"JOLTS sectors add up to the total ({sup:,} vs {jo:,}, rounding)")

        for table, key in (("employment", "series_id"), ("stock_prices", "ticker")):
            g = pd.read_sql_query(f"SELECT {key} AS k, COUNT(*) AS n, MIN(month) AS a, MAX(month) AS b "
                                  f"FROM {table} GROUP BY {key}", conn)
            g["expected"] = [len(pd.date_range(a, b, freq="MS")) for a, b in zip(g["a"], g["b"])]
            bad = g[g["n"] != g["expected"]]
            errors += check(bad.empty, f"{table}: {len(g)} series, no missing months")
    print("all checks passed" if errors == 0 else f"{errors} check(s) failed")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
