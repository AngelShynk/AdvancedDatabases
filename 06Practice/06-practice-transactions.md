# Practice 06: Transactions, ACID Properties & Concurrency Control

## Objective

Design and execute robust database transactions to maintain strict ACID properties. You will gain hands-on experience controlling partial rollbacks using savepoints, testing transaction isolation levels, analyzing real-time concurrency bottlenecks and deadlocks across parallel sessions, and building advanced exception-handling pipelines inside PL/pgSQL anonymous blocks.

---

## Deliverables

Submit:

* **SQL queries** for all tasks.
* **Screenshots with query and output**.

---

## Core Terminology

* **ACID Properties:** The four theoretical pillars of reliable database transactions:
  * **Atomicity:** All-or-nothing execution.
  * **Consistency:** Database rules and constraints are always enforced.
  * **Isolation:** Parallel transactions do not interfere with each other.
  * **Durability:** Committed changes are saved permanently, even during power loss.


* **Isolation Levels & Concurrency Anomalies:** Database settings that balance data accuracy with system performance. PostgreSQL implements a highly robust version of MVCC that goes beyond the ANSI SQL standard.

| Isolation Level | Dirty Read | Non-Repeatable Read | Phantom Read | Serialization Anomaly |
| --- | --- | --- | --- | --- |
| **Read Uncommitted** | Not Possible | Possible | Possible | Possible |
| **Read Committed** | Not Possible | Possible | Possible | Possible |
| **Repeatable Read** | Not Possible | Not Possible | Not Possible | Possible |
| **Serializable** | Not Possible | Not Possible | Not Possible | Not Possible |


---

## Data Ingestion

#### Way 1: Automated Script (Recommended)

Initialize a virtual environment, install dependencies, and run the provided `load_cinema_data.py` script. This script will automatically create the `cinema` database, build all required tables, and stream the data from Kaggle directly into your database.

**Windows:**

```bash
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
python load_cinema_data.py

```

**Linux/Mac:**

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 load_cinema_data.py

```


#### Way 2: Manual Setup & CSV Ingestion

If you prefer to manage the database infrastructure manually, follow these steps:

1. **Create the Database and Tables:** Connect to your PostgreSQL instance and execute the following SQL block in your query editor:

```sql
-- 1. Create the database
CREATE DATABASE cinema;

-- 2. Create the movie table
CREATE TABLE movie (
    movie_id INT PRIMARY KEY,
    poster_link TEXT,
    series_title VARCHAR(255) NOT NULL,
    released_year INT,
    runtime_in_min INT,
    genre VARCHAR(150),
    overview TEXT,
    revenue NUMERIC(15, 2),
    credits JSONB
);

-- 3. Create the guests table
CREATE TABLE guests (
    guest_id INT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    phone_number VARCHAR(30) UNIQUE NOT NULL,
    loyalty_points INT NOT NULL CHECK (loyalty_points >= 0)
);

-- 4. Create the sessions table (references movie)
CREATE TABLE sessions (
    session_id INT PRIMARY KEY,
    movie_id INT NOT NULL REFERENCES movie(movie_id) ON DELETE CASCADE,
    screen_time TIMESTAMP NOT NULL,
    hall_name VARCHAR(100) NOT NULL,
    available_seats INT NOT NULL CHECK (available_seats >= 0)
);

-- 5. Create the tickets table (references sessions and guests)
CREATE TABLE tickets (
    ticket_id INT PRIMARY KEY,
    session_id INT NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    guest_id INT NOT NULL REFERENCES guests(guest_id) ON DELETE CASCADE,
    seat_number VARCHAR(10) NOT NULL,
    ticket_price DECIMAL(10, 2) NOT NULL CHECK (ticket_price >= 0)
);

```

2. **Import Data:** Download the source files from the Kaggle dataset. Use  DataGrip to import the data. Right-click your target table -> **Import Data from File...** -> select the matching downloaded CSV file. Repeat this process for `movie`, `guests`, `sessions`, and `tickets` **exactly in that order** to maintain referential integrity.



---

## Task 1: Transaction Control & Savepoint Memory Management

### Minimal Syntax Template:

```sql
BEGIN;

-- Step 1: Establish a safety net before a risky operation
SAVEPOINT attempt_first_action;

-- Step 2: Execute the first risky operation (Assume it succeeds)
-- [Execute valid SQL data manipulation statements here]

-- Step 3: Operation was successful. We no longer need the fallback. Free the memory.
RELEASE SAVEPOINT attempt_first_action;

-- Step 4: Establish a new safety net for the next risky operation
SAVEPOINT attempt_second_action;

