-- Sector Pulse: jobs and stock market by sector, California and the U.S., 2021 - 2026
-- Database: data/sectors.db (built by src/build_database.py)
-- jobs_k = thousands of jobs. postings_index = Indeed postings, Feb 1 2020 = 100.
-- adj_close = month-end price with dividends reinvested. Months are stored as YYYY-MM-01.
-- Q1-Q12 California, Q13-Q15 California vs U.S., Q16-Q20 stock sectors, Q21-Q24 last three months,
-- Q25-Q30 occupations and college majors.
-- Each query starts with a "-- Qn: title" line so src/run_queries.py can split the file.

-- Q1: Five-year job change by sector (Sep 2021 -> Sep 2026)
WITH ends AS (
    SELECT s.name,
           MAX(CASE WHEN e.month = '2021-09-01' THEN e.jobs_k END) AS jobs_2021,
           MAX(CASE WHEN e.month = '2026-09-01' THEN e.jobs_k END) AS jobs_2026
    FROM employment e
    JOIN series s USING (series_id)
    WHERE s.region = 'CA' AND s.level IN ('supersector', 'total')
    GROUP BY s.name
)
SELECT name,
       jobs_2021,
       jobs_2026,
       ROUND(jobs_2026 - jobs_2021, 1)                         AS change_k,
       ROUND(100.0 * (jobs_2026 - jobs_2021) / jobs_2021, 1)   AS change_pct,
       RANK() OVER (ORDER BY jobs_2026 - jobs_2021 DESC)       AS rank_by_change
FROM ends
ORDER BY (name = 'Total nonfarm') DESC, change_k DESC;

-- Q2: Last 12 months by sector (Sep 2025 -> Sep 2026), matches the EDD release
WITH yoy AS (
    SELECT s.name, e.month, e.jobs_k,
           e.jobs_k - LAG(e.jobs_k, 12) OVER (PARTITION BY e.series_id ORDER BY e.month) AS change_k
    FROM employment e
    JOIN series s USING (series_id)
    WHERE s.region = 'CA' AND s.level IN ('supersector', 'total')
)
SELECT name,
       jobs_k                                   AS jobs_sep_2026,
       ROUND(change_k, 1)                       AS change_12m_k,
       ROUND(100.0 * change_k / (jobs_k - change_k), 1) AS change_12m_pct
FROM yoy
WHERE month = '2026-09-01'
ORDER BY (name = 'Total nonfarm') DESC, change_12m_k DESC;

-- Q3: Recovery since before the pandemic (Feb 2020 = 100)
WITH base AS (
    SELECT series_id, jobs_k AS feb_2020 FROM employment WHERE month = '2020-02-01'
)
SELECT s.name,
       b.feb_2020,
       e.jobs_k                                    AS sep_2026,
       ROUND(100.0 * e.jobs_k / b.feb_2020, 1)     AS index_feb2020_100,
       CASE WHEN e.jobs_k >= b.feb_2020 THEN 'above' ELSE 'still below' END AS status
FROM employment e
JOIN base b USING (series_id)
JOIN series s USING (series_id)
WHERE e.month = '2026-09-01' AND s.region = 'CA' AND s.level IN ('supersector', 'total')
ORDER BY index_feb2020_100 DESC;

-- Q4: Each sector's share of all California jobs, 2021 vs 2026
WITH totals AS (
    SELECT month, jobs_k AS total_k FROM employment WHERE series_id = 'CANA'
), shares AS (
    SELECT s.name, e.month, 100.0 * e.jobs_k / t.total_k AS share_pct
    FROM employment e
    JOIN totals t USING (month)
    JOIN series s USING (series_id)
    WHERE s.region = 'CA' AND s.level = 'supersector' AND e.month IN ('2021-09-01', '2026-09-01')
)
SELECT name,
       ROUND(MAX(CASE WHEN month = '2021-09-01' THEN share_pct END), 1) AS share_2021,
       ROUND(MAX(CASE WHEN month = '2026-09-01' THEN share_pct END), 1) AS share_2026,
       ROUND(MAX(CASE WHEN month = '2026-09-01' THEN share_pct END)
           - MAX(CASE WHEN month = '2021-09-01' THEN share_pct END), 2) AS change_pp
FROM shares
GROUP BY name
ORDER BY change_pp DESC;

