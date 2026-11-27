"""Time-series analysis and next-quarter forecast.  Usage: python src/forecast.py  (after load_db.py)

Models compared with rolling-origin backtesting:
  * Seasonal naive            (benchmark: same month last year)
  * Holt-Winters damped/none  (built-in, numpy/scipy, no extra dependency)
  * ETS + SARIMA              (statsmodels; used automatically when statsmodels is installed)
"""
import warnings

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy.optimize import minimize

from common import FIG, OUT, TAB, load_sales, run_all_sql

warnings.filterwarnings("ignore")
sns.set_theme(style="whitegrid", context="notebook")
BLUE, RED, GREEN, GREY = "#2F5D8A", "#C0504D", "#3E8E5A", "#8A8A8A"
H, M = 3, 12   # forecast horizon (months = one quarter), seasonal period

try:
    from statsmodels.tsa.exponential_smoothing.ets import ETSModel
    from statsmodels.tsa.seasonal import STL
    from statsmodels.tsa.statespace.sarimax import SARIMAX
    from statsmodels.tsa.stattools import adfuller
    HAVE_SM = True
except ImportError:
    HAVE_SM = False


# ------------------------------------------------------------------ models: f(train, h) -> (mean, lo95, hi95)
def f_snaive(train, h):
    y = train.values
    mean = np.array([y[len(y) - M + (i % M)] for i in range(h)])
    sig = np.nanstd(train.diff(M).dropna().values)
    w = 1.96 * sig * np.sqrt(np.ceil((np.arange(h) + 1) / M))
    return mean, mean - w, mean + w


def _hw_run(y, a, b, g, phi, trend):
    n = len(y)
    level = y[:M].mean()
    tr = (y[M:2 * M].mean() - y[:M].mean()) / M if (trend and n >= 2 * M) else 0.0
    seas = list(y[:M] - level)
    sse, errs = 0.0, []
    for t in range(n):
        s = seas[t % M] if t < M else seas[-M]
        pred = level + phi * tr + s
        e = y[t] - pred
        if t >= M:
            sse += e * e; errs.append(e)
        new_level = a * (y[t] - s) + (1 - a) * (level + phi * tr)
        tr = b * (new_level - level) + (1 - b) * phi * tr if trend else 0.0
        seas.append(g * (y[t] - new_level) + (1 - g) * s)
        level = new_level
    return sse, level, tr, seas, np.array(errs)


def f_hw(train, h, trend=True):
    y = train.values.astype(float); n = len(y)
    if trend:
        x0, bnd = [.3, .05, .2, .9], [(.01, .99), (.001, .5), (.01, .99), (.8, .98)]
    else:
        x0, bnd = [.3, .0, .2, 1.0], [(.01, .99), (0, 1e-9), (.01, .99), (1.0, 1.0)]
    res = minimize(lambda p: _hw_run(y, *p, trend)[0], x0, bounds=bnd, method="L-BFGS-B")
    a, b, g, phi = res.x
    _, level, tr, seas, errs = _hw_run(y, a, b, g, phi, trend)
    mean = np.array([level + sum(phi ** i for i in range(1, k + 2)) * tr + seas[len(seas) - M + (k % M)] for k in range(h)])
    sig = errs.std(ddof=1) if len(errs) > 2 else y.std() * .2
    w = 1.96 * sig * np.sqrt(np.arange(1, h + 1))      # approximate interval (random-walk-style widening)
    return mean, mean - w, mean + w


def f_ets_sm(train, h):
    m = ETSModel(train, error="add", trend="add", damped_trend=True, seasonal="add", seasonal_periods=M).fit(disp=False)
    sf = m.get_prediction(start=len(train), end=len(train) + h - 1).summary_frame(alpha=.05)
    return sf["mean"].values, sf["pi_lower"].values, sf["pi_upper"].values


def f_sarima_sm(train, h):
    m = SARIMAX(train, order=(1, 1, 1), seasonal_order=(0, 1, 1, M), enforce_stationarity=False,
                enforce_invertibility=False).fit(disp=False)
    fc = m.get_forecast(h); ci = fc.conf_int(alpha=.05)
    return fc.predicted_mean.values, ci.iloc[:, 0].values, ci.iloc[:, 1].values


MODELS = {"Seasonal naive": f_snaive, "Holt-Winters (damped trend)": f_hw,
          "Holt-Winters (no trend)": lambda t, h: f_hw(t, h, trend=False)}