-- Step 5: Execute the second risky operation (Assume it FAILS)
-- [Execute invalid SQL data manipulation statements here]

-- Step 6: Recover the transaction from the aborted state
ROLLBACK TO SAVEPOINT attempt_second_action;

-- Step 7: Permanently seal the successful modifications to disk
COMMIT;

```

### Concept Breakdown:

* **Transaction Boundaries (`BEGIN` / `COMMIT`):** `BEGIN` starts a transaction, holding database modifications in memory. `COMMIT` permanently writes these pending changes to disk.
* **`SAVEPOINT`:** A marker within an active transaction that records the current state of the database, requiring memory allocation to track.
* **`RELEASE SAVEPOINT`:** Destroys a specific savepoint, freeing system memory. In complex transactions, releasing savepoints after successful operations is essential to prevent memory exhaustion.
* **`ROLLBACK TO SAVEPOINT`:** Reverts the database to a specific savepoint, discarding subsequent errors and modifications while keeping the main transaction active for future commits.

---

### Transaction Definition:

Write a single SQL transaction that demonstrates savepoint lifecycle management—specifically memory cleanup and error recovery—across multiple operations.

You will execute two sequential actions for **Guest 1**, establishing a savepoint before each attempt. The first action (a ticket purchase) will succeed, so you must release its savepoint to free system memory. The second action (a ticket refund) will intentionally violate the zero-point `CHECK` constraint, throwing the transaction into an aborted state. You must then use your second savepoint to roll back the error, rescuing the transaction so the first successful purchase can be permanently committed.

### Execution Body:

Construct your transaction block by writing the SQL for the following steps in exact order:

1. **Initiate State:** Open the transaction block.
2. **First Safety Net:** Create a savepoint named `attempt_purchase`.
3. **Action 1: Purchase (Valid):**

* **Update `sessions`:** Subtract 1 from `available_seats` where `session_id = 50`.
* **Update `guests`:** **Add** `150` to `loyalty_points` where `guest_id = 1`.
* **Insert `tickets`:** Execute the following exact command:
`INSERT INTO tickets (ticket_id, session_id, guest_id, seat_number, ticket_price) VALUES (9001, 50, 1, 'A1', 15.00);`

4. **Memory Cleanup:** Execute the command to release the `attempt_purchase` savepoint.
5. **Second Safety Net:** Create a new savepoint named `attempt_refund`.
6. **Action 2: Refund (Invalid):**

* **Update `sessions`:** Add 1 back to `available_seats` where `session_id = 100`.
* **Delete `tickets`:** Delete the ticket where `ticket_id = 1500`.
* **Update `guests`:** **Subtract** `5000` from `loyalty_points` where `guest_id = 1`. *(This throws the entire transaction into an aborted state due to the constraint).*

7. **Error Recovery:** Execute the command to roll back your transaction strictly to the `attempt_refund` marker.
8. **Persistence:** Execute the final commit.

### Verify:

Run the validation queries below. You should see the newly purchased ticket, and Guest 1's points should have increased by 150 (ignoring the failed 5000 point deduction).

```sql
-- Verify the purchased ticket successfully saved
SELECT * FROM tickets WHERE guest_id = 1 AND session_id = 50;

-- Verify the guest earned points for the purchase, but did not lose the 5000 points
SELECT name, loyalty_points FROM guests WHERE guest_id = 1;

```

---

## Task 2: Isolation Levels and Concurrency Anomalies

### Concept Breakdown

Database isolation levels balance data accuracy with system performance by preventing specific concurrency anomalies.

* **`READ COMMITTED` (Default):** Queries see only data committed before they began.
* **`REPEATABLE READ`:** Takes a strict snapshot of the database at the start of the transaction, ignoring concurrent changes.
* **`SERIALIZABLE`:** The strictest level. Simulates running transactions sequentially and aborts if it detects logical inconsistencies.

---

### Subtask 2.a: The Changing Snapshot

**Objective:** Observe how the default isolation level handles concurrent updates versus a strict snapshot.

1. **Terminal A (`READ COMMITTED`):** Start a default transaction and read a value.

```sql
BEGIN; 
SELECT loyalty_points FROM guests WHERE guest_id = 5;

```

2. **Terminal B (Auto-commit):** Update that exact value concurrently.

```sql
UPDATE guests SET loyalty_points = 9999 WHERE guest_id = 5;

```

3. **Terminal A:** Read the value again, then close the transaction.

```sql
SELECT loyalty_points FROM guests WHERE guest_id = 5;
COMMIT;

```

*(Notice the value changed mid-transaction).*
4. **Repeat Steps 1-3** for `guest_id = 6`, but this time start Terminal A with:

```sql
BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ;

