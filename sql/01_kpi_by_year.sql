-- Headline KPIs per year with year-over-year change (LAG)
WITH y AS (
    SELECT CAST(strftime('%Y', order_date) AS INT) AS yr,
           SUM(sales) AS sales, SUM(profit) AS profit,
           COUNT(DISTINCT order_id) AS orders, COUNT(DISTINCT customer_id) AS customers,
           AVG(discount) AS avg_discount
    FROM sales GROUP BY 1
)
SELECT yr,
       ROUND(sales, 2)                                   AS sales,
       ROUND(profit, 2)                                  AS profit,
       ROUND(100.0 * profit / sales, 2)                  AS margin_pct,
       orders, customers,
       ROUND(sales * 1.0 / orders, 2)                    AS aov,
       ROUND(100.0 * avg_discount, 1)                    AS avg_discount_pct,
       ROUND(100.0 * (sales / LAG(sales) OVER (ORDER BY yr) - 1), 1)           AS sales_yoy_pct,
       ROUND(100.0 * (profit / LAG(profit) OVER (ORDER BY yr) - 1), 1)         AS profit_yoy_pct,
       ROUND(100.0 * (orders * 1.0 / LAG(orders) OVER (ORDER BY yr) - 1), 1)   AS orders_yoy_pct
FROM y ORDER BY yr;
