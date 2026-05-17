# Practice 05: Functions, Stored Procedures, and Database Triggers

## Objective

Design and implement programmable database objects in PostgreSQL using PL/pgSQL. You will gain hands-on experience enforcing domain validation rules at the schema boundary, executing conditional logical routing within functions, orchestrating atomic multi-table transaction blocks within stored procedures, and automating real-time data auditing and integrity barriers using before-and-after database triggers.

---

## Deliverables

Submit:

* **SQL queries** for all structural definitions, verification steps, and reference solutions.
* **Screenshots with query and output** clearly visible for each task's validation phase.

---

## Core Terminology

* **Function** — reusable routine that accepts input arguments, executes procedural logic, and returns a value or a set of values, invoked inline within a query expression or statement.
* **Stored Procedure** — database routine designed to execute complex operations with active transaction control states (such as `COMMIT` or `ROLLBACK`), invoked via the `CALL` statement.
* **Trigger** — automated event listener attached directly to a physical table that intercepts lifecycle modifications (`INSERT`, `UPDATE`, `DELETE`) to execute specialized code automatically.
---

> **Prerequisite Note:** All subsequent tasks assume the use of the tables (`users`, `products`, `orders`, and `order_items`) that were created and filled with data during Practice 4.

---

## Task 1: Input Validation via Domains (IN, DOMAIN)

### Minimal Function Syntax Template:

```sql
CREATE OR REPLACE FUNCTION function_name(parameter_name data_type)
RETURNS return_data_type 
LANGUAGE plpgsql 
AS $$
BEGIN
    RETURN value_or_expression;
END;
$$;

```

### Concept Breakdown:

* **Domain:** A user-defined data type that extends an existing base type (like `VARCHAR` or `NUMERIC`) by adding built-in `CHECK` constraints. It ensures data validation happens automatically at the schema architecture level before a function's code even executes.
* **IN Parameter:** The default parameter mode in PostgreSQL. It passes a value into a function as a read-only argument. The function can read and process this data internally, but it cannot modify the input variable or affect any external state outside the function's scope.

### Provided Domain Creation Script:

```sql
-- Enforces valid email formats requiring a standard local name, '@' symbol, domain, and a 2-4 letter TLD
CREATE DOMAIN secure_email_address AS VARCHAR(255)
CHECK (VALUE ~* '^[A-Za-z0-9._%-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,4}$');
```

### Function Requirements:

1. **Function Definition:** Create a scalar function named `extract_email_provider` from scratch.
2. **Input Parameter:** Accept a single parameter `p_email` of the type `secure_email_address` strictly restricted by the domain.
3. **Return Value:** Extract and return only the domain part of the email address (everything after the `@` symbol). **Note:** Use the built-in PostgreSQL function `split_part(string, delimiter, part_number)` to isolate the domain substring.

### Verify:

```sql
SELECT name, email, extract_email_provider(email::secure_email_address) AS provider 
FROM users;

```

---

## Task 2: Internal Declarations and Conditional Logic within Functions (DECLARE, IF-THEN, OUT)

### Minimal Function Syntax Template:

```sql
CREATE OR REPLACE FUNCTION function_name(
    p_input table_name.column_name%TYPE,
    OUT p_output_1 data_type,
    OUT p_output_2 data_type,
    OUT p_output_3 data_type
)   
LANGUAGE plpgsql
AS $$
DECLARE
    v_local_variable data_type;
BEGIN
    SELECT column_1, column_2 
    INTO p_output_1, v_local_variable
    FROM table_name 
    WHERE id_column = p_input;

    p_output_2 := v_local_variable;

    IF v_local_variable > threshold_value THEN
        p_output_3 := 'Value A';
    ELSE
        p_output_3 := 'Value B';
    END IF;
    
    -- Functions with OUT parameters use a blank RETURN to exit
    RETURN; 
END;
$$;

```

### Concept Breakdown:

* **Local Variables (`DECLARE`):** Temporary in-memory placeholders that store intermediate query values and vanish when the function execution scope terminates.
* **Conditional Logic (`IF-THEN-ELSE`):** The internal decision-maker that evaluates runtime variables to dynamically choose an execution path.
* **Output Parameters (`OUT`):** Exit parameters that allow a function to return multiple columns directly to a `SELECT` statement without defining a custom database type.
* **Anchored Data Types (`%TYPE`):** Automatically inherits the exact data type of a table column, preventing mismatch errors if the schema updates.

---

### Function Definition:

Create a user analysis function named `classify_user_loyalty` from scratch that aggregates a specific user's total completed order count into an internal variable, exposes that count as an output column, analyzes it via conditional branches to check for loyalty standing, and outputs their name, total order count, and calculated status tier.

### Input/Output Parameters:

* **Input Parameter:** `p_user_id` anchored dynamically to `users.user_id%TYPE`.
* **Output Parameters:** Three explicit write-back destination placeholders:
* `p_name` anchored to `users.name%TYPE`
* `p_order_count` of explicit type `INTEGER`
* `p_loyalty_tier` of explicit type `VARCHAR(50)`



