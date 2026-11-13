"""Build the interactive dashboard: docs/index.html (GitHub Pages ready).

Reads data/ca_jobs.db, packs the numbers the page needs into one JSON blob and
injects it into dashboard/template.html. The page has no external dependencies.
"""
import json
import sqlite3
from datetime import date

import pandas as pd

from config import CA_METROS_FOCUS, DB_PATH, DOCS, END_MONTH, PRE_PANDEMIC, ROOT, START_MONTH

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
        WHERE s.level IN ('supersector', 'total')
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
        WHERE s.level IN ('supersector', 'total')
        ORDER BY s.name, e.month""", {"feb": PRE_PANDEMIC})
    return {n: g[["month", "idx", "jobs_k"]].values.tolist() for n, g in df.groupby("name")}


def spotlight(conn):
    df = q(conn, """
        SELECT s.name, s.seasonally_adjusted AS sa,
               MAX(CASE WHEN month = :start THEN jobs_k END) AS j21,
               MAX(CASE WHEN month = date(:end, '-1 year') THEN jobs_k END) AS j25,
               MAX(CASE WHEN month = :end THEN jobs_k END) AS j26
        FROM employment e JOIN series s USING (series_id)
        WHERE s.level IN ('subsector', 'area') GROUP BY s.name, s.seasonally_adjusted""",
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
    template = (ROOT / "dashboard" / "template.html").read_text()
    html = template.replace("/*__DATA__*/null", json.dumps(data, separators=(",", ":")))
    DOCS.mkdir(exist_ok=True)
    (DOCS / "index.html").write_text(html)
    print(f"wrote docs/index.html ({len(html) / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