if HAVE_SM:
    MODELS.update({"ETS (statsmodels)": f_ets_sm, "SARIMA(1,1,1)(0,1,1,12)": f_sarima_sm})


def safe_forecast(fn, train, h):
    try:
        out = fn(train, h)
        if np.all(np.isfinite(out[0])):
            return out
    except Exception:
        pass
    return f_snaive(train, h)


# ------------------------------------------------------------------ evaluation
def backtest(s, first_origin=24, step=3):
    """Rolling-origin evaluation: refit at each origin, forecast the next H months, compare with actuals."""
    rec = []
    for origin in range(first_origin, len(s) - H + 1, step):
        train, actual = s.iloc[:origin], s.iloc[origin:origin + H].values
        for name, fn in MODELS.items():
            mean, lo, hi = safe_forecast(fn, train, H)
            rec.append(pd.DataFrame({"model": name, "origin": train.index[-1], "h": range(1, H + 1),
                                     "actual": actual, "forecast": mean, "in_pi": (actual >= lo) & (actual <= hi)}))
    d = pd.concat(rec)
    d["abs_err"] = (d.actual - d.forecast).abs()
    g = d.groupby("model").agg(wape=("abs_err", "sum"), a=("actual", "sum"), mae=("abs_err", "mean"),
                               bias=("forecast", "sum"), pi_coverage=("in_pi", "mean"))
    out = pd.DataFrame({"WAPE_pct": 100 * g.wape / g.a, "MAE": g.mae, "bias_pct": 100 * (g.bias - g.a) / g.a,
                        "pi95_coverage_pct": 100 * g.pi_coverage})
    base = out.loc["Seasonal naive", "WAPE_pct"]
    out["skill_vs_naive_pct"] = 100 * (1 - out.WAPE_pct / base)
    return out.sort_values("WAPE_pct").round(2), d["origin"].nunique()


def classical_decomposition(s):
    trend = s.rolling(M, center=True).mean().rolling(2).mean().shift(-1)
    detr = s - trend
    seas_idx = detr.groupby(detr.index.month).mean(); seas_idx -= seas_idx.mean()
    seasonal = pd.Series(s.index.month.map(seas_idx).values, index=s.index)
    return trend, seasonal, s - trend - seasonal


