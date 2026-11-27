-- Sub-category scorecard for the latest year: sales, YoY, margin and profit rank
WITH ly AS (SELECT MAX(CAST(strftime('%Y', order_date) AS INT)) AS yr FROM sales),
s AS (
    SELECT category, sub_category, CAST(strftime('%Y', order_date) AS INT) AS yr,
           SUM(sales) AS sales, SUM(profit) AS profit
    FROM sales GROUP BY 1, 2, 3
)
SELECT c.category, c.sub_category,
       ROUND(c.sales, 2)                                      AS sales,
       ROUND(100.0 * (c.sales / NULLIF(p.sales, 0) - 1), 1)   AS yoy_pct,
       ROUND(c.profit, 2)                                     AS profit,
       ROUND(100.0 * c.profit / c.sales, 2)                   AS margin_pct,
       RANK() OVER (ORDER BY c.profit DESC)                   AS profit_rank
FROM s c
JOIN ly ON c.yr = ly.yr
LEFT JOIN s p ON p.sub_category = c.sub_category AND p.category = c.category AND p.yr = ly.yr - 1
ORDER BY profit_rank;
