"""Make the PNG charts used in the README (charts/*.png)."""
import sqlite3

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from config import CHARTS, DB_PATH  # noqa: E402

# Palette (light mode): categorical slots 1-3, diverging poles, recessive greys.
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
NEG = "#e34948"
GREY = "#8a8984"
TEXT, TEXT2, GRID, SURFACE = "#0b0b0b", "#52514e", "#e6e5e1", "#fcfcfb"

plt.rcParams.update({
    "font.family": ["Inter", "DejaVu Sans"],
    "font.size": 10,
    "axes.edgecolor": GRID,
    "axes.labelcolor": TEXT2,
    "axes.titlesize": 13,
    "axes.titleweight": "semibold",
    "axes.titlecolor": TEXT,
    "axes.titlelocation": "left",
    "xtick.color": TEXT2,
    "ytick.color": TEXT2,
    "axes.grid": True,
    "grid.color": GRID,
    "grid.linewidth": 0.8,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "figure.facecolor": SURFACE,
    "axes.facecolor": SURFACE,
    "savefig.dpi": 160,
})


def q(conn, sql):
    return pd.read_sql_query(sql, conn)


def subtitle(ax, text):
    ax.text(0, 1.02, text, transform=ax.transAxes, color=TEXT2, fontsize=9.5, va="bottom")


def finish(fig, name, source):
    fig.text(0.01, -0.03, f"Source: {source}", color=TEXT2, fontsize=8)
    fig.savefig(CHARTS / name, bbox_inches="tight", facecolor=SURFACE)
    plt.close(fig)
    print(f"saved charts/{name}")


def hbar(ax, labels, values, fmt):
    colors = [BLUE if v >= 0 else NEG for v in values]
    ax.barh(labels, values, color=colors, height=0.55)
    ax.axvline(0, color=TEXT2, linewidth=0.8)
    ax.grid(axis="y", visible=False)
    ax.invert_yaxis()
    span = max(abs(v) for v in values)
    for i, v in enumerate(values):
        ax.text(v + (span * 0.015 if v >= 0 else -span * 0.015), i, fmt(v),
                va="center", ha="left" if v >= 0 else "right", color=TEXT, fontsize=9)
    lo, hi = min(values + [0]), max(values + [0])
    ax.set_xlim(lo - span * 0.14 if lo < 0 else 0, hi + span * 0.16)
    ax.set_axisbelow(True)


def chart_five_year(conn):
    df = q(conn, """
        SELECT s.name,
               MAX(CASE WHEN month='2026-09-01' THEN jobs_k END)
             - MAX(CASE WHEN month='2021-09-01' THEN jobs_k END) AS chg
        FROM employment e JOIN series s USING (series_id)
        WHERE s.level='supersector' GROUP BY s.name ORDER BY chg DESC""")
    fig, ax = plt.subplots(figsize=(9, 5.2))
    hbar(ax, df["name"].tolist(), df["chg"].round(1).tolist(),
         lambda v: f"{v:+,.0f}K")
    ax.set_title("Health care and education added two-thirds of California's new jobs", pad=26)
    subtitle(ax, "Change in payroll jobs by sector, Sep 2021 to Sep 2026 (thousands)")
    ax.set_xlabel("Thousands of jobs")
    finish(fig, "01_five_year_change.png", "BLS Current Employment Statistics via FRED, seasonally adjusted")


def chart_recovery(conn):
    df = q(conn, """
        SELECT e.month, s.name, 100.0 * e.jobs_k / b.jobs_k AS idx
        FROM employment e
        JOIN employment b ON b.series_id = e.series_id AND b.month = '2020-02-01'
        JOIN series s ON s.series_id = e.series_id
        WHERE s.series_id IN ('CANA','CAEDUH','SMS06000005000000001','CAMFG')""")
    df["month"] = pd.to_datetime(df["month"])
    order = [("Private education & health services", BLUE, "Education & health"),
             ("Information", ORANGE, "Information (tech, media)"),
             ("Manufacturing", AQUA, "Manufacturing"),
             ("Total nonfarm", GREY, "All jobs")]
    fig, ax = plt.subplots(figsize=(9, 5.2))
    for name, color, label in order:
        d = df[df["name"] == name].sort_values("month")
        ax.plot(d["month"], d["idx"], color=color, linewidth=2, solid_capstyle="round")
        last = d.iloc[-1]
        ax.scatter([last["month"]], [last["idx"]], s=36, color=color, edgecolor=SURFACE, linewidth=1.5, zorder=3)
        ax.annotate(f"{label}  {last['idx']:.0f}", (last["month"], last["idx"]),
                    xytext=(8, 0), textcoords="offset points", va="center", color=TEXT, fontsize=9)
    ax.axhline(100, color=TEXT2, linewidth=0.8)
    ax.axvspan(pd.Timestamp("2021-09-01"), pd.Timestamp("2026-09-01"), color=BLUE, alpha=0.05, linewidth=0)
    ax.set_xlim(pd.Timestamp("2020-01-01"), pd.Timestamp("2028-06-01"))
    ax.set_xticks([pd.Timestamp(f"{y}-01-01") for y in range(2020, 2027)], [str(y) for y in range(2020, 2027)])
    ax.set_title("Education & health kept growing; tech and media never recovered", pad=26)
    subtitle(ax, "California payroll jobs, indexed to February 2020 = 100 (shaded: the 5-year window)")
    ax.set_ylabel("Index (Feb 2020 = 100)")
    finish(fig, "02_recovery_index.png", "BLS Current Employment Statistics via FRED, seasonally adjusted")