-- Q5: How much of California's net job growth came from health care?
WITH chg AS (
    SELECT series_id,
           MAX(CASE WHEN month = '2021-09-01' THEN jobs_k END) AS j21,
           MAX(CASE WHEN month = '2025-09-01' THEN jobs_k END) AS j25,
           MAX(CASE WHEN month = '2026-09-01' THEN jobs_k END) AS j26
    FROM employment
    WHERE series_id IN ('CANA', 'SMS06000006562000001')
    GROUP BY series_id
)
SELECT '5 years (Sep 2021-Sep 2026)' AS period,
       ROUND(h.j26 - h.j21, 1) AS health_care_change_k,
       ROUND(t.j26 - t.j21, 1) AS all_jobs_change_k,
       ROUND(100.0 * (h.j26 - h.j21) / (t.j26 - t.j21), 1) AS health_care_share_pct
FROM chg h, chg t WHERE h.series_id = 'SMS06000006562000001' AND t.series_id = 'CANA'
UNION ALL
SELECT 'Last 12 months (Sep 2025-Sep 2026)',
       ROUND(h.j26 - h.j25, 1), ROUND(t.j26 - t.j25, 1),
       ROUND(100.0 * (h.j26 - h.j25) / (t.j26 - t.j25), 1)
FROM chg h, chg t WHERE h.series_id = 'SMS06000006562000001' AND t.series_id = 'CANA';

-- Q6: Industry spotlight (same-month comparisons, so unadjusted series are fair)
WITH pts AS (
    SELECT series_id,
           MAX(CASE WHEN month = '2021-09-01' THEN jobs_k END) AS j21,
           MAX(CASE WHEN month = '2025-09-01' THEN jobs_k END) AS j25,
           MAX(CASE WHEN month = '2026-09-01' THEN jobs_k END) AS j26
    FROM employment GROUP BY series_id
)
SELECT s.name,
       p.j26                                     AS jobs_sep_2026,
       ROUND(100.0 * (p.j26 - p.j21) / p.j21, 1) AS change_5y_pct,
       ROUND(100.0 * (p.j26 - p.j25) / p.j25, 1) AS change_12m_pct,
       CASE WHEN p.j26 > p.j25 AND p.j26 > p.j21 THEN 'growing'
            WHEN p.j26 < p.j25 AND p.j26 < p.j21 THEN 'shrinking'
            ELSE 'mixed' END                     AS trend
FROM pts p JOIN series s USING (series_id)
WHERE s.region = 'CA' AND s.level IN ('subsector', 'area')
ORDER BY change_5y_pct DESC;

-- Q7: Year-by-year change, September to September (thousands of jobs)
WITH yoy AS (
    SELECT s.name, e.month,
           e.jobs_k - LAG(e.jobs_k, 12) OVER (PARTITION BY e.series_id ORDER BY e.month) AS chg
    FROM employment e JOIN series s USING (series_id)
    WHERE s.region = 'CA' AND s.level IN ('supersector', 'total')
)
SELECT name,
       ROUND(MAX(CASE WHEN month = '2022-09-01' THEN chg END), 1) AS y2022,
       ROUND(MAX(CASE WHEN month = '2023-09-01' THEN chg END), 1) AS y2023,
       ROUND(MAX(CASE WHEN month = '2024-09-01' THEN chg END), 1) AS y2024,
       ROUND(MAX(CASE WHEN month = '2025-09-01' THEN chg END), 1) AS y2025,
       ROUND(MAX(CASE WHEN month = '2026-09-01' THEN chg END), 1) AS y2026
FROM yoy
GROUP BY name
ORDER BY (name = 'Total nonfarm') DESC, y2026 DESC;

-- Q8: Losing streaks - of the last 24 months, how many were below the same month a year earlier?
WITH yoy AS (
    SELECT s.name, e.month,
           e.jobs_k - LAG(e.jobs_k, 12) OVER (PARTITION BY e.series_id ORDER BY e.month) AS chg
    FROM employment e JOIN series s USING (series_id)
    WHERE s.region = 'CA'
)
SELECT name,
       SUM(CASE WHEN chg < 0 THEN 1 ELSE 0 END) AS months_down_of_24,
       SUM(CASE WHEN chg > 0 THEN 1 ELSE 0 END) AS months_up_of_24
FROM yoy
WHERE month > '2024-09-01' AND month <= '2026-09-01'
GROUP BY name
ORDER BY months_down_of_24 DESC, name;

