"""Check the database against figures published elsewhere.

1. California: the 12-month change by sector must match the EDD news release
   for September 2026 (Sep 2025 -> Sep 2026, seasonally adjusted, in jobs).
2. United States: October 2026 monthly changes must match the BLS
   Employment Situation release.
3. Hand-collected tables: monthly totals must match the published headline
   numbers (Challenger job cuts, JOLTS job openings).
4. Every series must have one value per month with no gaps.
5. Job postings: unique ids, platform totals add up, every posting classified, rule tests pass.
6. Year by year: FRED JOLTS matches the BLS table; Challenger annual figures match the industry table; no gaps.
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

        rn = conn.execute("SELECT openings_k FROM occupation_outlook WHERE code = '29-1141'").fetchone()[0]
        errors += check(rn == 180.8, f"BLS projections: registered nurses openings {rn}K per year")
        ov = conn.execute("SELECT unemployment_pct, underemployment_pct FROM majors WHERE major = 'Overall'").fetchone()
        errors += check(ov == (4.2, 39.4), f"NY Fed majors: overall unemployment {ov[0]}%, underemployment {ov[1]}%")
        n = conn.execute("SELECT COUNT(*), COUNT(DISTINCT major) FROM majors").fetchone()
        errors += check(n == (74, 74), f"NY Fed majors: {n[0]} rows, no duplicates")

        # Year by year (Part 7): FRED's JOLTS total must equal the hand-collected BLS release table.
        fred_sep, table_sep = conn.execute("""SELECT (SELECT value FROM fred_monthly WHERE series_id = 'JTSJOL' AND month = '2026-09-01'),
                                                     (SELECT openings_k FROM jolts WHERE industry = 'Total' AND month = '2026-09-01')""").fetchone()
        errors += check(fred_sep == table_sep, f"JOLTS Sep 2026 openings: FRED {fred_sep:,.0f} = BLS table {table_sep:,.0f} (thousands)")
        ann, ytd26, prior, ytd25 = conn.execute("""SELECT a.job_cuts, y.ytd_2026, a.prior_year_same_months, y.ytd_2025
                                                    FROM layoffs_annual a, layoffs_ytd y WHERE a.year = 2026 AND y.industry = 'TOTAL'""").fetchone()
        errors += check(ann == ytd26 and prior == ytd25, f"Challenger 2026 Jan-Oct: {ann:,} cuts against {int(prior):,} a year earlier, matches the industry table")
        short = conn.execute("""SELECT series_id, COUNT(*) FROM fred_monthly GROUP BY series_id HAVING COUNT(*) < 80""").fetchall()
        errors += check(not short, "FRED: every series has at least 80 months since Jan 2020" + (f" (short: {short})" if short else ""))
        occ_years = conn.execute("""SELECT COUNT(DISTINCT occupation) FROM postings_occ GROUP BY substr(date, 1, 4)""").fetchall()
        errors += check({n for (n,) in occ_years} == {47}, "Indeed: all 47 occupational categories in every year")
        trk = conn.execute("SELECT metric, MAX(date) FROM indeed_trackers GROUP BY metric").fetchall()
        errors += check(all(d >= "2026-09-01" for _, d in trk), "Indeed trackers (AI, remote, wages) reach autumn 2026: " + ", ".join(f"{m} {d}" for m, d in trk))

        n_post, n_ids = conn.execute("SELECT COUNT(*), COUNT(DISTINCT posting_id) FROM postings").fetchone()
        errors += check(n_post == n_ids and n_post > 30000, f"postings: {n_post:,} rows, ids unique")
        plat = conn.execute("SELECT SUM(postings) FROM posting_platforms").fetchone()[0]
        errors += check(plat == n_post, f"postings: platform totals add up ({plat:,})")
        blanks = conn.execute("SELECT COUNT(*) FROM postings WHERE family IS NULL OR loc_bucket IS NULL OR seniority IS NULL").fetchone()[0]
        errors += check(blanks == 0, "postings: every posting has a family, seniority and location bucket")
        bad_pay = conn.execute("SELECT COUNT(*) FROM postings WHERE pay_min > pay_max").fetchone()[0]
        errors += check(bad_pay == 0, "postings: pay ranges run low to high")
        orphan = conn.execute("""SELECT COUNT(*) FROM posting_skills s JOIN postings p USING (posting_id)
                                 WHERE p.desc_fetched = 0""").fetchone()[0]
        errors += check(orphan == 0, "postings: skills only on postings whose description was read")
        import subprocess
        rc = subprocess.run([sys.executable, str(DB_PATH.parents[1] / "tests" / "test_postings.py")], capture_output=True).returncode
        errors += check(rc == 0, "postings: classification rule tests pass")

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
