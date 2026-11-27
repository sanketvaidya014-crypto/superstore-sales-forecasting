-- Top 10 and bottom 10 products by total profit (RANK in both directions)
WITH p AS (
    SELECT product_id, product_name, sub_category,
           SUM(sales) AS sales, SUM(profit) AS profit, SUM(quantity) AS units, AVG(discount) AS avg_disc
    FROM sales GROUP BY product_id, product_name, sub_category
),
r AS (
    SELECT *, RANK() OVER (ORDER BY profit DESC) AS rk_top,
              RANK() OVER (ORDER BY profit ASC)  AS rk_bottom
    FROM p
)
SELECT * FROM (
    SELECT 'Top' AS bucket, rk_top AS rnk, product_name, sub_category,
           ROUND(sales, 2) AS sales, ROUND(profit, 2) AS profit,
           ROUND(100.0 * profit / sales, 1) AS margin_pct, units, ROUND(100.0 * avg_disc, 1) AS avg_discount_pct
    FROM r WHERE rk_top <= 10
    UNION ALL
    SELECT 'Bottom', rk_bottom, product_name, sub_category,
           ROUND(sales, 2), ROUND(profit, 2), ROUND(100.0 * profit / sales, 1), units, ROUND(100.0 * avg_disc, 1)
    FROM r WHERE rk_bottom <= 10
)
ORDER BY CASE bucket WHEN 'Top' THEN 0 ELSE 1 END, rnk;
