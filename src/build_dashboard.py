"""Build the interactive dashboard: docs/index.html (GitHub Pages ready).

Reads data/ca_jobs.db, packs the numbers the page needs into one JSON blob and
injects it into dashboard/template.html. The page has no external dependencies.
"""
import json
import re
import sqlite3
from datetime import date

import pandas as pd

from config import CA_METROS_FOCUS, DB_PATH, DOCS, END_MONTH, PRE_PANDEMIC, ROOT, SQL_DIR, START_MONTH, STOCK_END, STOCK_START

SHORT = {
    "Private education & health services": "Education & health",
    "Leisure & hospitality": "Leisure & hospitality",
    "Trade, transportation & utilities": "Trade & transportation",
    "Government": "Government",
    "Other services": "Other services",
    "Mining & logging": "Mining & logging",
    "Construction": "Construction",
    "Professional & business services": "Professional & business",
    "Manufacturing": "Manufacturing",
    "Financial activities": "Finance & real estate",
    "Information": "Information (tech, media)",
    "Total nonfarm": "All jobs",
}


def q(conn, sql, params=()):
    return pd.read_sql_query(sql, conn, params=params)


def sectors(conn):
    df = q(conn, """
        SELECT s.name, s.level,
               MAX(CASE WHEN month = :feb THEN jobs_k END) AS feb20,
               MAX(CASE WHEN month = :start THEN jobs_k END) AS j21,
               MAX(CASE WHEN month = date(:end, '-1 year') THEN jobs_k END) AS j25,
               MAX(CASE WHEN month = :end THEN jobs_k END) AS j26
        FROM employment e JOIN series s USING (series_id)
        WHERE s.region = 'CA' AND s.level IN ('supersector', 'total')
        GROUP BY s.name, s.level""", {"feb": PRE_PANDEMIC, "start": START_MONTH, "end": END_MONTH})
    total = df.loc[df["level"] == "total"].iloc[0]
    rows = []
    for r in df.itertuples():
        rows.append({
            "name": r.name, "short": SHORT[r.name], "total": r.level == "total",
            "j21": r.j21, "j25": r.j25, "j26": r.j26,
            "chg5": round(r.j26 - r.j21, 1), "pct5": round(100 * (r.j26 - r.j21) / r.j21, 1),
            "chg12": round(r.j26 - r.j25, 1), "pct12": round(100 * (r.j26 - r.j25) / r.j25, 1),
            "idx20": round(100 * r.j26 / r.feb20, 1),
            "share26": round(100 * r.j26 / total.j26, 1),
        })
    return sorted(rows, key=lambda x: (not x["total"], -x["chg5"]))


def index_lines(conn):
    df = q(conn, """
        SELECT s.name, e.month, ROUND(100.0 * e.jobs_k / b.jobs_k, 2) AS idx, e.jobs_k
        FROM employment e
        JOIN employment b ON b.series_id = e.series_id AND b.month = :feb
        JOIN series s ON s.series_id = e.series_id
        WHERE s.region = 'CA' AND s.level IN ('supersector', 'total')
        ORDER BY s.name, e.month""", {"feb": PRE_PANDEMIC})
    return {n: g[["month", "idx", "jobs_k"]].values.tolist() for n, g in df.groupby("name")}


def spotlight(conn):
    df = q(conn, """
        SELECT s.name, s.seasonally_adjusted AS sa,
               MAX(CASE WHEN month = :start THEN jobs_k END) AS j21,
               MAX(CASE WHEN month = date(:end, '-1 year') THEN jobs_k END) AS j25,
               MAX(CASE WHEN month = :end THEN jobs_k END) AS j26
        FROM employment e JOIN series s USING (series_id)
        WHERE s.region = 'CA' AND s.level IN ('subsector', 'area') GROUP BY s.name, s.seasonally_adjusted""",
          {"start": START_MONTH, "end": END_MONTH})
    df["pct5"] = (100 * (df.j26 - df.j21) / df.j21).round(1)
    df["pct12"] = (100 * (df.j26 - df.j25) / df.j25).round(1)
    return df.sort_values("pct5", ascending=False).to_dict("records")