### Function Body:

* **Query:** Select `name` from `users` and calculate the total order volume using `COUNT(order_id)` from the partitioned `orders` table.
* **Data Capture:** Route the user's name directly into the `p_name` output parameter, while capturing the computed aggregate order count into a localized variable named `v_order_count`.
* **State Exposure:** Assign the value of the internal variable `v_order_count` to the output parameter `p_order_count`.
* **Filter & Grouping:** Join the tables using `USING (user_id)` and filter using the exact condition `WHERE user_id = p_user_id`, grouping the record execution by `user_id, name`.
* **Conditional Mapping:** Evaluate `v_order_count`. If it is strictly greater than 5, assign `'Loyal Customer'` to `p_loyalty_tier`. Otherwise, assign `'Standard Customer'`.

---

### Verify:

Functions cannot be invoked with the `CALL` statement; instead, they are requested directly within standard data retrieval queries.

```sql
SELECT * FROM classify_user_loyalty('U000001');

```

```sql
SELECT * FROM classify_user_loyalty('U000006');

```

---

## Task 3: Transactional Multi-Table Orchestration within Procedures (INSERT, COMMIT)

### Minimal Procedure Syntax Template:

```sql
CREATE OR REPLACE PROCEDURE procedure_name(
    p_param_1 table_name_A.column_1%TYPE,
    p_param_2 table_name_A.column_2%TYPE,
    p_param_3 table_name_B.column_3%TYPE,
    p_param_4 data_type
)   
LANGUAGE plpgsql
AS $$
BEGIN
    -- Step 1: Insert into the primary parent table
    INSERT INTO table_name_A (column_1, column_2)
    VALUES (p_param_1, p_param_2);

    -- Step 2: Insert into the dependent child table
    INSERT INTO table_name_B (parent_id, column_3, extra_column)
    VALUES (p_param_1, p_param_3, p_param_4);

    -- Step 3: Permanently seal the transactional modifications
    COMMIT;
END;
$$;

```

### Concept Breakdown:

* **Transaction Control (`COMMIT`):** A command used inside procedures to save all pending changes permanently to the database disk, ensuring both parent and child writes succeed as an atomic unit.

---

### Procedure Definition:

Create an order placement procedure named `place_single_item_order` from scratch. This procedure accepts all necessary attributes to form a valid customer order record, writes a single header row into the primary `orders` tracking structure, instantly attaches its specific itemized detail row into the dependent `order_items` fact table, and permanently commits the unified unit of work to the database.

### Input/Output Parameters:

* **Input Parameters:** Eight explicit write placeholders required to satisfy the constraints of both destination relations:
* `p_order_id` anchored dynamically to `orders.order_id%TYPE`
* `p_user_id` anchored dynamically to `orders.user_id%TYPE`
* `p_order_date` anchored dynamically to `orders.order_date%TYPE`
* `p_order_status` anchored dynamically to `orders.order_status%TYPE`
* `p_order_item_id` anchored dynamically to `order_items.order_item_id%TYPE`
* `p_product_id` anchored dynamically to `order_items.product_id%TYPE`
* `p_quantity` anchored dynamically to `order_items.quantity%TYPE`
* `p_item_price` anchored dynamically to `order_items.item_price%TYPE`



### Procedure Body:

* **Primary Record Ingestion:** Insert the incoming order metadata attributes (`p_order_id`, `p_user_id`, `p_order_date`, `p_order_status`) directly into the target columns of the parent `orders` master table.
* **Dependent Line Ingestion:** Insert the accompanying detail attributes (`p_order_item_id`, `p_order_id`, `p_order_date`, `p_product_id`, `p_quantity`, `p_item_price`) into the corresponding columns of the `order_items` fact table.
* **State Persistence Execution:** Conclude the operations by executing an explicit `COMMIT;` statement to save the synchronized multi-table records to disk.

### Verify:

```sql
-- Ensure mock dimension rows for users ('U001') and products ('P001') exist first
CALL place_single_item_order(
    'O-2025-8888', 'U000001', '2025-04-12 10:15:00', 'processing',
    'OI-2025-9999', 'P000001', 3, 45.50
);

```

```sql
-- Query to verify both listings have propagated within their tables successfully
SELECT * FROM orders WHERE order_id = 'O-2025-8888';
SELECT * FROM order_items WHERE order_id = 'O-2025-8888';

```


---

## Task 4: Mastering Database Triggers (BEFORE and AFTER Variations)

### Unified Concept Breakdown

#### 1. Timing: BEFORE vs. AFTER

* **`BEFORE`:** Fires *before* changes are written to disk. Use this timing to intercept invalid changes and block them, or to mutate incoming values on the fly before they affect your data storage.
* **`AFTER`:** Fires *after* data changes are successfully written and verified on disk. Since the operation is guaranteed to be saved, this is the ideal timing for logging audit trails, updating tracking history, or calculating metrics across other tables.

