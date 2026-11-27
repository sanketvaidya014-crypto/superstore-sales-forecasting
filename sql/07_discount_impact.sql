-- How discount depth changes margin (order lines bucketed by discount)
SELECT CASE WHEN discount = 0    THEN '1) No discount'
            WHEN discount <= 0.2 THEN '2) Up to 20%'
            WHEN discount <= 0.4 THEN '3) 21-40%'
            ELSE                      '4) Above 40%' END      AS discount_band,
       COUNT(*)                                               AS order_lines,
       ROUND(SUM(sales), 2)                                   AS sales,
       ROUND(SUM(profit), 2)                                  AS profit,
       ROUND(100.0 * SUM(profit) / SUM(sales), 2)             AS margin_pct,
       ROUND(100.0 * AVG(CASE WHEN profit < 0 THEN 1.0 ELSE 0 END), 1) AS loss_making_lines_pct
FROM sales
GROUP BY 1 ORDER BY 1;
