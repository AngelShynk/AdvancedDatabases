import io
import zipfile
import requests
import psycopg2

# =================================================================
# CONFIGURATION AREA
# Fill in your Kaggle API credentials and Database details below.
# =================================================================
KAGGLE_USERNAME = "YOUR_KAGGLE_USERNAME"
KAGGLE_KEY = "YOUR_KAGGLE_KEY"

DB_HOST = "localhost"
DB_NAME = "YOUR_DB"
DB_USER = "YOUR_DB_USER"
DB_PASS = "YOUR_DB_PASSWORD"
DB_PORT = 5432


# =================================================================
# DATABASE LOADING LOGIC
# =================================================================

TABLE_NAME = "ecom_sales"
DATASET_PATH = "anechytailenko/e-commerce-practice-03-dataset"
CSV_FILE_NAME = "analytical.csv"


def load_data():
    try:
        print(f"Connecting to Kaggle to fetch {DATASET_PATH}...")
        api_url = f"https://www.kaggle.com/api/v1/datasets/download/{DATASET_PATH}"

        response = requests.get(
            api_url, auth=(KAGGLE_USERNAME, KAGGLE_KEY), stream=True
        )

        if response.status_code != 200:
            print(f"Error: Could not download dataset (Status {response.status_code})")
            return

        zip_buffer = io.BytesIO(response.content)
        with zipfile.ZipFile(zip_buffer) as z:
            with z.open(CSV_FILE_NAME) as csv_file:
                csv_text_stream = io.TextIOWrapper(csv_file, encoding="utf-8")

                conn = psycopg2.connect(
                    host=DB_HOST,
                    database=DB_NAME,
                    user=DB_USER,
                    password=DB_PASS,
                    port=DB_PORT,
                )
                cur = conn.cursor()

                print(f"Preparing table '{TABLE_NAME}'...")
                cur.execute(f"DROP TABLE IF EXISTS {TABLE_NAME};")
                cur.execute(f"""
                    CREATE TABLE {TABLE_NAME} (
                        order_item_id   VARCHAR(50) PRIMARY KEY,
                        order_id        VARCHAR(50) NOT NULL,
                        order_date      TIMESTAMP NOT NULL,
                        order_status    VARCHAR(50),
                        product_id      VARCHAR(50),
                        product_name    VARCHAR(255),
                        category        VARCHAR(100),
                        brand           VARCHAR(100),
                        customer_email  VARCHAR(255),
                        customer_gender VARCHAR(50), 
                        quantity        INTEGER,
                        item_price      DECIMAL(12, 2)
                    );
                """)

                print(f"Streaming data into {TABLE_NAME}...")
                copy_sql = f"""
                    COPY {TABLE_NAME} (
                        order_item_id, order_id, order_date, order_status, 
                        product_id, product_name, category, brand, 
                        customer_email, customer_gender, quantity, item_price
                    ) 
                    FROM STDIN WITH CSV HEADER
                """
                cur.copy_expert(sql=copy_sql, file=csv_text_stream)

                conn.commit()
                print(f"Success! Data loaded into '{TABLE_NAME}'.")

                cur.close()
                conn.close()

    except Exception as e:
        print(f"CRITICAL ERROR: {e}")


if __name__ == "__main__":
    load_data()
