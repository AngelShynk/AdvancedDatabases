import io
import os
import pandas as pd
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import kagglehub
from kagglehub import KaggleDatasetAdapter

# =====================================================================
#  STUDENT CONFIGURATION AREA
# Only edit the variables inside this box.
# =====================================================================

# 1. Your Kaggle API Credentials (found in your kaggle.json file)
KAGGLE_USERNAME = "YOUR_KAGGLE_USERNAME"
KAGGLE_KEY = "YOUT_KAGGLE_KEY"

# 2. Your Local PostgreSQL Connection Settings
DB_HOST = "localhost"
DB_USER = "YOUR_DB_USER"
DB_PASS = "YOUR_DB_PASS"
DB_PORT = 5432

# =====================================================================
# DO NOT EDIT ANYTHING BELOW THIS LINE
# The automated database creation and ingestion logic begins here.
# =====================================================================

# Target Database Name
TARGET_DB = "cinema"
DATASET_HANDLE = "anechytailenko/cinema-dataset-practice-06-07"

# Set credentials into the environment dynamically before kagglehub runs
os.environ["KAGGLE_USERNAME"] = KAGGLE_USERNAME
os.environ["KAGGLE_KEY"] = KAGGLE_KEY

# DDL Schema Execution Map
TABLE_SCHEMAS = {
    "movie": """
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
    """,
    "guests": """
        CREATE TABLE guests (
            guest_id INT PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            phone_number VARCHAR(30) UNIQUE NOT NULL,
            loyalty_points INT NOT NULL CHECK (loyalty_points >= 0)
        );
    """,
    "sessions": """
        CREATE TABLE sessions (
            session_id INT PRIMARY KEY,
            movie_id INT NOT NULL REFERENCES movie(movie_id) ON DELETE CASCADE,
            screen_time TIMESTAMP NOT NULL,
            hall_name VARCHAR(100) NOT NULL,
            available_seats INT NOT NULL CHECK (available_seats >= 0)
        );
    """,
    "tickets": """
        CREATE TABLE tickets (
            ticket_id INT PRIMARY KEY,
            session_id INT NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
            guest_id INT NOT NULL REFERENCES guests(guest_id) ON DELETE CASCADE,
            seat_number VARCHAR(10) NOT NULL,
            ticket_price DECIMAL(10, 2) NOT NULL CHECK (ticket_price >= 0)
        );
    """,
}

# Ordered explicitly to honor Referential Integrity Constraints
INGESTION_ORDER = [
    {
        "table": "movie",
        "file": "movie.csv",
        "columns": "movie_id, poster_link, series_title, released_year, runtime_in_min, genre, overview, revenue, credits",
    },
    {
        "table": "guests",
        "file": "guests.csv",
        "columns": "guest_id, name, phone_number, loyalty_points",
    },
    {
        "table": "sessions",
        "file": "sessions.csv",
        "columns": "session_id, movie_id, screen_time, hall_name, available_seats",
    },
    {
        "table": "tickets",
        "file": "tickets.csv",
        "columns": "ticket_id, session_id, guest_id, seat_number, ticket_price",
    },
]


def initialize_database():
    """Connects to default postgres database to recreate target database cleanly."""
    print("Connecting to Postgres to manage database infrastructure...")
    conn = psycopg2.connect(
        host=DB_HOST, user=DB_USER, password=DB_PASS, port=DB_PORT, database="postgres"
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)

    with conn.cursor() as cur:
        print(f"Dropping existing database '{TARGET_DB}' if present...")
        cur.execute(f"DROP DATABASE IF EXISTS {TARGET_DB};")

        print(f"Creating fresh '{TARGET_DB}' database instances...")
        cur.execute(f"CREATE DATABASE {TARGET_DB};")

    conn.close()
    print("Base infrastructure successfully configured.")


def build_schema_and_load_data():
    """Connects to the newly created database, builds structures, and streams dataset values."""
    initialize_database()

    try:
        print(f"\nConnecting to the new '{TARGET_DB}' schema deployment context...")
        with psycopg2.connect(
            host=DB_HOST,
            database=TARGET_DB,
            user=DB_USER,
            password=DB_PASS,
            port=DB_PORT,
        ) as conn:
            with conn.cursor() as cur:

                # Step 1: Generate Table DDL Shells
                for table_name, ddl_query in TABLE_SCHEMAS.items():
                    print(
                        f"Building relational architecture for table: '{table_name}'..."
                    )
                    cur.execute(ddl_query)
                print("All relational tables built safely.")

                # Step 2: Extract Kaggle cache data and load values sequentially via COPY stream
                for step in INGESTION_ORDER:
                    table_name = step["table"]
                    file_name = step["file"]
                    columns = step["columns"]

                    print(f"\nFetching source '{file_name}' via kagglehub...")
                    df = kagglehub.load_dataset(
                        KaggleDatasetAdapter.PANDAS, DATASET_HANDLE, file_name
                    )

                    print(
                        f"Streaming {len(df)} rows into table '{table_name}' via bulk copy stream..."
                    )

                    csv_buffer = io.StringIO()
                    df.to_csv(csv_buffer, index=False, header=False)
                    csv_buffer.seek(0)

                    copy_sql = f"COPY {table_name} ({columns}) FROM STDIN WITH CSV"
                    cur.copy_expert(sql=copy_sql, file=csv_buffer)
                    print(f"Table '{table_name}' data successfully loaded.")

            conn.commit()
            print("\nSuccess! The 'cinema' database is completely ready for your lab!")

    except psycopg2.Error as db_err:
        print(f"\nDATABASE TRANSACTION CRASH: {db_err}")
    except Exception as e:
        print(f"\nCRITICAL CRASH: {e}")


if __name__ == "__main__":
    build_schema_and_load_data()
