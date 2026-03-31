import Database from 'better-sqlite3';
import { readFileSync } from 'fs';

const db = new Database(':memory:');
db.exec(readFileSync('seed.sql', 'utf8'));

const running_total = db.prepare(`
  SELECT customer_id, id as order_id, order_date, amount,
    SUM(amount) OVER (PARTITION BY customer_id ORDER BY order_date, id) as running_total
  FROM orders
  ORDER BY customer_id, order_date, id
`).all();

const rank_customers = db.prepare(`
  SELECT customer_id,
    SUM(amount) as total_spend,
    DENSE_RANK() OVER (ORDER BY SUM(amount) DESC) as rank
  FROM orders
  GROUP BY customer_id
  ORDER BY rank
`).all();

const prev_order = db.prepare(`
  SELECT customer_id, id as order_id, order_date, amount,
    LAG(amount) OVER (PARTITION BY customer_id ORDER BY order_date, id) as prev_amount
  FROM orders
  ORDER BY customer_id, order_date, id
`).all();

const moving_avg = db.prepare(`
  SELECT customer_id, id as order_id, order_date, amount,
    ROUND(AVG(amount) OVER (PARTITION BY customer_id ORDER BY order_date, id ROWS BETWEEN 2 PRECEDING AND CURRENT ROW), 2) as moving_avg
  FROM orders
  ORDER BY customer_id, order_date, id
`).all();

const pct_of_total = db.prepare(`
  SELECT customer_id, id as order_id, order_date, amount,
    ROUND(amount * 100.0 / SUM(amount) OVER (PARTITION BY customer_id), 2) as pct_of_total
  FROM orders
  ORDER BY customer_id, order_date, id
`).all();

console.log(JSON.stringify({ running_total, rank_customers, prev_order, moving_avg, pct_of_total }));