-- Q9: Job postings on Indeed - California vs U.S., yearly average (Feb 2020 = 100)
SELECT substr(date, 1, 4)                                                   AS year,
       ROUND(AVG(CASE WHEN state = 'CA' THEN postings_index END), 1)        AS california,
       ROUND(AVG(CASE WHEN state = 'US' THEN postings_index END), 1)        AS united_states,
       ROUND(AVG(CASE WHEN state = 'CA' THEN postings_index END)
           - AVG(CASE WHEN state = 'US' THEN postings_index END), 1)        AS ca_minus_us,
       MAX(date)                                                            AS data_through
FROM postings_state
WHERE date >= '2021-01-01'
GROUP BY year
ORDER BY year;

-- Q10: Big California metros - postings now vs one year ago and vs Feb 2020 (28-day averages)
WITH latest AS (SELECT MAX(date) AS d FROM postings_metro),
big AS (
    SELECT 'Los Angeles-Long Beach-Anaheim, CA' AS metro UNION ALL
    SELECT 'San Francisco-Oakland-Berkeley, CA' UNION ALL
    SELECT 'San Jose-Sunnyvale-Santa Clara, CA' UNION ALL
    SELECT 'San Diego-Chula Vista-Carlsbad, CA' UNION ALL
    SELECT 'Riverside-San Bernardino-Ontario, CA' UNION ALL
    SELECT 'Sacramento-Roseville-Folsom, CA' UNION ALL
    SELECT 'Oxnard-Thousand Oaks-Ventura, CA' UNION ALL
    SELECT 'Fresno, CA'
),
now_ AS (
    SELECT metro, AVG(postings_index) AS idx_now
    FROM postings_metro JOIN big USING (metro), latest
    WHERE date > date(latest.d, '-28 days')
    GROUP BY metro
),
ago AS (
    SELECT metro, AVG(postings_index) AS idx_ago
    FROM postings_metro JOIN big USING (metro), latest
    WHERE date > date(latest.d, '-1 year', '-28 days') AND date <= date(latest.d, '-1 year')
    GROUP BY metro
)
SELECT n.metro,
       ROUND(n.idx_now, 1)                                   AS index_now_feb2020_100,
       ROUND(a.idx_ago, 1)                                   AS index_year_ago,
       ROUND(100.0 * (n.idx_now - a.idx_ago) / a.idx_ago, 1) AS change_12m_pct,
       RANK() OVER (ORDER BY n.idx_now / a.idx_ago DESC)     AS rank_12m
FROM now_ n JOIN ago a USING (metro)
ORDER BY rank_12m;

-- Q11: Which occupations are posting more or fewer jobs than a year ago? (U.S., 28-day averages)
WITH latest AS (SELECT MAX(date) AS d FROM postings_occ),
now_ AS (
    SELECT occupation, AVG(postings_index) AS idx_now
    FROM postings_occ, latest WHERE date > date(latest.d, '-28 days')
    GROUP BY occupation
),
ago AS (
    SELECT occupation, AVG(postings_index) AS idx_ago
    FROM postings_occ, latest
    WHERE date > date(latest.d, '-1 year', '-28 days') AND date <= date(latest.d, '-1 year')
    GROUP BY occupation
),
ranked AS (
    SELECT n.occupation,
           ROUND(n.idx_now, 1)                                    AS index_now,
           ROUND(100.0 * (n.idx_now - a.idx_ago) / a.idx_ago, 1)  AS change_12m_pct,
           ROW_NUMBER() OVER (ORDER BY n.idx_now / a.idx_ago DESC) AS rn_top,
           ROW_NUMBER() OVER (ORDER BY n.idx_now / a.idx_ago ASC)  AS rn_bottom
    FROM now_ n JOIN ago a USING (occupation)
)
SELECT occupation, index_now, change_12m_pct,
       CASE WHEN rn_top <= 8 THEN 'top 8'
            WHEN rn_bottom <= 8 THEN 'bottom 8'
            ELSE 'data roles' END AS grp
FROM ranked
WHERE rn_top <= 8 OR rn_bottom <= 8
   OR occupation IN ('Data & Analytics', 'Software Development', 'Medical Information')
ORDER BY change_12m_pct DESC;

