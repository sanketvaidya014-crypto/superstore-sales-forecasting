-- Quarterly sales, profit, margin, QoQ and YoY growth
WITH q AS (
    SELECT CAST(strftime('%Y', order_date) AS INT)           AS yr,
           (CAST(strftime('%m', order_date) AS INT) + 2) / 3 AS qtr,
           SUM(sales) AS sales, SUM(profit) AS profit
    FROM sales GROUP BY 1, 2
)
SELECT yr, qtr, yr || '-Q' || qtr AS quarter,
       ROUND(sales, 2)                  AS sales,
       ROUND(profit, 2)                 AS profit,
       ROUND(100.0 * profit / sales, 2) AS margin_pct,
       ROUND(100.0 * (sales / LAG(sales)    OVER (ORDER BY yr, qtr) - 1), 1) AS qoq_pct,
       ROUND(100.0 * (sales / LAG(sales, 4) OVER (ORDER BY yr, qtr) - 1), 1) AS yoy_pct
FROM q ORDER BY yr, qtr;
