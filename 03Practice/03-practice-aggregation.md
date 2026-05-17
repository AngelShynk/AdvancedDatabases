# Practice 03: PostgreSQL Aggregation & Analytical Queries Practice

## Objective

The goal of this task is to execute advanced aggregation queries, demonstrate multi-level grouping functionality, and implement analytical window functions for e-commerce performance reporting.

---


## Deliverables

Submit:

* **SQL queries** for all tasks.
* **Screenshots with query and output** clearly visible for each task.

---


## Core Terminology

* **Aggregation** — the process of summarizing multiple rows of data into a single result (e.g., `SUM`, `AVG`, `COUNT`).
* **Grouping** — organizing data into subsets based on specific column values to perform calculations on each set.
* **Window Function** — a function that performs a calculation across a set of table rows that are related to the current row without collapsing them into a single output row.
* **Partitioning** — the division of a result set into groups for a window function to process independently.
* **Frame** — a specific subset of rows within a partition (e.g., "all rows from the start to the current row") used for sliding calculations.

---

## Phase 0: Data Ingestion

Choose **ONE** of the following methods to load the `ecom_sales` dataset into your database.

## Way 1: Automated Script (Recommended)

This method is faster and handles both table creation and data streaming. It simulates a professional Data Engineering pipeline.

### 1. Installation

Set up a virtual environment and install the required libraries in your terminal:

* **Windows:**
```bash
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt

```


* **Linux/Mac:**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

```

### 2. Execution

1. Open **`load_ecom_sales.py`**.
2. Fill in your **Kaggle Credentials** and **PostgreSQL Database** details in the configuration block at the top.
3. Run the script:
* **Windows:** `python load_ecom_sales.py`
* **Linux/Mac:** `python3 load_ecom_sales.py`


*Note: This script automatically creates the `ecom_sales` table for you.*

---

## Way 2: Manual CSV Download

Use this method if you prefer working with local files and manual SQL commands.

### 1. Download the Data

Go to the [Kaggle Dataset](https://www.kaggle.com/datasets/anechytailenko/e-commerce-practice-03-dataset?select=analytical.csv) and download the `analytical.csv` file to your project folder.

### 2. Manual Table Preparation

Execute this SQL in **DataGrip** to create the target table:

```sql
DROP TABLE IF EXISTS ecom_sales;

CREATE TABLE ecom_sales (
    order_item_id   VARCHAR(50) PRIMARY KEY,
    order_id        VARCHAR(50) NOT NULL,
    order_date      TIMESTAMP NOT NULL,
    order_status    VARCHAR(50),
    product_id      VARCHAR(50),
    product_name    VARCHAR(255),
    category        VARCHAR(100),
    brand           VARCHAR(100),
    customer_email  VARCHAR(255),
    quantity        INTEGER,
    item_price      DECIMAL(12, 2)
);

```

### 3. Import the CSV

* **Via DataGrip:** Right-click the `ecom_sales` table -> **Import Data from File...** -> select your downloaded `analytical.csv`.
* **Via Terminal (psql):** Use the command below, replacing the placeholders with your actual connection details:

```bash
psql -h <HOST> -U <USERNAME> -d <DB_NAME> -c "\copy ecom_sales FROM '<PATH_TO_ANALYTICAL_CSV>' WITH (FORMAT csv, HEADER true);"

```

> **Note:** If you are using the default local setup, the command is likely:
> `psql -h localhost -U postgres -d postgres -c ...`

---

## 3. Verification & Monitoring

Regardless of the method chosen, verify that the data is loaded correctly.

```sql
-- 1. Confirm total row count
SELECT count(*) FROM ecom_sales;

-- 2. Check table health in system views
SELECT relname, n_live_tup 
FROM pg_stat_user_tables 
WHERE relname = 'ecom_sales';

-- 3. Monitor active sessions (run while loading to see the COPY process)
SELECT pid, usename, state, query 
FROM pg_stat_activity 
WHERE state = 'active';

```

---

## Task 1: Performance Analysis by Category

### The Scenario

The marketing department is evaluating product demand. They want to focus their analysis on established categories that have successfully processed multiple sales. By filtering out low-volume categories, they can ensure their budget is spent on areas with proven customer interest.

### The Task

Write a query that returns a report summarizing sales performance for each category.

**Query Requirements:**

1. **Columns:** Select `category`, the total number of items sold (`SUM(quantity)`), the total revenue generated (`SUM(quantity * item_price)`), and the average price of an item (`AVG(item_price)`).
2. **Filter (Row-level):** Only include orders where the `order_status` is `'completed'`.
3. **Filter (Group-level):** Use `HAVING` to only show categories where the **total number of items sold** is greater than **3**.
4. **Sorting:** Sort the results so the category with the **highest revenue** is at the top.

---

## Task 2: Multi-Level Aggregation with `GROUPING SETS`

### Syntax:

```sql
SELECT
    c1,
    c2,
    aggregate_function(c3)
FROM
    table_name
GROUP BY
    GROUPING SETS (
        (c1, c2),
        (c1),
        ()
    );

