-- Underperformance screen for the latest year.
-- Underperforming = margin below company margin AND growth below company growth. Watch = only one of the two.
WITH ly AS (SELECT MAX(CAST(strftime('%Y', order_date) AS INT)) AS yr FROM sales),
agg AS (
    SELECT region, category, CAST(strftime('%Y', order_date) AS INT) AS yr,
           SUM(sales) AS sales, SUM(profit) AS profit
    FROM sales GROUP BY 1, 2, 3
),
cur  AS (SELECT a.* FROM agg a JOIN ly ON a.yr = ly.yr),
prev AS (SELECT a.* FROM agg a JOIN ly ON a.yr = ly.yr - 1),
bench AS (
    SELECT (SELECT SUM(profit) FROM cur) / (SELECT SUM(sales) FROM cur)   AS margin,
           (SELECT SUM(sales)  FROM cur) / (SELECT SUM(sales) FROM prev)  AS growth
)
SELECT c.region, c.category,
       ROUND(c.sales, 2)                                          AS sales,
       ROUND(100.0 * (c.sales / NULLIF(p.sales, 0) - 1), 1)       AS yoy_pct,
       ROUND(100.0 * c.profit / c.sales, 2)                       AS margin_pct,
       ROUND(100.0 * (b.growth - 1), 1)                           AS company_yoy_pct,
       ROUND(100.0 * b.margin, 2)                                 AS company_margin_pct,
       CASE WHEN c.profit / c.sales < b.margin AND c.sales / NULLIF(p.sales, 0) < b.growth THEN 'Underperforming'
            WHEN c.profit / c.sales < b.margin OR  c.sales / NULLIF(p.sales, 0) < b.growth THEN 'Watch'
            ELSE 'On track' END                                   AS status
FROM cur c
LEFT JOIN prev p ON p.region = c.region AND p.category = c.category
CROSS JOIN bench b
ORDER BY margin_pct;
