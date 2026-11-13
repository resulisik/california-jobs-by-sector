"""Check the database against figures published elsewhere.

1. The 12-month change by sector must match the EDD news release for
   September 2026 (Sep 2025 -> Sep 2026, seasonally adjusted, in jobs).
2. Every series must have one value per month with no gaps.
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


def main() -> int:
    errors = 0
    with sqlite3.connect(DB_PATH) as conn:
        df = pd.read_sql_query("""
            SELECT s.name,
                   1000 * (MAX(CASE WHEN month = '2026-09-01' THEN jobs_k END)
                         - MAX(CASE WHEN month = '2025-09-01' THEN jobs_k END)) AS chg
            FROM employment e JOIN series s USING (series_id)
            WHERE s.level = 'supersector' GROUP BY s.name""", conn)
        for name, expected in EDD_SEP_2026.items():
            got = round(float(df.loc[df["name"] == name, "chg"].iloc[0]))
            ok = got == expected
            errors += not ok
            print(f"{'ok ' if ok else 'BAD'} {name:38s} db={got:>+9,}  EDD={expected:>+9,}")

        gaps = pd.read_sql_query("""
            SELECT series_id, COUNT(*) AS n, MIN(month) AS first, MAX(month) AS last
            FROM employment GROUP BY series_id""", conn)
        expected_n = len(pd.date_range(gaps["first"].min(), gaps["last"].max(), freq="MS"))
        bad = gaps[gaps["n"] != expected_n]
        errors += len(bad)
        print(f"{'ok ' if bad.empty else 'BAD'} {len(gaps)} series x {expected_n} months, no gaps")
    print("all checks passed" if errors == 0 else f"{errors} check(s) failed")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