def postings(conn):
    df = q(conn, """
        SELECT state, substr(date, 1, 7) || '-01' AS month, ROUND(AVG(postings_index), 1) AS idx
        FROM postings_state GROUP BY state, month ORDER BY month""")
    return {s: g[["month", "idx"]].values.tolist() for s, g in df.groupby("state")}


def window_change(conn, table, key, names=None):
    df = q(conn, f"""
        WITH latest AS (SELECT MAX(date) d FROM {table}),
        n AS (SELECT {key} k, AVG(postings_index) v FROM {table}, latest
              WHERE date > date(latest.d, '-28 days') GROUP BY {key}),
        a AS (SELECT {key} k, AVG(postings_index) v FROM {table}, latest
              WHERE date > date(latest.d, '-1 year', '-28 days') AND date <= date(latest.d, '-1 year')
              GROUP BY {key})
        SELECT n.k AS name, ROUND(n.v, 1) AS now, ROUND(a.v, 1) AS ago,
               ROUND(100.0 * (n.v - a.v) / a.v, 1) AS pct
        FROM n JOIN a USING (k) ORDER BY pct DESC""")
    if names:
        df = df[df["name"].isin(names)]
    return df.to_dict("records")


def named_queries() -> dict:
    """The dashboard reuses the queries in sql/analysis_queries.sql, looked up by number."""
    text = (SQL_DIR / "analysis_queries.sql").read_text()
    parts = re.split(r"^-- (Q\d+): .*$", text, flags=re.M)
    return dict(zip(parts[1::2], parts[2::2]))


def records(conn, sql):
    df = pd.read_sql_query(sql, conn)
    return json.loads(df.to_json(orient="records"))


def extra(conn) -> dict:
    """California vs U.S., stock sectors and the last-three-months tables."""
    Q = named_queries()
    mom = {(r["region"], r["name"]): r for r in records(conn, Q["Q15"])}
    ca_us = records(conn, Q["Q13"])
    for r in ca_us:
        r["ca12"] = mom[("CA", r["name"])]["last_12m_pct"]
        r["us12"] = mom[("US", r["name"])]["last_12m_pct"]
    stocks = records(conn, Q["Q16"])
    m17 = {r["sector"]: r for r in records(conn, Q["Q17"])}
    m19 = {r["sector"]: r for r in records(conn, Q["Q19"])}
    for r in stocks:
        r.update(prior_12m_pct=m17[r["sector"]]["prior_12m_pct"], momentum_pp=m17[r["sector"]]["momentum_pp"],
                 max_drawdown_pct=m19[r["sector"]]["max_drawdown_pct"], lowest_month=m19[r["sector"]]["lowest_month"])
    lines = q(conn, """
        SELECT k.sector, p.month, ROUND(100.0 * p.adj_close / b.adj_close, 1) AS idx
        FROM stock_prices p
        JOIN stock_prices b ON b.ticker = p.ticker AND b.month = ?
        JOIN stock_sectors k ON k.ticker = p.ticker
        WHERE p.month >= ? AND p.month <= ? ORDER BY k.sector, p.month""", (STOCK_START, STOCK_START, STOCK_END))
    return {
        "ca_us": ca_us,
        "ca_share": records(conn, Q["Q14"]),
        "stocks": stocks,
        "stock_lines": {s: g[["month", "idx"]].values.tolist() for s, g in lines.groupby("sector")},
        "jobs_vs_stocks": records(conn, Q["Q20"]),
        "last3": records(conn, Q["Q21"]),
        "layoffs": records(conn, Q["Q22"]),
        "jolts": records(conn, Q["Q23"]),
        "scorecard": records(conn, Q["Q24"]),
        "layoff_totals": records(conn, "SELECT * FROM layoff_totals ORDER BY month"),
        "layoff_ytd": records(conn, "SELECT * FROM layoffs_ytd WHERE industry IN ('TOTAL', 'Technology')"),
        "layoff_reasons": records(conn, "SELECT * FROM layoff_reasons ORDER BY oct_2026 DESC"),
        "occ_top": records(conn, Q["Q25"]),
        "occ_growth": records(conn, Q["Q26"]),
        "majors": records(conn, "SELECT * FROM majors ORDER BY underemployment_pct"),
        "major_groups": records(conn, Q["Q28"]),
        "major_tests": records(conn, Q["Q29"]),
        "post_kpi": records(conn, """SELECT COUNT(*) AS postings, COUNT(DISTINCT company) AS companies,
                                     COUNT(DISTINCT source) AS platforms, (SELECT COUNT(*) FROM posting_companies) AS ats_companies, SUM(is_us) AS us, SUM(loc_bucket = 'Los Angeles area') AS la,
                                     SUM(is_us AND seniority IN ('Entry level', 'Internship')) AS us_junior,
                                     MAX(snapshot_date) AS snapshot FROM postings""")[0],
        "post_platforms": records(conn, Q["Q31"]),
        "post_families": records(conn, """SELECT family, SUM(is_us) AS us, SUM(loc_bucket = 'Los Angeles area') AS la,
                                          SUM(is_ca) AS ca, SUM(loc_bucket = 'Remote (U.S.)') AS remote_us,
                                          SUM(is_us AND seniority IN ('Entry level', 'Internship')) AS junior,
                                          SUM(is_us AND seniority = 'Senior & management') AS senior
                                          FROM postings GROUP BY family ORDER BY us DESC"""),
        "post_titles": records(conn, Q["Q34"]),
        "post_eng": records(conn, Q["Q35"]),
        "post_skills": records(conn, Q["Q39"]),
        "post_pay": records(conn, Q["Q40"]),
        "post_la": records(conn, Q["Q41"]),
        "post_sectors": records(conn, Q["Q37"]),
        "post_jobs": records(conn, Q["Q43"]),
        "sources": records(conn, "SELECT report, url FROM research_sources"),
        "short": SHORT,
    }