# ------------------------------------------------------------------ main
def main():
    sq = run_all_sql()
    df = load_sales()
    m = df.set_index("order_date").sales.resample("MS").sum()
    full = pd.date_range(m.index.min(), m.index.max(), freq="MS")
    if len(full) != len(m.reindex(full).dropna()):
        print("WARNING: missing months were interpolated"); m = m.reindex(full).interpolate()
    s = m.asfreq("MS")
    n = len(s)
    print(f"Series: {n} months ({s.index[0]:%Y-%m} to {s.index[-1]:%Y-%m}). statsmodels available: {HAVE_SM}")

    # ---- decomposition (trend / seasonality)
    if HAVE_SM:
        r = STL(s, period=M, robust=True).fit(); trend, seasonal, resid = r.trend, r.seasonal, r.resid
    else:
        trend, seasonal, resid = classical_decomposition(s)
    fig, axes = plt.subplots(4, 1, figsize=(10, 9), sharex=True)
    for ax, (t, x, c) in zip(axes, [("Observed", s, BLUE), ("Trend", trend, GREEN), ("Seasonality", seasonal, RED), ("Residual", resid, GREY)]):
        ax.plot(x.index, x.values / 1e3, color=c); ax.set_ylabel(f"{t}\n(thousand)")
    axes[0].set_title("Monthly sales: trend and seasonality" + (" (STL)" if HAVE_SM else " (classical decomposition)"))
    fig.tight_layout(); fig.savefig(FIG / "decomposition.png", dpi=150); plt.close(fig)
    season_idx = seasonal.groupby(seasonal.index.month).mean()
    peak_m, low_m = int(season_idx.idxmax()), int(season_idx.idxmin())
    yrs = s.groupby(s.index.year).sum(); last_full_year = int(yrs.index[-1] if len(s.loc[str(yrs.index[-1])]) == 12 else yrs.index[-2])
    ly = s.loc[str(last_full_year)]; q4_share = 100 * ly[ly.index.month >= 10].sum() / ly.sum()
    stat = {}
    if HAVE_SM:
        stat = {"adf_p_level": adfuller(s)[1], "adf_p_diff1": adfuller(s.diff().dropna())[1]}
        pd.Series(stat).round(4).to_csv(TAB / "stationarity_adf.csv", header=["p_value"])

    # ---- model comparison by rolling-origin backtest
    comp, n_orig = backtest(s)
    comp.to_csv(TAB / "model_comparison.csv")
    print(f"\nRolling-origin backtest ({n_orig} origins, horizon {H} months):\n{comp.to_string()}")
    best = comp.index[0]
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.barh(comp.index[::-1], comp.WAPE_pct[::-1], color=[GREEN if i == best else BLUE for i in comp.index[::-1]])
    for i, v in enumerate(comp.WAPE_pct[::-1]): ax.text(v + .2, i, f"{v:.1f}%", va="center")
    ax.set(title="Backtest error by model (lower is better)", xlabel="WAPE (%)"); fig.tight_layout()
    fig.savefig(FIG / "model_comparison.png", dpi=150); plt.close(fig)

    # ---- final forecast for the next quarter
    mean, lo, hi = safe_forecast(MODELS[best], s, H)
    idx = pd.date_range(s.index[-1] + pd.offsets.MonthBegin(1), periods=H, freq="MS")
    ly_vals = s.reindex(idx - pd.DateOffset(years=1)).values
    fc = pd.DataFrame({"month": idx.strftime("%Y-%m"), "forecast": mean.round(0), "lower_95": lo.round(0), "upper_95": hi.round(0),
                       "same_month_last_year": ly_vals.round(0), "yoy_pct": (100 * (mean / ly_vals - 1)).round(1)})
    fc.to_csv(TAB / "forecast_next_quarter.csv", index=False)
    q_fc, q_ly = mean.sum(), np.nansum(ly_vals)
    qlabel = f"{idx[0].year}-Q{(idx[0].month + 2) // 3}" if idx[0].month % 3 == 1 else f"next {H} months"
    print(f"\n{qlabel} forecast ({best}): {q_fc:,.0f}  vs same period last year {q_ly:,.0f} ({100 * (q_fc / q_ly - 1):+.1f}%)")

    hist = s.iloc[-36:]
    fig, ax = plt.subplots(figsize=(11, 5))
    ax.plot(hist.index, hist.values / 1e3, color=BLUE, marker="o", ms=3, label="Actual")
    ax.plot([hist.index[-1], idx[0]], [hist.iloc[-1] / 1e3, mean[0] / 1e3], color=RED, ls="--", lw=1)
    ax.plot(idx, mean / 1e3, color=RED, marker="o", label=f"Forecast ({best})")
    ax.fill_between(idx, lo / 1e3, hi / 1e3, color=RED, alpha=.18, label="~95% interval")
    ax.plot(idx, ly_vals / 1e3, color=GREY, ls=":", marker="s", ms=4, label="Same months last year")
    ax.set(title=f"Sales forecast, {qlabel}: ${q_fc / 1e3:,.0f}K ({100 * (q_fc / q_ly - 1):+.1f}% vs last year)", ylabel="Sales (thousand)")
    ax.legend(); fig.tight_layout(); fig.savefig(FIG / "sales_forecast.png", dpi=150); plt.close(fig)

    # ---- regional forecast (same model family)
    rows = []
    for reg, g in df.groupby("region"):
        sr = g.set_index("order_date").sales.resample("MS").sum().reindex(s.index, fill_value=0.0).asfreq("MS")
        fr, _, _ = safe_forecast(MODELS[best], sr, H)
        ly_r = sr.reindex(idx - pd.DateOffset(years=1)).values
        rows.append({"region": reg, "forecast": fr.sum(), "same_period_last_year": ly_r.sum(), "yoy_pct": 100 * (fr.sum() / ly_r.sum() - 1)})
    rf = pd.DataFrame(rows)
    rf["raw_forecast"] = rf.forecast
    rf["forecast"] = rf.raw_forecast * q_fc / rf.raw_forecast.sum()      # top-down reconciliation: regions add up to the total forecast
    rf["yoy_pct"] = 100 * (rf.forecast / rf.same_period_last_year - 1)
    rf = rf.sort_values("yoy_pct"); rf.round(1).to_csv(TAB / "forecast_by_region.csv", index=False)
    fig, ax = plt.subplots(figsize=(8, 4.5)); x = np.arange(len(rf))
    ax.bar(x - .2, rf.same_period_last_year / 1e3, .4, color=GREY, label="Same period last year")
    ax.bar(x + .2, rf.forecast / 1e3, .4, color=BLUE, label="Forecast")
    for i, v in enumerate(rf.yoy_pct): ax.text(i + .2, rf.forecast.iloc[i] / 1e3, f"{v:+.0f}%", ha="center", va="bottom", fontsize=9)
    ax.set_xticks(x); ax.set_xticklabels(rf.region); ax.set(title=f"Regional forecast, {qlabel}", ylabel="Sales (thousand)"); ax.legend()
    fig.tight_layout(); fig.savefig(FIG / "regional_forecast.png", dpi=150); plt.close(fig)

    # ---- recommendations (all numbers computed)
    mx, prod, disc, reg4 = sq["05_region_category_matrix"], sq["06_top_bottom_products"], sq["07_discount_impact"], sq["04_region_performance"]
    yr = int(reg4.yr.max()); reg4 = reg4[reg4.yr == yr].sort_values("margin_pct")
    under = mx[mx.status == "Underperforming"]
    bottom = prod[prod.bucket == "Bottom"]
    d0, dh = disc.iloc[0], disc.iloc[-1]
    mn = lambda k: pd.Timestamp(2000, k, 1).strftime("%B")
    best_row = comp.iloc[0]
    L = [f"# Business recommendations (auto-generated from the data currently loaded)\n",
         f"## Forecast: {qlabel}\n",
         f"- **Expected sales: ${q_fc:,.0f}** ({100 * (q_fc / q_ly - 1):+.1f}% vs the same period last year). Monthly 95% bounds: "
         f"${lo.sum():,.0f} to ${hi.sum():,.0f} (summed monthly bounds, so deliberately conservative).",
         f"- Model: **{best}**, chosen by rolling-origin backtest ({n_orig} origins, {H}-month horizon): WAPE {best_row.WAPE_pct:.1f}%, "
         f"{best_row.skill_vs_naive_pct:+.1f}% vs the seasonal-naive benchmark.",
         f"- Seasonality: peak month is **{mn(peak_m)}**, weakest is **{mn(low_m)}**; Q4 delivers {q4_share:.0f}% of {last_full_year} sales.",
         f"- Weakest regional outlook: **{rf.iloc[0].region}** ({rf.iloc[0].yoy_pct:+.1f}% vs last year); strongest: **{rf.iloc[-1].region}** ({rf.iloc[-1].yoy_pct:+.1f}%).\n",
         f"## Who underperforms ({yr})\n",
         f"- Region x category cells below BOTH company margin and company growth: " +
         ("; ".join(f"**{r.region} / {r.category}** (margin {r.margin_pct:.1f}%, growth {r.yoy_pct:+.1f}%)" for r in under.itertuples()) if len(under) else "none") + ".",
         f"- Lowest-margin region: **{reg4.iloc[0].region}** at {reg4.iloc[0].margin_pct:.1f}% (company {mx.company_margin_pct.iloc[0]:.1f}%).",
         f"- Bottom products lose ${-bottom.profit.sum():,.0f} in total; worst three: " + ", ".join(f"{p}" for p in bottom.product_name.head(3)) + ".\n",
         "## Recommended actions (validate each with a controlled test)\n",
         f"1. **Discount discipline:** lines discounted above 40% earn a {dh.margin_pct:.1f}% margin vs {d0.margin_pct:.1f}% with no discount; "
         f"{dh.loss_making_lines_pct:.0f}% of those lines lose money. Set approval thresholds for deep discounts.",
         f"2. **Fix or exit loss-making products** in the bottom-10 list (reprice, renegotiate cost, or delist).",
         f"3. **Target the underperforming region/category cells** above with margin recovery (pricing, discount caps) before chasing more volume.",
         f"4. **Plan inventory and staffing for the forecast**: build stock ahead of {mn(peak_m)} and avoid over-stocking in {mn(low_m)}.",
         f"5. **Track forecast accuracy monthly** and retrain; re-run after each new month of data.\n",
         "## Caveats\n",
         f"- Only {n} monthly observations: intervals are wide and only simple seasonal models are reliable. Treat the forecast as a planning range.",
         "- The forecast assumes the past pattern continues; promotions, pricing changes or shocks are not modelled.",
         "- Regional forecasts are fitted independently on smaller, noisier series, then scaled so the regions add up to the total forecast." + ("" if HAVE_SM else " statsmodels models were not available in this run (built-in Holt-Winters used).")]
    (OUT / "recommendations.md").write_text("\n".join(L), encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
