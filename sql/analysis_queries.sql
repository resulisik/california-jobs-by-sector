-- California jobs by sector, Sept 2021 - Sept 2026
-- Database: data/ca_jobs.db (built by src/build_database.py)
-- jobs_k = thousands of jobs. postings_index = Indeed postings, Feb 1 2020 = 100.
-- Each query starts with a "-- Qn: title" line so src/run_queries.py can split the file.

-- Q1: Five-year job change by sector (Sep 2021 -> Sep 2026)
WITH ends AS (
    SELECT s.name,
           MAX(CASE WHEN e.month = '2021-09-01' THEN e.jobs_k END) AS jobs_2021,
           MAX(CASE WHEN e.month = '2026-09-01' THEN e.jobs_k END) AS jobs_2026
    FROM employment e
    JOIN series s USING (series_id)
    WHERE s.level IN ('supersector', 'total')
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
    WHERE s.level IN ('supersector', 'total')
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
WHERE e.month = '2026-09-01' AND s.level IN ('supersector', 'total') AND s.seasonally_adjusted = 1
ORDER BY index_feb2020_100 DESC;

-- Q4: Each sector's share of all California jobs, 2021 vs 2026
WITH totals AS (
    SELECT month, jobs_k AS total_k FROM employment WHERE series_id = 'CANA'
), shares AS (
    SELECT s.name, e.month, 100.0 * e.jobs_k / t.total_k AS share_pct
    FROM employment e
    JOIN totals t USING (month)
    JOIN series s USING (series_id)
    WHERE s.level = 'supersector' AND e.month IN ('2021-09-01', '2026-09-01')
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
WHERE s.level IN ('subsector', 'area')
ORDER BY change_5y_pct DESC;

-- Q7: Year-by-year change, September to September (thousands of jobs)
WITH yoy AS (
    SELECT s.name, e.month,
           e.jobs_k - LAG(e.jobs_k, 12) OVER (PARTITION BY e.series_id ORDER BY e.month) AS chg
    FROM employment e JOIN series s USING (series_id)
    WHERE s.level IN ('supersector', 'total')
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
)
SELECT name,
       SUM(CASE WHEN chg < 0 THEN 1 ELSE 0 END) AS months_down_of_24,
       SUM(CASE WHEN chg > 0 THEN 1 ELSE 0 END) AS months_up_of_24
FROM yoy
WHERE month > '2024-09-01'
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
