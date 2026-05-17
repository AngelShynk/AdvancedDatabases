import io
import zipfile
import requests
import psycopg2

# =================================================================
# CONFIGURATION AREA
# Fill in your Kaggle API credentials and Database details below.
# =================================================================
KAGGLE_USERNAME = "anechytailenko"
KAGGLE_KEY = "KGAT_9404d7d61a5941f5644147e33f3b28a1"

DB_HOST = "localhost"
DB_NAME = "postgres"
DB_USER = "postgres"
DB_PASS = "postgres"
DB_PORT = 5432

# =================================================================
# DATABASE LOADING LOGIC
# =================================================================
DATASET_PATH = "anechytailenko/e-commerce-practice-04-dataset"

INGESTION_ORDER = [
    {"table": "users", "file": "users.csv", "columns": "user_id, name, email"},
    {
        "table": "products",
        "file": "products.csv",
        "columns": "product_id, product_name, category, brand, price, rating",
    },
    {
        "table": "orders",
        "file": "orders.csv",
        "columns": "order_id, user_id, order_date, order_status",
    },
    {
        "table": "order_items",
        "file": "order_items.csv",
        "columns": "order_item_id, order_id, order_date, product_id, quantity, item_price",
    },
]


def load_data():
    print(f"Connecting to Kaggle to fetch {DATASET_PATH}...")
    api_url = f"https://www.kaggle.com/api/v1/datasets/download/{DATASET_PATH}"

    try:
        response = requests.get(api_url, auth=(KAGGLE_USERNAME, KAGGLE_KEY))

        if response.status_code != 200:
            print(f"Error: Could not download dataset (Status {response.status_code})")
            return

        zip_buffer = io.BytesIO(response.content)

        with zipfile.ZipFile(zip_buffer) as z, psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASS,
            port=DB_PORT,
        ) as conn:

            with conn.cursor() as cur:
                for step in INGESTION_ORDER:
                    table_name = step["table"]
                    file_name = step["file"]
                    columns = step["columns"]

                    print(
                        f"Streaming data from {file_name} into table '{table_name}'..."
                    )

                    with z.open(file_name) as csv_file:
                        csv_text_stream = io.TextIOWrapper(
                            csv_file, encoding="utf-8", newline=""
                        )

                        copy_sql = (
                            f"COPY {table_name} ({columns}) FROM STDIN WITH CSV HEADER"
                        )
                        cur.copy_expert(sql=copy_sql, file=csv_text_stream)

            conn.commit()
            print(
                "Success! All tables populated sequentially with zero constraint conflicts."
            )

    except psycopg2.Error as db_err:
        print(f"DATABASE ERROR: {db_err}")
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")


if __name__ == "__main__":
    load_data()
