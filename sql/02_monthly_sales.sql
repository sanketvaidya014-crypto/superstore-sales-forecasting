-- Monthly sales with MoM, YoY and a 3-month moving average (window frames).
-- LAG(...,12) assumes no missing months; the Python layer checks this.
WITH m AS (
    SELECT strftime('%Y-%m', order_date) AS month,
           SUM(sales) AS sales, SUM(profit) AS profit, COUNT(DISTINCT order_id) AS orders
    FROM sales GROUP BY 1
)
SELECT month,
       ROUND(sales, 2)                          AS sales,
       ROUND(profit, 2)                         AS profit,
       ROUND(100.0 * profit / sales, 2)         AS margin_pct,
       orders,
       ROUND(100.0 * (sales / LAG(sales)     OVER (ORDER BY month) - 1), 1) AS mom_pct,
       ROUND(100.0 * (sales / LAG(sales, 12) OVER (ORDER BY month) - 1), 1) AS yoy_pct,
       ROUND(AVG(sales) OVER (ORDER BY month ROWS BETWEEN 2 PRECEDING AND CURRENT ROW), 2) AS sales_ma3
FROM m ORDER BY month;