#### 2. Special Variables: NEW and OLD

* **`NEW`:** A record variable containing the row being inserted, or the proposed new data state during an `UPDATE`.
* **`OLD`:** A record variable containing the historical data exactly as it looked *before* the modification occurred (this variable is always `NULL` during an `INSERT`).

#### 3. Scope: ROW vs. STATEMENT

* **`FOR EACH ROW`:** Fires separately for **every individual row** modified by a query. This scope is mandatory whenever you need to read or alter specific field values using the `NEW` and `OLD` records.
* **`FOR EACH STATEMENT` (Default):** Fires exactly **once per SQL query**, regardless of whether it alters millions of rows or zero rows. It treats the operation as a single batch and cannot access individual row-level buffers.

#### 4. The Two-Part Structure

Every trigger requires two distinct database components to function:

1. **The Trigger Function:** A block of code that returns the special `TRIGGER` type and contains your internal conditional logic.
2. **The Trigger Binding:** The explicit `CREATE TRIGGER` statement that links your trigger function to a target physical table and dictates exactly when it should listen.

---

### 4.1 BEFORE Trigger: Automating Business Rules

#### Step 1: Run the Setup Code

Execute this script to implement business rule enforcement on the `order_items` table. It looks up the parent order's status and completely blocks any item updates or insertions if that order has already been finalized.

```sql
-- 1. The Trigger Function
CREATE OR REPLACE FUNCTION check_order_modification_eligibility()
RETURNS TRIGGER 
LANGUAGE plpgsql
AS $$
DECLARE
    v_current_status order_status_enum;
BEGIN
    -- Look up the current status of the parent order using the incoming NEW data
    SELECT order_status INTO v_current_status
    FROM orders
    WHERE order_id = NEW.order_id 
      AND order_date = NEW.order_date;

    -- If the order is already finalized, block any insert or update
    IF v_current_status IN ('completed', 'shipped') THEN
        RAISE EXCEPTION 'Cannot modify items. The parent order status is already: %', v_current_status;
    END IF;

    -- Return NEW to allow the insert or update operation to proceed
    RETURN NEW;
END;
$$;

-- 2. The Trigger Binding (Listening to INSERT OR UPDATE at the ROW level)
CREATE OR REPLACE TRIGGER trg_prevent_isolated_order_items
BEFORE INSERT OR UPDATE ON order_items
FOR EACH ROW
EXECUTE FUNCTION check_order_modification_eligibility();

```

#### Step 2: Verify

Write and execute your own test cases to verify the `BEFORE` trigger logic:

* **Write a successful query:** Insert or update a line item connected to an open order (e.g., an order currently in `'processing'` status) to confirm the data saves without issues.
* **Write a query that triggers the exception:** Attempt to insert or update a line item on a finalized order (e.g., `'completed'` or `'shipped'`) and verify that the database actively blocks the operation and raises your custom error message.

---

### 4.2 AFTER Trigger: Auditing and History Tracking

#### Step 1: Run the Setup Code

Execute this script to establish an automated historical logging pipeline. This creates an audit log table and hooks a row-level trigger to the `orders` table that captures old and new states whenever an order moves through lifecycle phases.

```sql
-- 1. Create the target table to house the audit logs
CREATE TABLE order_status_logs (
    log_id        SERIAL PRIMARY KEY, --  Auto-incrementing sequential integer
    order_id      VARCHAR(50) NOT NULL,
    old_status    order_status_enum,
    new_status    order_status_enum,
    changed_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. The Trigger Function
CREATE OR REPLACE FUNCTION audit_order_status_transitions()
RETURNS TRIGGER 
LANGUAGE plpgsql
AS $$
BEGIN
    -- Insert the historical state difference directly into the log table
    INSERT INTO order_status_logs (order_id, old_status, new_status)
    VALUES (NEW.order_id, OLD.order_status, NEW.order_status);

    -- In AFTER triggers, the return value is ignored, but returning NEW is standard practice
    RETURN NEW;
END;
$$;

-- 3. The Trigger Binding (Fires AFTER an UPDATE)
CREATE OR REPLACE TRIGGER trg_log_order_status_updates
AFTER UPDATE ON orders
FOR EACH ROW
WHEN (NEW.order_status IS DISTINCT FROM OLD.order_status) -- Trigger executes only when status changes
EXECUTE FUNCTION audit_order_status_transitions();

```

#### Step 2: Verify

Write and execute your own verification scripts to confirm the logging framework functions perfectly:

* **Write the modification query:** Write an `UPDATE` statement that changes the status of an existing order (e.g., moving it from `'processing'` to `'shipped'`).
* **Write the verification query:** Write a `SELECT` query targeting the `order_status_logs` table to confirm that the trigger successfully intercepted the modification, captured both the `OLD` and `NEW` states, and generated a real-time historical audit row.