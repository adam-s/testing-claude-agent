import csv
from collections import defaultdict

rows = []
with open('data/sales.csv') as f:
    for row in csv.DictReader(f):
        rows.append(row)

total_revenue = sum(float(r['revenue']) for r in rows)
print(f"Total Revenue: ${total_revenue:.2f}")

units_by_product = defaultdict(int)
for r in rows:
    units_by_product[r['product']] += int(r['units'])
top3 = sorted(units_by_product.items(), key=lambda x: x[1], reverse=True)[:3]
print("Top 3 Products by Units Sold:")
for product, units in top3:
    print(f"  {product}: {units}")

revenue_by_region = defaultdict(float)
for r in rows:
    revenue_by_region[r['region']] += float(r['revenue'])
print("Revenue by Region:")
for region, rev in sorted(revenue_by_region.items(), key=lambda x: x[1], reverse=True):
    print(f"  {region}: ${rev:.2f}")

revenue_by_month = defaultdict(float)
for r in rows:
    month = r['date'][:7]
    revenue_by_month[month] += float(r['revenue'])
best_month = max(revenue_by_month.items(), key=lambda x: x[1])
print(f"Month with Highest Revenue: {best_month[0]} (${best_month[1]:.2f})")

revenue_orders = defaultdict(lambda: [0.0, 0])
for r in rows:
    revenue_orders[r['product']][0] += float(r['revenue'])
    revenue_orders[r['product']][1] += 1
avg_order = {p: v[0] / v[1] for p, v in revenue_orders.items()}
best_product = max(avg_order.items(), key=lambda x: x[1])
print(f"Product with Highest Average Order Value: {best_product[0]} (${best_product[1]:.2f})")