-- Q12: Los Angeles County vs all of California - total jobs every September
WITH la AS (
    SELECT month, jobs_k AS la_k FROM employment WHERE series_id = 'SMU06310840000000001'
), ca AS (
    SELECT month, jobs_k AS ca_k FROM employment WHERE series_id = 'CANA'
)
SELECT substr(month, 1, 4) AS year,
       la_k                AS la_county_k,
       ROUND(la_k - LAG(la_k) OVER (ORDER BY month), 1) AS la_change_k,
       ROUND(100.0 * (la_k - LAG(la_k) OVER (ORDER BY month)) / LAG(la_k) OVER (ORDER BY month), 1) AS la_change_pct,
       ROUND(100.0 * (ca_k - LAG(ca_k) OVER (ORDER BY month)) / LAG(ca_k) OVER (ORDER BY month), 1) AS state_change_pct
FROM la JOIN ca USING (month)
WHERE substr(month, 6, 2) = '09'
ORDER BY year
LIMIT -1 OFFSET 1;

-- Q13: California vs U.S. - five-year job growth by sector (Sep 2021 -> Sep 2026)
WITH g AS (
    SELECT s.region, s.name,
           100.0 * (MAX(CASE WHEN e.month = '2026-09-01' THEN e.jobs_k END)
                  - MAX(CASE WHEN e.month = '2021-09-01' THEN e.jobs_k END))
                  / MAX(CASE WHEN e.month = '2021-09-01' THEN e.jobs_k END) AS pct
    FROM employment e
    JOIN series s USING (series_id)
    WHERE s.level IN ('supersector', 'total')
    GROUP BY s.region, s.name
)
SELECT ca.name,
       ROUND(ca.pct, 1)          AS california_pct,
       ROUND(us.pct, 1)          AS us_pct,
       ROUND(ca.pct - us.pct, 1) AS gap_pp,
       CASE WHEN ca.pct > us.pct THEN 'CA ahead' ELSE 'CA behind' END AS verdict
FROM g ca
JOIN g us ON us.name = ca.name AND us.region = 'US'
WHERE ca.region = 'CA'
ORDER BY (ca.name = 'Total nonfarm') DESC, gap_pp DESC;

-- Q14: California's share of U.S. jobs by sector, 2021 vs 2026
WITH j AS (
    SELECT s.region, s.name, e.month, e.jobs_k
    FROM employment e
    JOIN series s USING (series_id)
    WHERE s.level IN ('supersector', 'total') AND e.month IN ('2021-09-01', '2026-09-01')
)
SELECT ca.name,
       ROUND(100.0 * MAX(CASE WHEN ca.month = '2021-09-01' THEN ca.jobs_k / us.jobs_k END), 2) AS ca_share_2021_pct,
       ROUND(100.0 * MAX(CASE WHEN ca.month = '2026-09-01' THEN ca.jobs_k / us.jobs_k END), 2) AS ca_share_2026_pct,
       ROUND(100.0 * MAX(CASE WHEN ca.month = '2026-09-01' THEN ca.jobs_k / us.jobs_k END)
           - 100.0 * MAX(CASE WHEN ca.month = '2021-09-01' THEN ca.jobs_k / us.jobs_k END), 2) AS change_pp
FROM j ca
JOIN j us ON us.name = ca.name AND us.month = ca.month AND us.region = 'US'
WHERE ca.region = 'CA'
GROUP BY ca.name
ORDER BY ca_share_2026_pct DESC;

-- Q15: Job momentum - is each sector speeding up or slowing down? (last 12 months vs the 12 before)
WITH p AS (
    SELECT s.region, s.name, e.month, e.jobs_k,
           LAG(e.jobs_k, 12) OVER w AS year_ago,
           LAG(e.jobs_k, 24) OVER w AS two_years_ago
    FROM employment e
    JOIN series s USING (series_id)
    WHERE s.level IN ('supersector', 'total')
    WINDOW w AS (PARTITION BY e.series_id ORDER BY e.month)
)
SELECT region, name,
       ROUND(100.0 * (jobs_k - year_ago) / year_ago, 2)                AS last_12m_pct,
       ROUND(100.0 * (year_ago - two_years_ago) / two_years_ago, 2)    AS prior_12m_pct,
       ROUND(100.0 * (jobs_k - year_ago) / year_ago
           - 100.0 * (year_ago - two_years_ago) / two_years_ago, 2)    AS momentum_pp,
       CASE WHEN (jobs_k - year_ago) / year_ago > (year_ago - two_years_ago) / two_years_ago
            THEN 'speeding up' ELSE 'slowing down' END                 AS direction
