# Practice 04: Relational Database Design & Partitioning

## Objective

Design and implement a robust, range-partitioned e-commerce database schema in PostgreSQL, ingest raw data, and analyze execution performance. You will gain hands-on experience working with advanced relational structures, including partitioned tables with composite foreign key references, session-isolated temporary staging tables, and both dynamic and materialized views.

---

## Deliverables

Submit:

* **SQL queries** for all tasks.
* **Screenshots with query and output** clearly visible for each task.

---

## Core Terminology

* **Table Partitioning** — The structural design of breaking down a large logical table into smaller, physically independent child tables bounded by key range limits.
* **Partition Pruning** — A query planning mechanism where the optimizer skips scanning unrelated child tables based on query filter conditions to increase execution speed.
* **Temporary Table** — A short-lived sandbox table that stores data locally within a single connection boundary and is automatically destroyed when the session terminates.
* **Standard View** — A virtual reporting layer defined by a query that calculates its results dynamically on demand, reflecting live changes to underlying database fields instantly.
* **Materialized View** — A persistent reporting architecture that executes an aggregation once and caches the physical results to disk to avoid expensive computation over long records.

---

## Task 1: Complete Schema Design & Implementation

Write a single, cohesive SQL script creating all tables. You must establish the tables sequentially based on their dependencies to avoid foreign key errors.

### Step 1: Design the Base Dimension Tables

#### `users.csv`

* **`user_id`** *(VARCHAR)* — Primary Key.
* **`name`** *(VARCHAR)*
* **`email`** *(VARCHAR)* — Unique Constraint.

#### `products.csv`

* **`product_id`** *(VARCHAR)* — Primary Key.
* **`product_name`** *(VARCHAR)*
* **`category`** *(VARCHAR)* 
* **`brand`** *(VARCHAR)* 
* **`price`** *(DECIMAL)* — Retail price (Requires `CHECK > 0`).
* **`rating`** *(FLOAT)* — Customer rating (Nullable; requires `CHECK` between 0 and 5).

---

### Step 2: Implement the Partitioned Orders Architecture

Include this script exactly as written to build the status type, the partitioned master table, and its physical annual chunks:

```sql
-- Define custom ENUM type for order lifecycle states
CREATE TYPE order_status_enum AS ENUM ('shipped', 'processing', 'completed', 'cancelled', 'returned');

-- Define the Partitioned Master Orders Table
CREATE TABLE orders (
    order_id     VARCHAR(50) NOT NULL,
    user_id      VARCHAR(50) NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    order_date   TIMESTAMP NOT NULL,
    order_status order_status_enum NOT NULL,
    PRIMARY KEY (order_id, order_date)
) PARTITION BY RANGE (order_date);

-- Create physical standalone child partitions for 2024 and 2025
CREATE TABLE orders_2024 PARTITION OF orders
    FOR VALUES FROM ('2024-01-01 00:00:00') TO ('2025-01-01 00:00:00');

CREATE TABLE orders_2025 PARTITION OF orders
    FOR VALUES FROM ('2025-01-01 00:00:00') TO ('2026-01-01 00:00:00');

```

---

### Step 3: Design the Dependent Fact Table

#### `order_items.csv`

* **`order_item_id`** *(VARCHAR)* — Primary Key.
* **`order_id`** *(VARCHAR)* 
* **`order_date`** *(TIMESTAMP)*
* **`product_id`** *(VARCHAR)* — Foreign Key referencing `products(product_id)` (`ON DELETE RESTRICT`).
* **`quantity`** *(INTEGER)* — Item count (Requires `CHECK > 0`).
* **`item_price`** *(DECIMAL)* — Captured purchase price (Requires `CHECK >= 0`).
* **Composite Foreign Key Constraint** — To match the parent partition layout, link your composite references directly at the table level using this exact constraint:

```sql
FOREIGN KEY (order_id, order_date) REFERENCES orders(order_id, order_date) ON DELETE CASCADE

```

---

## Task 2: Data Ingestion & Architecture Verification

> **Troubleshooting Note:** If you encounter errors during the data loading process (such as `"extra data after last expected column"`), it is highly likely that your table structures do not perfectly match the source CSV files. Double-check your `CREATE TABLE` definitions from Task 1 to ensure all columns, data types, and sequences are exactly correct before running the ingestion.

## Task 2: Data Ingestion & Architecture Verification

