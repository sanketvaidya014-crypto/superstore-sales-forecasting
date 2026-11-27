-- Region x year: sales, margin, YoY growth and share of company sales
WITH r AS (
    SELECT region, CAST(strftime('%Y', order_date) AS INT) AS yr,
           SUM(sales) AS sales, SUM(profit) AS profit, AVG(discount) AS avg_discount
    FROM sales GROUP BY 1, 2
)
SELECT region, yr,
       ROUND(sales, 2)                  AS sales,
       ROUND(profit, 2)                 AS profit,
       ROUND(100.0 * profit / sales, 2) AS margin_pct,
       ROUND(100.0 * avg_discount, 1)   AS avg_discount_pct,
       ROUND(100.0 * (sales / LAG(sales) OVER (PARTITION BY region ORDER BY yr) - 1), 1) AS sales_yoy_pct,
       ROUND(100.0 * sales / SUM(sales) OVER (PARTITION BY yr), 1)                       AS share_of_sales_pct
FROM r ORDER BY region, yr;
