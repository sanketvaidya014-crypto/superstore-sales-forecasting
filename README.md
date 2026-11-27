# Retail Sales Forecasting & KPI Dashboard (Superstore)

**Business question:** *How do we forecast next quarter's sales, and which regions and products are underperforming?*

An end-to-end project: **SQL** reporting (KPIs, YoY growth, region and product performance) feeds a **Python** time-series layer (trend/seasonality, model comparison by backtesting, next-quarter forecast), ending in a **KPI dashboard** and **business recommendations**.

## Dataset
Superstore Sales (Kaggle, "Sample - Superstore"): ~10k order lines, 2014-2017, with sales, profit, discount, region, category and product.
Save the CSV as `data/raw/Sample - Superstore.csv` (the loader accepts several common file names, encodings and date formats).

## Project structure
```
data/raw/            source CSV (git-ignored)
sql/                 8 reporting queries (SQLite)
src/common.py        paths + helpers
src/load_db.py       clean + load into SQLite, prints data-quality checks
src/reporting.py     runs the SQL, builds the KPI dashboard
src/forecast.py      decomposition, backtesting, forecast, recommendations
src/make_sample_data.py   synthetic data for testing ONLY
outputs/             figures/, tables/, recommendations.md
```

## How to run
```bash
pip install -r requirements.txt
python src/load_db.py
python src/reporting.py     # SQL tables + kpi_dashboard.png
python src/forecast.py      # forecast, charts, recommendations.md
```
No dataset yet? `python src/make_sample_data.py` creates a synthetic file to test the pipeline. **Never report numbers from it as findings.**

## SQL layer
| File | Output | Techniques |
|---|---|---|
| 01_kpi_by_year | Sales, profit, margin, orders, AOV with YoY | CTE, `LAG` |
| 02_monthly_sales | Monthly sales with MoM, YoY, 3-month average | `LAG(,12)`, window frame `ROWS BETWEEN` |
| 03_quarterly_sales | Quarterly sales with QoQ and YoY | date functions, `LAG(,4)` |
| 04_region_performance | Region x year: margin, growth, share of sales | `PARTITION BY`, share of total |
| 05_region_category_matrix | Underperforming / Watch / On track flags | multi-CTE benchmarks, `CASE` |
| 06_top_bottom_products | Top 10 and bottom 10 products by profit | `RANK` both directions, `UNION ALL` |
| 07_discount_impact | Margin by discount depth | bucketing, conditional aggregation |
| 08_subcategory_performance | Sub-category scorecard | joins on prior year, `RANK` |

## Forecasting method
1. **Series:** monthly sales (48 points), completeness check, trend/seasonality decomposition (STL when statsmodels is installed).
2. **Models:** seasonal naive (benchmark), Holt-Winters with and without damped trend; with statsmodels installed, **ETS and SARIMA(1,1,1)(0,1,1,12)** are added automatically.
3. **Selection:** **rolling-origin backtest** (refit at several origins, forecast 3 months each time), compared by WAPE, bias and 95%-interval coverage, and by skill versus the seasonal-naive benchmark. The model is chosen on backtest error, not in-sample fit.
4. **Forecast:** next 3 months with an approximate 95% interval, compared with the same period last year; regional forecasts are scaled to add up to the total.

## Outputs
| Deliverable | File |
|---|---|
| Forecast chart | `outputs/figures/sales_forecast.png` |
| KPI dashboard | `outputs/figures/kpi_dashboard.png` |
| Trend/seasonality, model comparison, regional forecast | `decomposition.png`, `model_comparison.png`, `regional_forecast.png` |
| Business recommendations (numbers auto-generated) | `outputs/recommendations.md` |
| Forecast and backtest tables | `outputs/tables/` |

## Results
Run the pipeline, then paste the key numbers from `outputs/recommendations.md` here and add:
```markdown
![KPI dashboard](outputs/figures/kpi_dashboard.png)
![Forecast](outputs/figures/sales_forecast.png)
```

## Limitations
- Only 48 monthly points: intervals are wide, and complex models are not justified. Treat the forecast as a planning range.
- Assumes past patterns continue; promotions, price changes and shocks are not modelled.
- Superstore is a sample dataset, so findings illustrate the method rather than a real business.
- Prophet or gradient-boosting with calendar features are natural extensions once more history is available.

## Interview talking points
- "I picked the forecasting model by rolling-origin backtesting against a seasonal-naive benchmark, not by in-sample fit."
- "I used SQL window functions for YoY/QoQ and a CTE-based benchmark to flag underperforming region and category cells."
- "I quantified how deep discounts destroy margin and turned it into a concrete policy recommendation."
- "I reported forecast uncertainty and checked interval coverage instead of giving a single number."