### Step 1: Ingest the Data

Populate your schema using **one** of the following methods.

#### Way 1: Automated Script (Recommended)

Initialize a virtual environment, install dependencies, and run the tracking script with your database credentials configured inside `load_ecom_sales.py`:

* **Windows:**

```bash
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
python load_ecom_sales.py

```

* **Linux/Mac:**

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 load_ecom_sales.py

```

#### Way 2: Manual CSV Ingestion

Download the source files from [Kaggle](https://www.kaggle.com/datasets/anechytailenko/e-commerce-practice-04-dataset) and populate your database using one of the following approaches. Ensure you execute these steps sequentially (`users` -> `products` -> `orders` -> `order_items`) to respect structural foreign key constraints:

* **Via DataGrip:** Right-click the target table -> **Import Data from File...** -> select your matching downloaded CSV file (repeat this process for `users`, `products`, `orders`, and `order_items`).
* **Via Terminal (psql):** Use the commands below, replacing the placeholders with your actual connection details:

```bash
psql -h <HOST> -U <USERNAME> -d <DB_NAME> -c "\copy users FROM '<PATH_TO_USERS_CSV>' WITH (FORMAT csv, HEADER true);"
psql -h <HOST> -U <USERNAME> -d <DB_NAME> -c "\copy products FROM '<PATH_TO_PRODUCTS_CSV>' WITH (FORMAT csv, HEADER true);"
psql -h <HOST> -U <USERNAME> -d <DB_NAME> -c "\copy orders FROM '<PATH_TO_ORDERS_CSV>' WITH (FORMAT csv, HEADER true);"
psql -h <HOST> -U <USERNAME> -d <DB_NAME> -c "\copy order_items FROM '<PATH_TO_ORDER_ITEMS_CSV>' WITH (FORMAT csv, HEADER true);"

```

> **Note:** If you are using the default local setup, the command is likely:
> `psql -h localhost -U postgres -d postgres -c ...`

---

### Step 2: Structure & Performance Verification

#### 1. Verify Data Existence and Partition Distribution

Execute this single unified query to confirm that records have been successfully loaded into all base dimension and fact tables.

```sql
SELECT 'users' AS layer, count(*) FROM users
UNION ALL
SELECT 'products' AS layer, count(*) FROM products
UNION ALL
SELECT 'orders (master table)' AS layer, count(*) FROM orders
UNION ALL
SELECT 'orders_2024 (child partition)' AS layer, count(*) FROM orders_2024
UNION ALL
SELECT 'orders_2025 (child partition)' AS layer, count(*) FROM orders_2025
UNION ALL
SELECT 'order_items' AS layer, count(*) FROM order_items;

```

#### 2. Verify Performance Optimization using EXPLAIN ANALYZE

Run this statement to analyze the query planner behavior when accessing a localized date range:

```sql
EXPLAIN ANALYZE
SELECT * FROM orders 
WHERE order_date >= '2024-06-01 00:00:00' AND order_date < '2024-07-01 00:00:00';

```

**Verification Requirement:** Look for a `Seq Scan` executed exclusively against the `orders_2024` child table. The `orders_2025` partition should not appear anywhere in the output tree, proving that the unneeded data layer was successfully pruned.

---

## Task 3: Data Staging & Reporting via Temporary Tables

### Objective

You will isolate failed transactions from 2025 into a session-scoped temporary staging table to optimize downstream analytical performance. By caching this specific subset of records, you avoid executing expensive filtering logic over the massive master tables multiple times. You will then query this optimized staging layer to analyze financial loss across product categories.

---

### Step 1: Stage the High-Risk Transactions

Write a `CREATE TEMPORARY TABLE ... AS SELECT` statement to build a temporary table named `temp_revenue_risks`. This table must extract the `order_id` from the `orders` table, filtering strictly for records where:

* The `order_date` is within the year 2025.
* The `order_status` is either `'cancelled'` or `'returned'`.

---

### Step 2: Verify and Generate the Lost Revenue Report

Run the following analytical query to verify your staging table configuration and calculate the total financial deficit across product categories:

```sql
SELECT 
    p.category,
    SUM(oi.quantity * oi.item_price) AS lost_revenue,
    COUNT(DISTINCT trr.order_id) AS impacted_orders
FROM temp_revenue_risks trr
JOIN order_items oi ON trr.order_id = oi.order_id
JOIN products p ON oi.product_id = p.product_id
GROUP BY p.category
ORDER BY lost_revenue DESC;

