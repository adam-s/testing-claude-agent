import csv
from collections import defaultdict

with open('data/sales.csv') as f:
    rows = list(csv.DictReader(f))

total_revenue = sum(float(r['revenue']) for r in rows)
print(f"Total Revenue: ${total_revenue:.2f}")

units_by_product = defaultdict(int)
revenue_by_product = defaultdict(float)
count_by_product = defaultdict(int)
for r in rows:
    units_by_product[r['product']] += int(r['units'])
    revenue_by_product[r['product']] += float(r['revenue'])
    count_by_product[r['product']] += 1

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

avg_order = {p: revenue_by_product[p] / count_by_product[p] for p in revenue_by_product}
best_avg = max(avg_order.items(), key=lambda x: x[1])
print(f"Product with Highest Average Order Value: {best_avg[0]} (${best_avg[1]:.2f})")