def main() -> None:
    with sqlite3.connect(DB_PATH) as conn:
        secs = sectors(conn)
        total = next(s for s in secs if s["total"])
        hc = q(conn, """
            SELECT MAX(CASE WHEN month = :end THEN jobs_k END) - MAX(CASE WHEN month = :start THEN jobs_k END) AS chg
            FROM employment WHERE series_id = 'SMS06000006562000001'""",
               {"start": START_MONTH, "end": END_MONTH}).iloc[0]["chg"]
        post = postings(conn)
        latest_post = q(conn, "SELECT MAX(date) d FROM postings_state").iloc[0]["d"]
        metros = window_change(conn, "postings_metro", "metro", CA_METROS_FOCUS + [
            "Oxnard-Thousand Oaks-Ventura, CA", "Fresno, CA"])
        for m in metros:
            m["short"] = m["name"].replace(", CA", "").split("-")[0]
        data = {
            "meta": {"start": START_MONTH, "end": END_MONTH, "postings_through": latest_post,
                     "built": date.today().isoformat()},
            "kpi": {
                "total_chg5": total["chg5"], "total_pct5": total["pct5"],
                "health_care_chg5": round(hc, 1),
                "health_care_share": round(100 * hc / total["chg5"], 1),
                "info_pct5": next(s["pct5"] for s in secs if s["name"] == "Information"),
                "ca_postings": post["CA"][-1][1], "us_postings": post["US"][-1][1],
            },
            "sectors": secs,
            "lines": index_lines(conn),
            "spotlight": spotlight(conn),
            "postings": post,
            "metros": metros,
            "occupations": window_change(conn, "postings_occ", "occupation"),
        }
        data.update(extra(conn))
        data["meta"]["stock_start"] = STOCK_START
        data["meta"]["stock_end"] = STOCK_END
    template = (ROOT / "dashboard" / "template.html").read_text()
    html = template.replace("/*__DATA__*/null", json.dumps(data, separators=(",", ":")))
    DOCS.mkdir(exist_ok=True)
    (DOCS / "index.html").write_text(html)
    print(f"wrote docs/index.html ({len(html) / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
