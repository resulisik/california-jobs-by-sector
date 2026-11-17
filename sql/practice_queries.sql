-- Practice queries for data/sectors.db
-- Open the database in DB Browser for SQLite (or any SQLite tool), go to "Execute SQL",
-- paste one query at a time and press Ctrl+Enter. Start at the top: each level adds one idea.
--
-- Tables
--   series(series_id, name, level, seasonally_adjusted, region)      region = 'CA' or 'US'
--   employment(series_id, month, jobs_k)                             thousands of jobs, monthly
--   stock_prices(ticker, month, adj_close)                           month-end price, dividends reinvested
--   stock_sectors(ticker, sector, jobs_sector)
--   layoffs_monthly(industry, jobs_sector, month, cuts)              Aug-Oct 2026, hand-collected
--   layoffs_ytd(industry, jobs_sector, ytd_2026, ytd_2025)
--   jolts(industry, jobs_sector, level, month, openings_k, hires_k, separations_k)
--   postings_state(date, state, postings_index)                      Indeed, Feb 1 2020 = 100
--   postings_metro(date, metro, cbsa_code, postings_index)
--   postings_occ(date, occupation, postings_index)
--   research_sources(dataset, report, published, url, collected_on, notes)
--   postings(posting_id, source, company, sector_name, title, family, eng_type, seniority, loc_bucket,
--            is_la, is_ca, is_us, is_remote, posted_date, days_old, pay_min, pay_max, pay_period, url, ...)
--                                                                    one row per open job, snapshot of 17 Nov 2026
--   posting_skills(posting_id, skill)                                skills named in data-related descriptions
--   posting_companies(platform, slug, company, sector, postings)     the employers in the snapshot

-- ---------- Level 1: SELECT, WHERE, ORDER BY ----------

-- 1.1 What series are in the database?
SELECT series_id, name, level, region FROM series ORDER BY region, level, name;

-- 1.2 California jobs in health care, month by month
SELECT month, jobs_k
FROM employment
WHERE series_id = 'SMS06000006562000001'
ORDER BY month;

-- 1.3 The ten best months for the technology fund
SELECT month, adj_close FROM stock_prices WHERE ticker = 'XLK' ORDER BY adj_close DESC LIMIT 10;

-- ---------- Level 2: JOIN and GROUP BY ----------

-- 2.1 Jobs by sector in the latest month, California and the U.S.
SELECT s.region, s.name, e.jobs_k
FROM employment e
JOIN series s USING (series_id)
WHERE e.month = '2026-09-01' AND s.level = 'supersector'
ORDER BY s.region, e.jobs_k DESC;

-- 2.2 Average jobs per year in California's information sector
SELECT substr(e.month, 1, 4) AS year, ROUND(AVG(e.jobs_k), 1) AS avg_jobs_k
FROM employment e
JOIN series s USING (series_id)
WHERE s.region = 'CA' AND s.name = 'Information'
GROUP BY year
ORDER BY year;

-- 2.3 Announced layoffs by industry, last three months, largest first
SELECT industry, SUM(cuts) AS cuts_3m
FROM layoffs_monthly
WHERE industry <> 'TOTAL'
GROUP BY industry
HAVING SUM(cuts) > 5000
ORDER BY cuts_3m DESC;

-- ---------- Level 3: CASE and conditional aggregation ----------

-- 3.1 Turn rows into columns: jobs in Sep 2021 and Sep 2026 side by side
SELECT s.name,
       MAX(CASE WHEN e.month = '2021-09-01' THEN e.jobs_k END) AS sep_2021,
       MAX(CASE WHEN e.month = '2026-09-01' THEN e.jobs_k END) AS sep_2026
FROM employment e
JOIN series s USING (series_id)
WHERE s.region = 'US' AND s.level = 'supersector'
GROUP BY s.name;

-- 3.2 Label each stock sector by its last-12-month return
SELECT k.sector,
       ROUND(100.0 * (n.adj_close / o.adj_close - 1), 1) AS return_1y_pct,
       CASE WHEN n.adj_close / o.adj_close - 1 > 0.20 THEN 'strong'
            WHEN n.adj_close / o.adj_close - 1 > 0    THEN 'positive'
            ELSE 'negative' END AS label
FROM stock_sectors k
JOIN stock_prices n ON n.ticker = k.ticker AND n.month = '2026-10-01'
JOIN stock_prices o ON o.ticker = k.ticker AND o.month = '2025-10-01'
ORDER BY return_1y_pct DESC;