```

### The Concept

Standard grouping produces a single level of aggregation. To generate subtotals and grand totals across multiple dimensions simultaneously without executing multiple independent queries combined via high-overhead `UNION ALL` statements, PostgreSQL provides the **[GROUPING SETS](https://neon.com/postgresql/tutorial/grouping-sets)** clause.

**Abstract Logic:**

$$\text{GROUPING SETS}((A, B), (A), ()) \approx (\text{GROUP BY } A, B) \cup (\text{GROUP BY } A) \cup (\text{GROUP BY ALL})$$

### Why Use COALESCE with Grouping Sets?

When evaluating higher-level aggregation planes (like a category subtotal or a grand total), the query engine leaves the excluded columns blank, automatically returning structural `NULL` values. Wrapping these columns in the **[COALESCE](https://neon.com/postgresql/tutorial/coalesce)** function intercepts these blank fields and replaces them with clear, presentation-ready reporting labels.

---

### The Task

The inventory manager needs a hierarchical sales report to evaluate brand performance alongside category and company-wide totals.

**Query Requirements:**

1. **Columns & Aliases**:
* Select the category field using **`COALESCE(category, 'ALL CATEGORIES')`**, explicitly aliasing the output column as **`category`**.
* Select the brand field using **`COALESCE(brand, 'ALL BRANDS')`**, explicitly aliasing the output column as **`brand`**.


2. **Aggregates & Aliases**:
* Use `SUM(quantity * item_price)` to track total sales, explicitly aliasing the output column as **`total_revenue`**.


3. **Grouping Sets Hierarchy**: Use the `GROUPING SETS` clause to define the following evaluation planes:
* **Brand Level**: Group by both `category` and `brand`.
* **Category Subtotal**: Group by `category` only.
* **Grand Total**: Use an empty set `()` to calculate the total for all combined records.


4. **Filter**: Only include orders with a `'completed'` status.
5. **Sorting**: Order the final unified grid by `category` (ascending) and `total_revenue` (descending).

---


## Task 3: Competition & Ranking with `DENSE_RANK`

### The Scenario

The merchandising team wants to identify "Luxury Tier" products. They need a list of the **top 3 most expensive products** within each category to determine premium shelf placement.

### The Task

Write a query to rank products by their price within each specific category and filter the results to show only the top 3.

**Query Requirements:**

1. **Columns & Aliases:** Select `category`, `product_name`, `item_price`, and your rank column, explicitly aliasing it as **`product_rank`**.
2. **Grouping & Uniqueness:** Group by `category`, `product_name`, and `item_price` to collapse individual line-item transactions into unique product rows before calculating the rank.
3. **Analytical Ranking:** Calculate a rank for each unique product based on its price, partitioned by its category (most expensive = #1).
4. **Filtering:**
* Only include orders with a `'completed'` status.
* **Keep only products with a rank of 3 or less.**


5. **Sorting:** Order the final result by `category` (ascending) and `product_rank` (ascending).

> **Note:**
> * **Function Requirement:** Use the **[DENSE_RANK()](https://neon.com/postgresql/window-function/dense_rank-function)** function to calculate the retail price ordering partitions for each category.
> * **Filtering Constraint:** Because window functions cannot be evaluated directly within a standard `WHERE` clause, you must wrap your ranking logic inside a **CTE (WITH clause)** or a **Subquery** to isolate the top 3 spots.
> 
> 

---



## Task 4: Customer Loyalty & the `WINDOW` Clause

If you use multiple window functions in a query with the same partition and order, your code can become repetitive:

```sql
-- Repetitive Syntax
SELECT 
    wf1() OVER(PARTITION BY c1 ORDER BY c2), 
    wf2() OVER(PARTITION BY c1 ORDER BY c2) 
FROM table_name;

```

You can use the **WINDOW clause** to shorten the query and improve maintainability:

```sql
-- Clean Syntax using WINDOW Clause
SELECT 
    wf1() OVER w, 
    wf2() OVER w 
FROM table_name 
WINDOW w AS (PARTITION BY c1 ORDER BY c2);

```

### The Scenario

The Marketing team is analyzing **Customer Lifetime Value (CLV)**. They want to see the "growth story" of every customer: how much they have spent in total and how many orders they have placed up to any given point in time.

### The Task

Write a query using the **WINDOW clause** and a specific **frame** to calculate cumulative statistics for each user.

**Query Requirements:**

1. **Columns**: Select `order_date`, `customer_email`, and calculate the individual `order_revenue` (**quantity * item_price**).
2. **Window Functions & Aliases**:
* Use `SUM(quantity * item_price)` to track cumulative spend, explicitly aliasing the output column as **`cumulative_spend`**.
* Use `COUNT(order_id)` to track the running count of orders, explicitly aliasing the output column as **`running_order_count`**.


3. **The Window Definition**: Use the `WINDOW` clause to define a window named `w` that partitions by **`customer_email`** and orders by `order_date`.
4. **Frame Clause**: Within your window definition, use the **[frame specification](https://medium.com/@anusoosanbaby/understanding-frame-specification-in-postgresql-window-functions-b93e0bba9a80)** boundary: `ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW`.
5. **Filter**: Only include `'completed'` orders.