def chart_postings(conn):
    df = q(conn, """
        SELECT substr(date,1,7)||'-01' AS month, state, AVG(postings_index) AS idx
        FROM postings_state GROUP BY month, state""")
    df["month"] = pd.to_datetime(df["month"])
    fig, ax = plt.subplots(figsize=(9, 5.2))
    for st, color, label in (("US", ORANGE, "United States"), ("CA", BLUE, "California")):
        d = df[df["state"] == st].sort_values("month")
        ax.plot(d["month"], d["idx"], color=color, linewidth=2)
        last = d.iloc[-1]
        ax.scatter([last["month"]], [last["idx"]], s=36, color=color, edgecolor=SURFACE, linewidth=1.5, zorder=3)
        ax.annotate(f"{label}  {last['idx']:.0f}", (last["month"], last["idx"]),
                    xytext=(8, 0), textcoords="offset points", va="center", color=TEXT, fontsize=9)
    ax.axhline(100, color=TEXT2, linewidth=0.8)
    ax.set_xlim(pd.Timestamp("2020-02-01"), pd.Timestamp("2027-10-01"))
    ax.set_xticks([pd.Timestamp(f"{y}-01-01") for y in range(2021, 2027)], [str(y) for y in range(2021, 2027)])
    ax.set_title("California job postings are still below 2020; the U.S. is back above", pad=26)
    subtitle(ax, "Indeed job postings, monthly average, indexed to Feb 1, 2020 = 100")
    ax.set_ylabel("Index (Feb 2020 = 100)")
    finish(fig, "03_postings_ca_vs_us.png", "Indeed Hiring Lab, seasonally adjusted (data through Nov 6, 2026)")


def window_change(conn, table, key, where=""):
    return q(conn, f"""
        WITH latest AS (SELECT MAX(date) d FROM {table}),
        n AS (SELECT {key} k, AVG(postings_index) v FROM {table}, latest
              WHERE date > date(latest.d,'-28 days') {where} GROUP BY {key}),
        a AS (SELECT {key} k, AVG(postings_index) v FROM {table}, latest
              WHERE date > date(latest.d,'-1 year','-28 days') AND date <= date(latest.d,'-1 year') {where}
              GROUP BY {key})
        SELECT n.k AS name, 100.0*(n.v-a.v)/a.v AS pct, n.v AS idx_now
        FROM n JOIN a USING (k) ORDER BY pct DESC""")


def chart_metros(conn):
    big = ("'Los Angeles-Long Beach-Anaheim, CA','San Francisco-Oakland-Berkeley, CA',"
           "'San Jose-Sunnyvale-Santa Clara, CA','San Diego-Chula Vista-Carlsbad, CA',"
           "'Riverside-San Bernardino-Ontario, CA','Sacramento-Roseville-Folsom, CA',"
           "'Oxnard-Thousand Oaks-Ventura, CA','Fresno, CA'")
    df = window_change(conn, "postings_metro", "metro", f"AND metro IN ({big})")
    df["name"] = df["name"].str.replace(", CA", "").str.split("-").str[0]
    fig, ax = plt.subplots(figsize=(9, 4.6))
    hbar(ax, df["name"].tolist(), df["pct"].round(1).tolist(), lambda v: f"{v:+.1f}%")
    ax.set_title("Bay Area postings bounced back; Los Angeles is flat", pad=26)
    subtitle(ax, "Change in Indeed job postings, last 28 days vs the same 28 days a year earlier")
    ax.set_xlabel("Percent change")
    finish(fig, "04_metro_postings.png", "Indeed Hiring Lab metro postings (data through Nov 6, 2026)")


def chart_occupations(conn):
    df = window_change(conn, "postings_occ", "occupation")
    keep = pd.concat([df.head(6), df[df["name"].isin(["Data & Analytics", "Nursing",
                     "Medical Information", "Software Development"])], df.tail(5)]).drop_duplicates("name")
    keep = keep.sort_values("pct", ascending=False)
    fig, ax = plt.subplots(figsize=(9, 5.6))
    hbar(ax, keep["name"].tolist(), keep["pct"].round(1).tolist(), lambda v: f"{v:+.1f}%")
    for lbl in ax.get_yticklabels():
        if lbl.get_text() == "Data & Analytics":
            lbl.set_fontweight("bold")
    ax.set_title("Engineering and software postings rose most; Data & Analytics up modestly", pad=26)
    subtitle(ax, "U.S. Indeed postings by occupation, last 28 days vs a year earlier (top 6, bottom 5, and roles to watch)")
    ax.set_xlabel("Percent change")
    finish(fig, "05_occupation_postings.png", "Indeed Hiring Lab occupational categories, U.S. (data through Nov 6, 2026)")


def main() -> None:
    CHARTS.mkdir(exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        chart_five_year(conn)
        chart_recovery(conn)
        chart_postings(conn)
        chart_metros(conn)
        chart_occupations(conn)


if __name__ == "__main__":
    main()
