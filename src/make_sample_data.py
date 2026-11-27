"""Generate a SYNTHETIC file with the Superstore schema to test the pipeline end to end.
Numbers produced from it are NOT real findings. Use the real Kaggle dataset for the analysis."""
import numpy as np
import pandas as pd

from common import RAW

rng = np.random.default_rng(11)
SEASON = {1: .60, 2: .55, 3: 1.0, 4: .80, 5: .85, 6: .90, 7: .85, 8: .90, 9: 1.40, 10: .95, 11: 1.60, 12: 1.70}
YEAR_G = {2014: 1.0, 2015: 1.10, 2016: 1.25, 2017: 1.55}
REGIONS = {"West": (.32, ["California", "Washington", "Oregon"]), "East": (.28, ["New York", "Pennsylvania", "Ohio"]),
           "Central": (.23, ["Texas", "Illinois", "Michigan"]), "South": (.17, ["Florida", "Georgia", "Virginia"])}
REG_GROWTH = {"West": 1.0, "East": 1.0, "Central": .95, "South": .75}   # South stagnates in later years
SUBS = {"Furniture": {"Bookcases": (300, .08), "Chairs": (320, .12), "Furnishings": (80, .20), "Tables": (450, .02)},
        "Office Supplies": {"Appliances": (110, .22), "Art": (25, .25), "Binders": (40, .15), "Envelopes": (30, .35),
                            "Fasteners": (12, .30), "Labels": (15, .40), "Paper": (25, .40), "Storage": (120, .15),
                            "Supplies": (60, .05)},
        "Technology": {"Accessories": (90, .25), "Copiers": (1500, .35), "Machines": (700, .10), "Phones": (280, .18)}}
products = []
for cat, subs in SUBS.items():
    for sub, (price, margin) in subs.items():
        for i in range(12):
            products.append((f"{cat[:3].upper()}-{sub[:2].upper()}-{i:04d}", cat, sub, f"{sub} item {i + 1}", price * rng.uniform(.6, 1.5), margin))
cust = [f"CG-{i:05d}" for i in range(800)]
rows, oid, rid = [], 0, 1
for yr, g in YEAR_G.items():
    for mo, sf in SEASON.items():
        n_orders = int(95 * sf * g)
        for _ in range(n_orders):
            oid += 1
            region = rng.choice(list(REGIONS), p=[REGIONS[r][0] for r in REGIONS])
            if rng.random() > REG_GROWTH[region] ** (yr - 2014) and region == "South":
                continue
            day = int(rng.integers(1, 28))
            d = pd.Timestamp(yr, mo, day)
            ship = d + pd.Timedelta(days=int(rng.integers(2, 7)))
            state = rng.choice(REGIONS[region][1])
            for _ in range(int(rng.integers(1, 5))):
                pid, cat, sub, name, price, bm = products[rng.integers(0, len(products))]
                disc_p = [.5, .25, .15, .1] if region != "Central" else [.25, .25, .25, .25]
                disc = float(rng.choice([0, .2, .4, .6], p=disc_p))
                qty = int(rng.integers(1, 8))
                sales = round(price * qty * (1 - disc), 2)
                profit = round(sales * (bm - .55 * disc + rng.normal(0, .05)), 2)
                rows.append([rid, f"US-{yr}-{oid:06d}", f"{d.month}/{d.day}/{d.year}", f"{ship.month}/{ship.day}/{ship.year}",
                             "Standard Class", cust[oid % len(cust)], f"Customer {oid % len(cust)}", rng.choice(["Consumer", "Corporate", "Home Office"]),
                             "United States", f"City {state[:3]}", state, 10000 + oid % 80000, region, pid, cat, sub, name,
                             sales, qty, disc, profit])
                rid += 1
cols = ["Row ID", "Order ID", "Order Date", "Ship Date", "Ship Mode", "Customer ID", "Customer Name", "Segment", "Country",
        "City", "State", "Postal Code", "Region", "Product ID", "Category", "Sub-Category", "Product Name", "Sales",
        "Quantity", "Discount", "Profit"]
pd.DataFrame(rows, columns=cols).to_csv(RAW / "Sample - Superstore.csv", index=False)
print(f"Synthetic sample written: {len(rows):,} order lines, 2014-2017. NOT real data.")