```

**Note:** The `USING` clause simplifies your join syntax when the shared keys have identical names across tables, automatically merging them and removing the need for explicit table aliases or equality operators. This makes the query cleaner and more readable when working with standardized foreign key names.

---
## Task 4: Dynamic Views vs. Materialized Views

### Objective

Analyze the differences between standard and materialized views under data changes, and practice manually synchronizing a cached data structure.

---

### Theory & Terminology

* **Standard View (Virtual View):** A saved SQL query that acts as a virtual table. It does not store physical data; instead, it executes its underlying query dynamically every time it is referenced, ensuring real-time accuracy.
* **Materialized View:** A database object that executes a query and physically stores (caches) the resulting dataset on disk. It provides significantly faster read times for complex aggregations but creates data staleness until it is explicitly updated.

---

### Step 1: Create the Reporting Structures

Based on the following analytical query, write the appropriate DDL statements to create two database objects side-by-side: a standard view named **`v_brand_summary`** and a materialized view named **`mv_brand_summary`**.

```sql
SELECT 
    brand,
    SUM(quantity) AS total_units_sold,
    SUM(quantity * item_price) AS total_revenue
FROM order_items
JOIN products USING (product_id)
GROUP BY brand;

```

---

### Step 2: Establish the Data Baseline

Run this unified query using `UNION ALL` to check the baseline metrics specifically for the **'Willow'** brand across both view layers before any data alterations:

```sql
SELECT 'Standard View Baseline' AS view_type, brand, total_units_sold, total_revenue 
FROM v_brand_summary WHERE brand = 'Willow'
UNION ALL
SELECT 'Materialized View Baseline', brand, total_units_sold, total_revenue 
FROM mv_brand_summary WHERE brand = 'Willow';

```

---

### Step 3: Add New Data Record

Execute this transactional block to insert a new customer, order, product brand ('Willow'), and corresponding line item:

```sql
-- 1. Add a new customer
INSERT INTO users (user_id, name, email) 
VALUES ('usr_willow_test', 'Willow Tester', 'willow.test@example.com');

-- 2. Add a new master transaction record
INSERT INTO orders (order_id, user_id, order_date, order_status) 
VALUES ('ord_willow_test', 'usr_willow_test', '2025-06-01 10:00:00', 'completed');

-- 3. Introduce the new 'Willow' brand into the product catalog
INSERT INTO products (product_id, product_name, category, brand, price, rating)
VALUES ('prod_willow_test', 'Willow Eco Desk', 'Furniture', 'Willow', 250.00, 5.0);

-- 4. Create the corresponding purchase line item
INSERT INTO order_items (order_item_id, order_id, order_date, product_id, quantity, item_price)
VALUES ('item_willow_test', 'ord_willow_test', '2025-06-01 10:00:00', 'prod_willow_test', 1, 250.00);

```

---

### Step 4: Compare Sync Behavior

Re-run the targeted brand filter query to observe how the aggregated metrics within each view layer respond to the new record insertion:

```sql
SELECT 'Standard View Post-Insert' AS view_type, brand, total_units_sold, total_revenue 
FROM v_brand_summary WHERE brand = 'Willow'
UNION ALL
SELECT 'Materialized View Post-Insert', brand, total_units_sold, total_revenue 
FROM mv_brand_summary WHERE brand = 'Willow';

```

**Observation Requirement:**

* Notice that the standard view `v_brand_summary` instantly reflects the newly added unit sold and revenue metrics because it processes live table data in real time.
* Notice that the materialized view `mv_brand_summary` output remains unchanged (stale or empty) because its data is safely cached on disk and does not scan the source tables dynamically.

---

### Step 5: Refresh the Cache and Verify Synchronization

To bring the materialized view up to date, execute the refresh maintenance command:

```sql
REFRESH MATERIALIZED VIEW mv_brand_summary;

```

Once executed, re-run the validation query one final time to verify that both data layers have synchronized and display identical, up-to-date metrics:

```sql
SELECT 'Standard View Final' AS view_type, brand, total_units_sold, total_revenue 
FROM v_brand_summary WHERE brand = 'Willow'
UNION ALL
SELECT 'Materialized View Final', brand, total_units_sold, total_revenue 
FROM mv_brand_summary WHERE brand = 'Willow';

```