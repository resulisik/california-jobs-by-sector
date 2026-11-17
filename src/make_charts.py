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


def finish(fig, name, source, y=-0.03):
    fig.text(0.01, y, f"Source: {source}", color=TEXT2, fontsize=8)
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
        WHERE s.region='CA' AND s.level='supersector' GROUP BY s.name ORDER BY chg DESC""")
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


def chart_ca_vs_us(conn):
    df = q(conn, """
        SELECT s.region, s.name,
               100.0 * (MAX(CASE WHEN month='2026-09-01' THEN jobs_k END)
                      / MAX(CASE WHEN month='2021-09-01' THEN jobs_k END) - 1) AS pct
        FROM employment e JOIN series s USING (series_id)
        WHERE s.level='supersector' GROUP BY s.region, s.name""")
    w = df.pivot(index="name", columns="region", values="pct")
    w = w.assign(gap=w["CA"] - w["US"]).sort_values("gap")
    fig, ax = plt.subplots(figsize=(9, 6))
    y = range(len(w))
    ax.barh([i + 0.2 for i in y], w["CA"], height=0.36, color=BLUE, label="California")
    ax.barh([i - 0.2 for i in y], w["US"], height=0.36, color=ORANGE, label="United States")
    for i, (ca, us) in enumerate(zip(w["CA"], w["US"])):
        for v, dy in ((ca, 0.2), (us, -0.2)):
            ax.text(v + (0.4 if v >= 0 else -0.4), i + dy, f"{v:+.1f}%", va="center",
                    ha="left" if v >= 0 else "right", fontsize=8.5, color=TEXT)
    ax.set_yticks(list(y), w.index)
    ax.axvline(0, color=TEXT2, linewidth=0.8)
    ax.grid(axis="y", visible=False)
    ax.set_axisbelow(True)
    ax.set_xlim(w[["CA", "US"]].min().min() - 4, w[["CA", "US"]].max().max() + 5)
    ax.legend(frameon=False, loc="lower right")
    ax.set_title("California beats the U.S. in health care and little else", pad=26)
    subtitle(ax, "Change in payroll jobs by sector, Sep 2021 to Sep 2026 (percent)")
    finish(fig, "06_california_vs_us.png", "BLS Current Employment Statistics via FRED, seasonally adjusted")


def stock_returns(conn):
    return q(conn, """
        SELECT k.sector, k.ticker, k.jobs_sector,
               100.0 * (n.adj_close / a.adj_close - 1) AS r5,
               100.0 * (n.adj_close / b.adj_close - 1) AS r1,
               100.0 * (b.adj_close / c.adj_close - 1) AS r1_prior
        FROM stock_sectors k
        JOIN stock_prices n ON n.ticker = k.ticker AND n.month = '2026-10-01'
        JOIN stock_prices a ON a.ticker = k.ticker AND a.month = '2021-10-01'
        JOIN stock_prices b ON b.ticker = k.ticker AND b.month = '2025-10-01'
        JOIN stock_prices c ON c.ticker = k.ticker AND c.month = '2024-10-01'
        ORDER BY r5 DESC""")


def chart_stock_returns(conn):
    df = stock_returns(conn)
    fig, axes = plt.subplots(1, 2, figsize=(11, 5.4))
    for ax, col, title in ((axes[0], "r5", "5 years (Oct 2021 to Oct 2026)"), (axes[1], "r1", "Last 12 months")):
        hbar(ax, df["sector"].tolist(), df[col].round(1).tolist(), lambda v: f"{v:+.0f}%")
        ax.set_xlabel(title)
    axes[1].set_yticklabels([])
    axes[1].tick_params(axis="y", length=0)
    for lbl in axes[0].get_yticklabels():
        if lbl.get_text().startswith("S&P"):
            lbl.set_fontweight("bold")
    axes[0].set_title("Energy and technology led over five years; the last year looks different", pad=26)
    subtitle(axes[0], "Total return of S&P 500 sector funds, dividends reinvested (percent)")
    fig.subplots_adjust(wspace=0.08)
    finish(fig, "07_stock_sector_returns.png", "Yahoo Finance month-end adjusted prices (SPDR sector funds, SPY). Not investment advice.")


def chart_jobs_vs_stocks(conn):
    df = stock_returns(conn)
    jobs = q(conn, """
        SELECT s.name AS jobs_sector,
               100.0 * (MAX(CASE WHEN month='2026-10-01' THEN jobs_k END)
                      / MAX(CASE WHEN month='2021-10-01' THEN jobs_k END) - 1) AS j5
        FROM employment e JOIN series s USING (series_id)
        WHERE s.region='US' AND s.level IN ('supersector','total') GROUP BY s.name""")
    df = df.merge(jobs, on="jobs_sector")
    fig, ax = plt.subplots(figsize=(9, 5.6))
    ax.axhline(0, color=TEXT2, linewidth=0.8)
    ax.axvline(0, color=TEXT2, linewidth=0.8)
    offsets = {"Financials": (-8, 6, "right"), "Materials": (-8, -4, "right"), "Utilities": (8, 8, "left"),
               "Consumer staples": (8, -10, "left"), "Communication services": (-6, -14, "left")}
    for r in df.itertuples():
        color = GREY if r.ticker == "SPY" else BLUE
        ax.scatter([r.j5], [r.r5], s=64, color=color, edgecolor=SURFACE, linewidth=1.5, zorder=3)
        dx, dy, ha = offsets.get(r.sector, (8, 0, "left"))
        ax.annotate(r.sector.replace(" (all sectors)", ""), (r.j5, r.r5), xytext=(dx, dy),
                    textcoords="offset points", va="center", ha=ha, fontsize=9, color=TEXT)
    ax.set_xlim(df["j5"].min() - 3, df["j5"].max() + 5)
    ax.set_xlabel("U.S. job growth in the closest jobs sector, 5 years (%)")
    ax.set_ylabel("Stock sector total return, 5 years (%)")
    ax.set_title("Stock returns do not follow jobs: tech stocks soared while tech jobs fell", pad=26)
    subtitle(ax, "Each dot is a stock sector, Oct 2021 to Oct 2026. The sector match is approximate.")
    finish(fig, "08_jobs_vs_stocks.png", "BLS via FRED; Yahoo Finance month-end adjusted prices")


def chart_last_three_months(conn):
    df = q(conn, """
        SELECT s.name,
               MAX(CASE WHEN month='2026-10-01' THEN jobs_k END)
             - MAX(CASE WHEN month='2026-07-01' THEN jobs_k END) AS chg
        FROM employment e JOIN series s USING (series_id)
        WHERE s.region='US' AND s.level='supersector' GROUP BY s.name ORDER BY chg DESC""")
    fig, ax = plt.subplots(figsize=(9, 5.2))
    hbar(ax, df["name"].tolist(), df["chg"].round(0).tolist(), lambda v: f"{v:+,.0f}K")
    ax.set_title("U.S. hiring in the last three months: health care and business services lead", pad=26)
    subtitle(ax, "Change in U.S. payroll jobs by sector, July to October 2026 (thousands)")
    ax.set_xlabel("Thousands of jobs")
    finish(fig, "09_us_last_three_months.png", "BLS Employment Situation via FRED, seasonally adjusted")


def chart_top_occupations(conn):
    df = q(conn, """
        SELECT field, title, openings_k,
               ROW_NUMBER() OVER (PARTITION BY field ORDER BY openings_k DESC) AS rn
        FROM occupation_outlook WHERE field IS NOT NULL""")
    df = df[df["rn"] <= 5]
    fields = ["Engineering", "Health care", "Finance", "Computer & data", "Film & media"]
    fig, axes = plt.subplots(5, 1, figsize=(9, 11))
    for ax, field in zip(axes, fields):
        d = df[df["field"] == field].sort_values("openings_k", ascending=False)
        labels = [x if len(x) < 44 else x[:42] + "…" for x in d["title"]]
        hbar(ax, labels, d["openings_k"].tolist(), lambda v: f"{v:,.1f}K")
        ax.set_ylabel(field, fontweight="semibold", color=TEXT)
    axes[0].set_title("Top five occupations by yearly job openings in each field", pad=26)
    subtitle(axes[0], "Projected openings per year, 2025-35 average (thousands). Each panel has its own scale.")
    fig.subplots_adjust(hspace=0.45)
    finish(fig, "10_top_occupations_by_field.png", "BLS Employment Projections 2025-35, Table 1.10", y=0.07)


def chart_majors(conn):
    df = q(conn, "SELECT major, underemployment_pct FROM majors WHERE major <> 'Overall' ORDER BY underemployment_pct")
    overall = q(conn, "SELECT underemployment_pct FROM majors WHERE major = 'Overall'").iloc[0, 0]
    d = pd.concat([df.head(10), df.tail(10)])
    fig, ax = plt.subplots(figsize=(9, 6.6))
    colors = [BLUE] * 10 + [ORANGE] * 10
    ax.barh(d["major"], d["underemployment_pct"], color=colors, height=0.6)
    ax.invert_yaxis()
    ax.grid(axis="y", visible=False)
    ax.set_axisbelow(True)
    for i, v in enumerate(d["underemployment_pct"]):
        ax.text(v + 0.8, i, f"{v:.1f}%", va="center", fontsize=9, color=TEXT)
    ax.axvline(overall, color=TEXT2, linewidth=1, linestyle="--")
    ax.text(overall + 0.6, 9.5, f"all graduates {overall:.1f}%", color=TEXT2, fontsize=9, va="center")
    ax.set_xlim(0, 75)
    ax.set_xlabel("Recent graduates working in jobs that do not require a degree (%)")
    ax.set_title("The major matters: underemployment runs from 13% to 66%", pad=26)
    subtitle(ax, "Ten majors with the lowest (blue) and ten with the highest (orange) underemployment, graduates aged 22-27, 2024")
    finish(fig, "11_majors_underemployment.png", "Federal Reserve Bank of New York, The Labor Market for Recent College Graduates")


POSTINGS_SOURCE = ("public job APIs of Greenhouse, Ashby, Lever and SmartRecruiters (283 employers' careers pages) "
                   "and the remote job boards Remotive, Remote OK and Jobicy, collected 17 Nov 2026")


def chart_posting_families(conn):
    df = q(conn, """SELECT family, COUNT(*) AS n,
                           100.0 * SUM(seniority IN ('Entry level', 'Internship')) / COUNT(*) AS junior
                    FROM postings WHERE is_us = 1 GROUP BY family ORDER BY n DESC""")
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(10, 6), sharey=True, gridspec_kw={"width_ratios": [1.5, 1]})
    hbar(a1, df["family"].tolist(), df["n"].tolist(), lambda v: f"{v:,.0f}")
    hbar(a2, df["family"].tolist(), df["junior"].tolist(), lambda v: f"{v:.1f}%")
    a2.invert_yaxis()  # shared axis was already inverted by the first panel
    for ax, lab in ((a1, "U.S. postings"), (a2, "Entry level or internship (% of the family)")):
        ax.set_xlabel(lab)
    a1.get_yticklabels()[df.index[df["family"] == "Data & analytics"][0]].set_fontweight("bold")
    a1.set_title("What employers are hiring for, and how much of it is junior", pad=26)
    subtitle(a1, f"{df['n'].sum():,} U.S. job postings by job family (keyword rules on the title). Each panel has its own scale.")
    fig.subplots_adjust(wspace=0.08)
    finish(fig, "12_postings_by_family.png", POSTINGS_SOURCE)


def chart_posting_skills(conn):
    df = q(conn, """WITH d AS (SELECT posting_id FROM postings
                               WHERE family = 'Data & analytics' AND desc_fetched = 1 AND is_us = 1)
                    SELECT skill, 100.0 * COUNT(*) / (SELECT COUNT(*) FROM d) AS pct, (SELECT COUNT(*) FROM d) AS n
                    FROM posting_skills JOIN d USING (posting_id) GROUP BY skill ORDER BY pct DESC""")
    names = {"sql": "SQL", "python": "Python", "statistics": "Statistics", "machine_learning": "Machine learning",
             "ab_testing": "A/B testing", "dbt": "dbt", "snowflake": "Snowflake", "tableau": "Tableau", "r": "R", "spark": "Spark",
             "looker": "Looker", "airflow": "Airflow", "excel": "Excel", "aws": "AWS", "bigquery": "BigQuery", "power_bi": "Power BI"}
    fig, ax = plt.subplots(figsize=(9, 6))
    hbar(ax, [names.get(s, s) for s in df["skill"]], df["pct"].tolist(), lambda v: f"{v:.0f}%")
    ax.set_xlabel("Share of postings whose description names the skill (%)")
    ax.set_title("SQL and Python lead the skills named in data & analytics postings", pad=26)
    subtitle(ax, f"{int(df['n'].iloc[0]):,} U.S. data & analytics postings whose description was read")
    finish(fig, "13_data_posting_skills.png", POSTINGS_SOURCE)


def main() -> None:
    CHARTS.mkdir(exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        chart_five_year(conn)
        chart_recovery(conn)
        chart_postings(conn)
        chart_metros(conn)
        chart_occupations(conn)
        chart_ca_vs_us(conn)
        chart_stock_returns(conn)
        chart_jobs_vs_stocks(conn)
        chart_last_three_months(conn)
        chart_top_occupations(conn)
        chart_majors(conn)
        chart_posting_families(conn)
        chart_posting_skills(conn)


if __name__ == "__main__":
    main()
