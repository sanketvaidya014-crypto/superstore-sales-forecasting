"""SQL reporting layer + KPI dashboard.  Usage: python src/reporting.py  (after load_db.py)"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns

from common import FIG, run_all_sql

sns.set_theme(style="whitegrid", context="notebook")
BLUE, RED, GREEN = "#2F5D8A", "#C0504D", "#3E8E5A"


def card(ax, title, value, delta, good):
    ax.set_facecolor("#F3F6FA"); ax.set_xticks([]); ax.set_yticks([]); ax.grid(False)
    for s in ax.spines.values(): s.set_edgecolor("#D5DCE6")
    ax.text(.06, .74, title, fontsize=11, color="#555", transform=ax.transAxes)
    ax.text(.06, .30, value, fontsize=24, fontweight="bold", color="#1F2D3D", transform=ax.transAxes)
    ax.text(.62, .34, delta, fontsize=12, color=GREEN if good else RED, fontweight="bold", transform=ax.transAxes)


def main():
    sq = run_all_sql()
    k = sq["01_kpi_by_year"]; cur, prev = k.iloc[-1], k.iloc[-2]
    yr = int(cur.yr)

    def monthly(ax):
        m = sq["02_monthly_sales"]
        ax.plot(m.month, m.sales / 1e3, color=BLUE, lw=1.4, label="Monthly sales")
        ax.plot(m.month, m.sales_ma3 / 1e3, color=RED, lw=2, label="3-month average")
        ax.set(title="Monthly sales", ylabel="Sales (thousand)")
        ax.set_xticks(range(0, len(m), 6)); ax.set_xticklabels(m.month.iloc[::6], rotation=45, ha="right"); ax.legend(fontsize=8)

    def quarterly(ax):
        p = sq["03_quarterly_sales"].pivot(index="qtr", columns="yr", values="sales") / 1e3
        p.plot(kind="bar", ax=ax, color=sns.color_palette("Blues", len(p.columns)), width=.8)
        ax.set(title="Quarterly sales by year", xlabel="Quarter", ylabel="Sales (thousand)"); ax.legend(title="", fontsize=8, ncol=2)
        ax.set_xticklabels([f"Q{q}" for q in p.index], rotation=0)

    def region(ax):
        r = sq["04_region_performance"]; r = r[r.yr == yr]
        ax.scatter(r.sales_yoy_pct, r.margin_pct, s=r.sales / r.sales.max() * 1500, color=BLUE, alpha=.6)
        for _, x in r.iterrows(): ax.annotate(x.region, (x.sales_yoy_pct, x.margin_pct), ha="center", fontsize=10, fontweight="bold")
        ax.axhline(cur.margin_pct, color=RED, ls="--", lw=1); ax.axvline(cur.sales_yoy_pct, color=RED, ls="--", lw=1)
        ax.set(title=f"Regions {yr}: growth vs margin (bubble = sales)", xlabel="Sales YoY growth (%)", ylabel="Profit margin (%)")
        ax.margins(.25)

    def products(ax):
        p = sq["06_top_bottom_products"]; p = pd_concat(p)
        ax.barh([n[:30] for n in p.product_name], p.profit / 1e3, color=[GREEN if v > 0 else RED for v in p.profit])
        ax.invert_yaxis(); ax.set(title="Top 5 / bottom 5 products by profit", xlabel="Profit (thousand)")

    def discount(ax):
        d = sq["07_discount_impact"]
        ax.bar(d.discount_band.str[3:], d.margin_pct, color=[GREEN if v > 0 else RED for v in d.margin_pct])
        for i, v in enumerate(d.margin_pct): ax.text(i, v + (.6 if v >= 0 else -1.8), f"{v:.1f}%", ha="center", fontsize=9)
        ax.axhline(0, color="k", lw=.8); ax.set(title="Profit margin by discount depth", ylabel="Margin (%)")

    def heat(ax):
        mx = sq["05_region_category_matrix"].pivot(index="region", columns="category", values="margin_pct")
        sns.heatmap(mx, annot=True, fmt=".1f", cmap="RdYlGn", center=float(cur.margin_pct), ax=ax, cbar=False)
        ax.set(title=f"Margin % by region x category ({yr})", xlabel="", ylabel="")

    charts = [("monthly_sales", monthly), ("quarterly_sales", quarterly), ("region_growth_vs_margin", region),
              ("top_bottom_products", products), ("discount_vs_margin", discount), ("margin_heatmap", heat)]
    for name, fn in charts:
        fig, ax = plt.subplots(figsize=(8, 4.6)); fn(ax); fig.tight_layout()
        fig.savefig(FIG / f"{name}.png", dpi=150); plt.close(fig)

    fig = plt.figure(figsize=(21, 13)); gs = fig.add_gridspec(3, 12, height_ratios=[.4, 1, 1], hspace=.5, wspace=2)
    cards = [(f"Sales FY{yr}", f"${cur.sales / 1e6:,.2f}M", f"{cur.sales_yoy_pct:+.1f}% YoY", cur.sales_yoy_pct >= 0),
             (f"Profit FY{yr}", f"${cur.profit / 1e3:,.0f}K", f"{cur.profit_yoy_pct:+.1f}% YoY", cur.profit_yoy_pct >= 0),
             ("Profit margin", f"{cur.margin_pct:.1f}%", f"{cur.margin_pct - prev.margin_pct:+.1f} pp", cur.margin_pct >= prev.margin_pct),
             ("Orders", f"{int(cur.orders):,}", f"{cur.orders_yoy_pct:+.1f}% YoY", cur.orders_yoy_pct >= 0)]
    for i, c in enumerate(cards): card(fig.add_subplot(gs[0, i * 3:(i + 1) * 3]), *c)
    for i, (_, fn) in enumerate(charts):
        r, c = divmod(i, 3); fn(fig.add_subplot(gs[1 + r, c * 4:(c + 1) * 4]))
    fig.suptitle("Retail Sales KPI Dashboard", fontsize=19, fontweight="bold", y=.97)
    fig.savefig(FIG / "kpi_dashboard.png", dpi=120, bbox_inches="tight"); plt.close(fig)
    print(k.to_string(index=False)); print(f"\nDashboard saved to {FIG / 'kpi_dashboard.png'}")


def pd_concat(p):
    import pandas as pd
    return pd.concat([p[p.bucket == "Top"].head(5), p[p.bucket == "Bottom"].head(5).sort_values("profit", ascending=False)])


if __name__ == "__main__":
    main()
