#!/usr/bin/env python3
import csv
from collections import defaultdict

rows = []
with open("data/sales.csv") as f:
    for row in csv.DictReader(f):
        row["units"] = int(row["units"])
        row["revenue"] = float(row["revenue"])
        rows.append(row)

# 1. Total revenue
total = sum(r["revenue"] for r in rows)
print(f"Total Revenue: ${total:.2f}")

# 2. Top 3 products by units sold
units = defaultdict(int)
for r in rows:
    units[r["product"]] += r["units"]
top3 = sorted(units.items(), key=lambda x: x[1], reverse=True)[:3]
print("Top 3 Products by Units Sold:")
for product, u in top3:
    print(f"  {product}: {u}")

# 3. Revenue by region sorted descending
region_rev = defaultdict(float)
for r in rows:
    region_rev[r["region"]] += r["revenue"]
print("Revenue by Region:")
for region, rev in sorted(region_rev.items(), key=lambda x: x[1], reverse=True):
    print(f"  {region}: ${rev:.2f}")

# 4. Month with highest revenue
month_rev = defaultdict(float)
for r in rows:
    month_rev[r["date"][:7]] += r["revenue"]
best_month, best_rev = max(month_rev.items(), key=lambda x: x[1])
print(f"Month with Highest Revenue: {best_month} (${best_rev:.2f})")

# 5. Product with highest average order value
prod_rev = defaultdict(float)
prod_count = defaultdict(int)
for r in rows:
    prod_rev[r["product"]] += r["revenue"]
    prod_count[r["product"]] += 1
avg = {p: prod_rev[p] / prod_count[p] for p in prod_rev}
best_prod, best_avg = max(avg.items(), key=lambda x: x[1])
print(f"Highest Avg Order Value: {best_prod} (${best_avg:.2f})")