```

*(Notice the value does NOT change mid-transaction).*

---

### Subtask 2.b: The Parallel Insert Violation

**Objective:** Observe how `REPEATABLE READ` can still fail business rules, and how `SERIALIZABLE` enforces them.

*Business Rule:* A guest can hold a maximum of 1 ticket per session.

1. **Terminal A & B (`REPEATABLE READ`):** Start both terminals with:

```sql
BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ;

```

2. **Terminal A & B:** In both terminals, check if Guest 10 has tickets for Session 120.

```sql
SELECT COUNT(*) FROM tickets WHERE guest_id = 10 AND session_id = 120;

```

3. **Terminal A & B:** Both see "0", so both proceed to insert a ticket.

```sql
-- Terminal A
INSERT INTO tickets (ticket_id, session_id, guest_id, seat_number, ticket_price) VALUES (8001, 120, 10, 'F1', 10.00);

-- Terminal B
INSERT INTO tickets (ticket_id, session_id, guest_id, seat_number, ticket_price) VALUES (8002, 120, 10, 'F2', 10.00);

```

4. **Terminal A & B:** Execute `COMMIT;` in both. *(Both succeed. The rule is broken).*
5. **Repeat Steps 1-4** for `guest_id = 11`, but this time start both terminals with:

```sql
BEGIN TRANSACTION ISOLATION LEVEL SERIALIZABLE;

```

*(Notice one terminal successfully commits, while the other crashes with a serialization error).*

---

### Step 3: Analysis & Elaboration Requirement

**Deliverable:** Submit a short analysis answering the following:

1. **Subtask 2.a:** Name the specific concurrency anomaly observed in the first test. How exactly did `REPEATABLE READ` prevent it during the second test?
2. **Subtask 2.b:** Name the specific concurrency anomaly observed when the business rule was broken. How did `SERIALIZABLE` know to crash the second transaction even though they were inserting completely different `ticket_id` rows?

---

## Task 3: Concurrent Transactions, `pg_locks`, and Deadlocks

### Concept Breakdown

In PostgreSQL, when a transaction modifies a record (for example, by executing an `UPDATE`), the database places a **row-level lock** on that specific record. This lock accumulates in memory and is strictly held until the transaction finishes (via `COMMIT` or `ROLLBACK`).

If multiple concurrent transactions attempt to modify the same rows but in different orders, they will block each other. A **Deadlock** occurs when two or more transactions are stuck in an infinite standoff, each waiting for the other to release a lock they need to proceed.

---

### Task Definition

Your goal is to deliberately orchestrate a deadlock using two separate terminal windows (Terminal A and Terminal B). You will initiate transactions that accumulate locks in opposing orders until the system crashes. You may use standard `UPDATE` statements on the `sessions` and `guests` tables to achieve this.

#### Step 1: Establish the Blocking Conflict

Open two separate terminal windows and perform the following sequence manually. Do not commit your transactions yet!

1. **Terminal A:** Begin a transaction and `UPDATE` a specific row in the `sessions` table (e.g., session 100).
2. **Terminal B:** Begin a transaction and `UPDATE` a specific row in the `guests` table (e.g., guest 20).
3. **Terminal A:** Attempt to `UPDATE` the exact same guest account that Terminal B just locked in the previous step.
*(Notice that Terminal A freezes. It is now blocked, waiting for Terminal B to finish).*

#### Step 2: Analyze the Lock Queue

Open a **third** terminal (Terminal C) to act as the database administrator. Query the `pg_locks` view to analyze the traffic jam.

```sql
SELECT 
    pid, 
    relation::regclass AS table_name, 
    mode, 
    granted 
FROM pg_locks 
WHERE relation::regclass::text IN ('sessions', 'guests');

