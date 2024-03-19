import pandas as pd
import mysql.connector
from mysql.connector import Error

# Function to convert datetime string to a MySQL-compatible format
def convert_datetime(dt_str):
    if pd.isnull(dt_str):
        return None
    # Handle the microseconds and 'UTC', if present
    if '.' in dt_str:
        dt_str = dt_str.split('.')[0]  # Remove microseconds
    if 'UTC' in dt_str:
        dt_str = dt_str.replace(' UTC', '')  # Remove 'UTC'
    return dt_str

# Load the CSV data into a DataFrame
csv_file_path = 'sales_forecasting\Sales_Data.csv'
df = pd.read_csv(csv_file_path)

# Convert 'order_date' and 'shipped_at' columns
df['order_date'] = df['order_date'].apply(convert_datetime)
df['shipped_at'] = df['shipped_at'].apply(convert_datetime)

# Replace NaN values with None for SQL compatibility
df = df.where(pd.notnull(df), None)

# Database connection parameters
host = 'localhost'
database = 'quixellai_db'
user = 'root'
password = '123'
port = 3306

try:
    # Establish a database connection
    connection = mysql.connector.connect(
        host=host,
        database=database,
        user=user,
        password=password,
        port=port
    )

    if connection.is_connected():
        cursor = connection.cursor()

        # Iterate over the DataFrame rows as tuples and insert into the sales table
        for row in df.itertuples(index=False):
            insert_query = """
            INSERT INTO sales (user_id, product_id, product_name, product_category, 
                               cost, selling_price, margin, quantity, amount, 
                               order_id, order_date)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            # Define how you calculate or extract the cost and margin
            cost = None  # Placeholder, replace with actual logic if available
            margin = None  # Placeholder, replace with actual logic if available
            quantity = row.num_of_item
            amount = row.sale_price * quantity if row.sale_price and row.num_of_item else None

            record = (row.user_id, row.product_id, row.product_name, row.product_category,
                      cost, row.sale_price, margin, quantity, amount,
                      row.order_id, row.order_date)

            cursor.execute(insert_query, record)

        connection.commit()
        print("Data inserted successfully")

except Error as e:
    print("Error while connecting to MySQL", e)
finally:
    if connection.is_connected():
        cursor.close()
        connection.close()
        print("MySQL connection is closed")