-- ---------- Level 4: CTEs (WITH) ----------

-- 4.1 Which U.S. sectors grew faster than the country as a whole in five years?
WITH growth AS (
    SELECT s.name, s.level,
           100.0 * (MAX(CASE WHEN e.month = '2026-10-01' THEN e.jobs_k END)
                  / MAX(CASE WHEN e.month = '2021-10-01' THEN e.jobs_k END) - 1) AS pct
    FROM employment e
    JOIN series s USING (series_id)
    WHERE s.region = 'US' AND s.level IN ('supersector', 'total')
    GROUP BY s.name, s.level
)
SELECT name, ROUND(pct, 1) AS growth_pct
FROM growth
WHERE level = 'supersector'
  AND pct > (SELECT pct FROM growth WHERE level = 'total')
ORDER BY pct DESC;

-- ---------- Level 5: window functions ----------

-- 5.1 Month-over-month change with LAG
SELECT month, jobs_k,
       ROUND(jobs_k - LAG(jobs_k) OVER (ORDER BY month), 1) AS change_k
FROM employment
WHERE series_id = 'PAYEMS'
ORDER BY month DESC
LIMIT 12;

-- 5.2 Three-month moving average of U.S. monthly job gains
WITH chg AS (
    SELECT month, jobs_k - LAG(jobs_k) OVER (ORDER BY month) AS change_k
    FROM employment WHERE series_id = 'PAYEMS'
)
SELECT month, change_k,
       ROUND(AVG(change_k) OVER (ORDER BY month ROWS BETWEEN 2 PRECEDING AND CURRENT ROW), 1) AS avg_3m
FROM chg
WHERE month >= '2025-10-01';

-- 5.3 Rank stock sectors inside each year (October to October)
WITH yearly AS (
    SELECT k.sector, p.month,
           100.0 * (p.adj_close / LAG(p.adj_close, 12) OVER (PARTITION BY p.ticker ORDER BY p.month) - 1) AS ret
    FROM stock_prices p
    JOIN stock_sectors k USING (ticker)
)
SELECT substr(month, 1, 4) AS year, sector, ROUND(ret, 1) AS return_pct,
       RANK() OVER (PARTITION BY month ORDER BY ret DESC) AS rank_in_year
FROM yearly
WHERE substr(month, 6, 2) = '10' AND ret IS NOT NULL
ORDER BY year, rank_in_year;

-- ---------- Level 6: job postings ----------

-- 6.1 How many open jobs does each employer have in the Los Angeles area?
SELECT company, COUNT(*) AS postings
FROM postings
WHERE loc_bucket = 'Los Angeles area'
GROUP BY company
ORDER BY postings DESC
LIMIT 10;

-- 6.2 Entry-level share by job family, U.S. postings (CASE inside SUM counts the rows that match)
SELECT family,
       COUNT(*) AS postings,
       SUM(CASE WHEN seniority IN ('Entry level', 'Internship') THEN 1 ELSE 0 END) AS junior,
       ROUND(100.0 * SUM(CASE WHEN seniority IN ('Entry level', 'Internship') THEN 1 ELSE 0 END) / COUNT(*), 1) AS junior_pct
FROM postings
WHERE is_us = 1
GROUP BY family
ORDER BY junior_pct DESC;

-- 6.3 Data postings that ask for both SQL and Tableau (a JOIN to the same table twice)
SELECT p.company, p.title, p.loc_bucket, p.url
FROM postings p
JOIN posting_skills s1 ON s1.posting_id = p.posting_id AND s1.skill = 'sql'
JOIN posting_skills s2 ON s2.posting_id = p.posting_id AND s2.skill = 'tableau'
WHERE p.family = 'Data & analytics' AND p.is_us = 1
ORDER BY p.posted_date DESC;

-- ---------- Your turn (answers are in sql/analysis_queries.sql) ----------
-- A. Which California sector lost the most jobs between Sep 2021 and Sep 2026?            (see Q1)
-- B. In which sectors is California ahead of the U.S. over five years?                    (see Q13)
-- C. Which stock sector had the largest fall from its previous high?                      (see Q19)
-- D. Which jobs sector has the most job openings per hire?                                (see Q23)
-- E. Build one table with jobs, openings, layoffs and stock returns per sector.           (see Q24)
-- F. Which five job titles are most common in each sector's postings?                     (see Q34)
-- G. Which skills appear most often in data & analytics postings?                         (see Q39)