```

**Verification Requirement:** Take a screenshot of this output. You must clearly capture the row where `granted` is `false`, proving that one transaction is actively waiting on a lock.

#### Step 3: Trigger the Deadlock

Return to **Terminal B** and attempt to `UPDATE` the exact same session row that Terminal A originally locked in Step 1.

> **Observation:** PostgreSQL will instantly detect the infinite loop, kill one of the transactions, and throw a `deadlock detected` error. Run `ROLLBACK;` in whichever terminal survived.

---

## Task 4: Exception Handling and Stacked Diagnostics in PL/pgSQL

### Concept Breakdown

In complex database operations, a single error shouldn't always crash your entire script. PL/pgSQL provides built-in mechanisms to intercept failures, harvest error metadata, and allow the transaction to continue gracefully.

* **The Implicit Savepoint (`EXCEPTION`):** In Task 1, you manually managed errors using `SAVEPOINT` and `ROLLBACK TO`. In PL/pgSQL, any `BEGIN ... EXCEPTION ... END` sub-block **automatically creates a savepoint under the hood**.
* If the sub-block succeeds, its changes are kept.
* If the sub-block fails, PostgreSQL silently rolls back *every* change made inside that specific sub-block—even the valid ones!
* Importantly, changes made *outside* the failed block (or inside other successful sub-blocks) are preserved.
* **Anonymous Block (`DO $$`):** A temporary, one-time stored procedure that executes immediately without being permanently saved to the database.
* **Stacked Diagnostics (`GET STACKED DIAGNOSTICS`):** Catching an error prevents a crash, but as an administrator, you need to know exactly *what* went wrong and *where*. This command pulls rich telemetry directly from the database engine:
* `MESSAGE_TEXT`: Extracts the exact, human-readable error message.
* `PG_EXCEPTION_CONTEXT`: Extracts the internal stack trace, giving you the exact line number where the execution fatally crashed.

### Task Definition

You will design an anonymous block that executes a mix of valid and invalid SQL operations across different sub-blocks. You will observe how a completely valid sub-block survives, while a second sub-block containing a mix of valid and invalid commands gets partially rolled back. Instead of crashing the whole script, your exception handler will catch the error in the second block, extract the context trace using `GET STACKED DIAGNOSTICS`, and log the telemetry.

### Execution Body

#### Step 1: Create the Logging Table

First, run this standard SQL command to create the destination table for your error logs.

```sql
CREATE TABLE transaction_errors (
    error_id SERIAL PRIMARY KEY,
    msg TEXT,
    context TEXT,
    logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

```

#### Step 2: Build the Diagnostic Block

Use the minimal syntax template below to structure your script. Write an anonymous `DO $$` block that contains an outer valid command, and two inner `BEGIN...EXCEPTION...END` sub-blocks:

```sql
DO $$ 
DECLARE 
    exc_message TEXT; 
    exc_context TEXT; 
BEGIN 
    -- Outer Command
    -- [Execute a VALID operation here]

    -- Sub-block 1 (Completely Valid)
    BEGIN 
        -- [Execute a VALID operation here]
    EXCEPTION 
        WHEN OTHERS THEN 
            GET STACKED DIAGNOSTICS exc_message = MESSAGE_TEXT, exc_context = PG_EXCEPTION_CONTEXT; 
            -- [Write INSERT statement to save to your log table]
    END; 

    -- Sub-block 2 (Demonstrating Partial Rollback)
    BEGIN 
        -- [Execute a VALID operation here]
        -- [Execute an INVALID operation here to crash the block]
    EXCEPTION 
        WHEN OTHERS THEN 
            GET STACKED DIAGNOSTICS exc_message = MESSAGE_TEXT, exc_context = PG_EXCEPTION_CONTEXT; 
            -- [Write INSERT statement to save to your log table]
    END; 
END $$;

```

**Implementation Requirements:**

* **Outer Command:** Write a valid `UPDATE` that subtracts 1 from `available_seats` for `session_id = 50`.
* **In Sub-block 1 (The Survivor):**
* **Valid Action:** Write a valid `INSERT` statement into the `tickets` table (choose a unique `ticket_id`, `session_id = 50`, `guest_id = 1`, `seat_number = 'B1'`). Because this succeeds, its exception block will never trigger.
* **In Sub-block 2 (The Partial Rollback):**
* **Valid Action:** First, write a valid `UPDATE` that adds 500 `loyalty_points` to Guest 1.
* **Invalid Action:** Next, write an `UPDATE` that changes Guest 1's `loyalty_points` to `-100`. This will instantly trigger your zero-point check constraint and crash the block.
* **Handler:** Insert your captured `exc_message` and `exc_context` into the `transaction_errors` table.

#### Step 3: Verify the Audit Log & Rollback Behavior

Run the following queries to verify exactly how the database handled the script.

```sql
-- 1. Check the error logs (You should only have ONE row!)
SELECT * FROM transaction_errors;

-- 2. Verify the Outer Command survived (Seats should be reduced)
SELECT available_seats FROM sessions WHERE session_id = 50;

-- 3. Verify Sub-block 1 survived (Ticket B1 should exist)
SELECT * FROM tickets WHERE guest_id = 1 AND seat_number = 'B1';

-- 4. Verify Sub-block 2 Partial Rollback (Guest 1 should NOT have the 500 extra points)
SELECT name, loyalty_points FROM guests WHERE guest_id = 1;

```




