FROM p
WHERE month = '2026-09-01'
ORDER BY region, momentum_pp DESC;

-- Q16: Stock market sectors - total return over 5 years, 1 year, 6 and 3 months (to Oct 2026)
WITH p AS (
    SELECT ticker, month, adj_close,
           LAG(adj_close, 3)  OVER w AS p3,
           LAG(adj_close, 6)  OVER w AS p6,
           LAG(adj_close, 12) OVER w AS p12,
           LAG(adj_close, 60) OVER w AS p60
    FROM stock_prices
    WINDOW w AS (PARTITION BY ticker ORDER BY month)
)
SELECT k.sector, p.ticker,
       ROUND(100.0 * (adj_close / p60 - 1), 1) AS return_5y_pct,
       ROUND(100.0 * (adj_close / p12 - 1), 1) AS return_1y_pct,
       ROUND(100.0 * (adj_close / p6 - 1), 1)  AS return_6m_pct,
       ROUND(100.0 * (adj_close / p3 - 1), 1)  AS return_3m_pct,
       RANK() OVER (ORDER BY adj_close / p60 DESC) AS rank_5y,
       RANK() OVER (ORDER BY adj_close / p12 DESC) AS rank_1y
FROM p
JOIN stock_sectors k USING (ticker)
WHERE p.month = '2026-10-01'
ORDER BY return_5y_pct DESC;

-- Q17: Stock momentum - last 12 months vs the 12 before, and vs the S&P 500
WITH p AS (
    SELECT ticker, month, adj_close,
           LAG(adj_close, 12) OVER w AS p12,
           LAG(adj_close, 24) OVER w AS p24
    FROM stock_prices
    WINDOW w AS (PARTITION BY ticker ORDER BY month)
), r AS (
    SELECT ticker,
           100.0 * (adj_close / p12 - 1) AS last_12m,
           100.0 * (p12 / p24 - 1)       AS prior_12m
    FROM p WHERE month = '2026-10-01'
)
SELECT k.sector,
       ROUND(r.last_12m, 1)                AS last_12m_pct,
       ROUND(r.prior_12m, 1)               AS prior_12m_pct,
       ROUND(r.last_12m - r.prior_12m, 1)  AS momentum_pp,
       ROUND(r.last_12m - (SELECT last_12m FROM r WHERE ticker = 'SPY'), 1) AS vs_sp500_pp,
       CASE WHEN r.last_12m > r.prior_12m THEN 'accelerating' ELSE 'decelerating' END AS direction
FROM r
JOIN stock_sectors k USING (ticker)
ORDER BY momentum_pp DESC;

-- Q18: Stock sectors year by year (October to October total return, %)
WITH y AS (
    SELECT ticker, month,
           100.0 * (adj_close / LAG(adj_close, 12) OVER (PARTITION BY ticker ORDER BY month) - 1) AS ret
    FROM stock_prices
)
SELECT k.sector,
       ROUND(MAX(CASE WHEN month = '2022-10-01' THEN ret END), 1) AS y2022,
       ROUND(MAX(CASE WHEN month = '2023-10-01' THEN ret END), 1) AS y2023,
       ROUND(MAX(CASE WHEN month = '2024-10-01' THEN ret END), 1) AS y2024,
       ROUND(MAX(CASE WHEN month = '2025-10-01' THEN ret END), 1) AS y2025,
       ROUND(MAX(CASE WHEN month = '2026-10-01' THEN ret END), 1) AS y2026,
       SUM(CASE WHEN month IN ('2022-10-01','2023-10-01','2024-10-01','2025-10-01','2026-10-01') AND ret > 0
                THEN 1 ELSE 0 END) AS years_up_of_5
FROM y
JOIN stock_sectors k USING (ticker)
GROUP BY k.sector
ORDER BY y2026 DESC;

-- Q19: Worst fall from a previous high in the five years (maximum drawdown, month-end prices)
WITH run AS (
    SELECT ticker, month, adj_close,
           MAX(adj_close) OVER (PARTITION BY ticker ORDER BY month
                                ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS peak_so_far
    FROM stock_prices
    WHERE month >= '2021-10-01'
), dd AS (
    SELECT ticker, month, 100.0 * (adj_close / peak_so_far - 1) AS drawdown,
           ROW_NUMBER() OVER (PARTITION BY ticker ORDER BY adj_close / peak_so_far) AS rn
    FROM run
)
SELECT k.sector,
       ROUND(dd.drawdown, 1)  AS max_drawdown_pct,
       substr(dd.month, 1, 7) AS lowest_month
FROM dd
JOIN stock_sectors k USING (ticker)
WHERE dd.rn = 1
ORDER BY max_drawdown_pct;

-- Q20: Do stock returns follow jobs? Sector fund return vs U.S. job growth in the closest jobs sector (Oct 2021 -> Oct 2026)
WITH stock AS (
    SELECT ticker,
           100.0 * (MAX(CASE WHEN month = '2026-10-01' THEN adj_close END)
                  / MAX(CASE WHEN month = '2021-10-01' THEN adj_close END) - 1) AS ret_5y,
           100.0 * (MAX(CASE WHEN month = '2026-10-01' THEN adj_close END)
                  / MAX(CASE WHEN month = '2025-10-01' THEN adj_close END) - 1) AS ret_1y
    FROM stock_prices GROUP BY ticker
), jobs AS (
    SELECT s.name,
           100.0 * (MAX(CASE WHEN e.month = '2026-10-01' THEN e.jobs_k END)
                  / MAX(CASE WHEN e.month = '2021-10-01' THEN e.jobs_k END) - 1) AS jobs_5y,
           100.0 * (MAX(CASE WHEN e.month = '2026-10-01' THEN e.jobs_k END)
                  / MAX(CASE WHEN e.month = '2025-10-01' THEN e.jobs_k END) - 1) AS jobs_1y
    FROM employment e JOIN series s USING (series_id)
    WHERE s.region = 'US' AND s.level IN ('supersector', 'total')
    GROUP BY s.name
)
SELECT k.sector              AS stock_sector,
       k.jobs_sector         AS closest_jobs_sector,
       ROUND(stock.ret_5y, 1) AS stock_return_5y_pct,
       ROUND(jobs.jobs_5y, 1) AS us_jobs_5y_pct,
       ROUND(stock.ret_1y, 1) AS stock_return_1y_pct,
       ROUND(jobs.jobs_1y, 1) AS us_jobs_1y_pct,
       CASE WHEN stock.ret_5y > 0 AND jobs.jobs_5y < 0 THEN 'stocks up, jobs down'
            WHEN stock.ret_5y > 0 AND jobs.jobs_5y > 0 THEN 'both up'
            ELSE 'other' END  AS pattern
FROM stock_sectors k
JOIN stock USING (ticker)
JOIN jobs ON jobs.name = k.jobs_sector
ORDER BY stock_return_5y_pct DESC;

-- Q21: Last three months - U.S. payroll change by sector (Jul -> Oct 2026) vs the pace of the year before
WITH p AS (
    SELECT s.name, e.month, e.jobs_k,
           LAG(e.jobs_k, 1)  OVER w AS m1,
           LAG(e.jobs_k, 2)  OVER w AS m2,
           LAG(e.jobs_k, 3)  OVER w AS m3,
           LAG(e.jobs_k, 15) OVER w AS m15
    FROM employment e
    JOIN series s USING (series_id)
    WHERE s.region = 'US' AND s.level IN ('supersector', 'total')
    WINDOW w AS (PARTITION BY e.series_id ORDER BY e.month)
)
SELECT name,
       ROUND(m2 - m3)        AS aug_k,
       ROUND(m1 - m2)        AS sep_k,
       ROUND(jobs_k - m1)    AS oct_k,
       ROUND(jobs_k - m3)    AS last_3m_k,
       ROUND((m3 - m15) / 4.0) AS typical_3m_k,
       CASE WHEN jobs_k - m3 > (m3 - m15) / 4.0 THEN 'faster than before' ELSE 'slower than before' END AS pace
FROM p
WHERE month = '2026-10-01'
ORDER BY (name = 'Total nonfarm') DESC, last_3m_k DESC;

-- Q22: Last three months - announced layoffs by jobs sector (hand-collected from the Challenger reports)
WITH m AS (
    SELECT jobs_sector,
           SUM(CASE WHEN month = '2026-08-01' THEN cuts END) AS aug,
           SUM(CASE WHEN month = '2026-09-01' THEN cuts END) AS sep,
           SUM(CASE WHEN month = '2026-10-01' THEN cuts END) AS oct,
           SUM(cuts) AS last_3m
    FROM layoffs_monthly WHERE industry <> 'TOTAL' GROUP BY jobs_sector
), y AS (
    SELECT jobs_sector, SUM(ytd_2026) AS ytd_2026, SUM(ytd_2025) AS ytd_2025
    FROM layoffs_ytd WHERE industry <> 'TOTAL' GROUP BY jobs_sector
)
SELECT m.jobs_sector, m.aug, m.sep, m.oct, m.last_3m,
       ROUND(100.0 * m.last_3m / SUM(m.last_3m) OVER (), 1)        AS share_of_3m_pct,
       y.ytd_2026, y.ytd_2025,
       ROUND(100.0 * (y.ytd_2026 - y.ytd_2025) / y.ytd_2025, 0)    AS ytd_change_pct
FROM m JOIN y USING (jobs_sector)
ORDER BY m.last_3m DESC;

-- Q23: Job openings and hiring by sector (BLS JOLTS, Sep 2026 vs Sep 2025; hand-collected, thousands)
WITH a AS (SELECT * FROM jolts WHERE month = '2026-09-01' AND level IN ('supersector', 'total')),
     b AS (SELECT * FROM jolts WHERE month = '2025-09-01')
SELECT a.jobs_sector,
       a.openings_k                                                     AS openings_sep_2026,
       ROUND(100.0 * (a.openings_k - b.openings_k) / b.openings_k, 1)   AS openings_change_12m_pct,
       a.hires_k                                                        AS hires_sep_2026,
       a.hires_k - a.separations_k                                      AS hires_minus_separations,
       ROUND(1.0 * a.openings_k / a.hires_k, 2)                         AS openings_per_hire,
       RANK() OVER (ORDER BY 1.0 * a.openings_k / a.hires_k DESC)       AS hardest_to_fill_rank
FROM a JOIN b USING (industry)
ORDER BY (a.level = 'total') DESC, openings_change_12m_pct DESC;

-- Q24: Sector scorecard - jobs, openings, layoffs and stocks side by side (U.S.)
WITH jobs AS (
    SELECT s.name,
           100.0 * (MAX(CASE WHEN e.month = '2026-10-01' THEN e.jobs_k END)
                  / MAX(CASE WHEN e.month = '2025-10-01' THEN e.jobs_k END) - 1) AS jobs_12m_pct,
           MAX(CASE WHEN e.month = '2026-10-01' THEN e.jobs_k END)
         - MAX(CASE WHEN e.month = '2026-07-01' THEN e.jobs_k END)               AS jobs_3m_k
    FROM employment e JOIN series s USING (series_id)
    WHERE s.region = 'US' AND s.level = 'supersector'
    GROUP BY s.name
), openings AS (
    SELECT a.jobs_sector AS name,
           100.0 * (a.openings_k - b.openings_k) / b.openings_k AS openings_12m_pct
    FROM jolts a JOIN jolts b USING (industry)
    WHERE a.month = '2026-09-01' AND b.month = '2025-09-01' AND a.level = 'supersector'
), layoffs AS (
    SELECT jobs_sector AS name, SUM(cuts) AS layoffs_3m
    FROM layoffs_monthly WHERE industry <> 'TOTAL' GROUP BY jobs_sector
), stocks AS (
    SELECT k.jobs_sector AS name,
           AVG(100.0 * (n.adj_close / o.adj_close - 1)) AS stock_1y_pct,
           GROUP_CONCAT(k.sector, ' + ')                 AS stock_sectors
    FROM stock_sectors k
    JOIN stock_prices n ON n.ticker = k.ticker AND n.month = '2026-10-01'
    JOIN stock_prices o ON o.ticker = k.ticker AND o.month = '2025-10-01'
    WHERE k.ticker <> 'SPY'
    GROUP BY k.jobs_sector
)
SELECT j.name                              AS sector,
       ROUND(j.jobs_12m_pct, 1)            AS jobs_12m_pct,
       ROUND(j.jobs_3m_k)                  AS jobs_last_3m_k,
       ROUND(o.openings_12m_pct, 1)        AS openings_12m_pct,
       l.layoffs_3m                        AS announced_layoffs_3m,
       ROUND(st.stock_1y_pct, 1)           AS stock_1y_pct,
       st.stock_sectors,
       (j.jobs_12m_pct > 0) + (j.jobs_3m_k > 0) + (o.openings_12m_pct > 0) AS hiring_signals_of_3
FROM jobs j
LEFT JOIN openings o USING (name)
LEFT JOIN layoffs l USING (name)
LEFT JOIN stocks st USING (name)
ORDER BY hiring_signals_of_3 DESC, j.jobs_12m_pct DESC;

-- Q25: Top five occupations by yearly job openings in each field (BLS projections 2025-35)
WITH ranked AS (
    SELECT field, title, openings_k, change_pct, median_wage, education,
           ROW_NUMBER() OVER (PARTITION BY field ORDER BY openings_k DESC) AS rank_in_field
    FROM occupation_outlook
    WHERE field IS NOT NULL
)
SELECT field, rank_in_field, title,
       openings_k   AS openings_per_year_k,
       change_pct   AS growth_2025_35_pct,
       median_wage,
       education    AS typical_education
FROM ranked
WHERE rank_in_field <= 5
ORDER BY field, rank_in_field;

-- Q26: Bachelor's-level occupations growing fastest and shrinking most (2025-35, at least 50,000 jobs)
WITH b AS (
    SELECT title, emp_2025_k, change_pct, openings_k, median_wage,
           ROW_NUMBER() OVER (ORDER BY change_pct DESC) AS from_top,
           ROW_NUMBER() OVER (ORDER BY change_pct ASC)  AS from_bottom
    FROM occupation_outlook
    WHERE bachelors = 1 AND emp_2025_k >= 50
)
SELECT CASE WHEN from_top <= 10 THEN 'fastest growing' ELSE 'shrinking' END AS grp,
       title, change_pct AS growth_2025_35_pct, openings_k AS openings_per_year_k, median_wage
FROM b
WHERE from_top <= 10 OR from_bottom <= 8
ORDER BY change_pct DESC;

-- Q27: College majors with the lowest and highest underemployment (recent graduates, 2024)
WITH r AS (
    SELECT major, major_group, underemployment_pct, unemployment_pct, wage_early,
           ROW_NUMBER() OVER (ORDER BY underemployment_pct ASC)  AS best,
           ROW_NUMBER() OVER (ORDER BY underemployment_pct DESC) AS worst
    FROM majors WHERE major <> 'Overall'
)
SELECT CASE WHEN best <= 10 THEN 'lowest underemployment' ELSE 'highest underemployment' END AS grp,
       major, major_group, underemployment_pct, unemployment_pct, wage_early
FROM r
WHERE best <= 10 OR worst <= 10
ORDER BY underemployment_pct;

-- Q28: Major families compared (simple averages across the majors in each family)
SELECT major_group,
       COUNT(*)                               AS majors,
       ROUND(AVG(unemployment_pct), 1)        AS avg_unemployment_pct,
       ROUND(AVG(underemployment_pct), 1)     AS avg_underemployment_pct,
       ROUND(AVG(wage_early))                 AS avg_wage_early,
       ROUND(AVG(wage_mid))                   AS avg_wage_mid,
       ROUND(100.0 * (AVG(wage_mid) / AVG(wage_early) - 1)) AS wage_growth_pct,
       ROUND(AVG(grad_share_pct), 1)          AS avg_grad_degree_share_pct
FROM majors
WHERE major <> 'Overall'
GROUP BY major_group
ORDER BY avg_underemployment_pct;

-- Q29: Major scorecard - how many of three tests does each major pass against the average graduate?
WITH o AS (SELECT * FROM majors WHERE major = 'Overall'),
s AS (
    SELECT m.major, m.major_group, m.unemployment_pct, m.underemployment_pct, m.wage_early,
           (m.unemployment_pct < o.unemployment_pct)
         + (m.underemployment_pct < o.underemployment_pct)
         + (m.wage_early > o.wage_early) AS tests_passed
    FROM majors m, o
    WHERE m.major <> 'Overall'
)
SELECT tests_passed,
       COUNT(*) AS majors,
       GROUP_CONCAT(major, ', ') AS which
FROM s
GROUP BY tests_passed
ORDER BY tests_passed DESC;

-- Q30: Well paid but harder to land - majors with above-average pay and above-average unemployment
SELECT m.major, m.major_group, m.unemployment_pct, m.underemployment_pct, m.wage_early, m.wage_mid
FROM majors m
JOIN majors o ON o.major = 'Overall'
WHERE m.major <> 'Overall'
  AND m.wage_early > o.wage_early
  AND m.unemployment_pct > o.unemployment_pct
ORDER BY m.unemployment_pct DESC;
