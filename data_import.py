# from fastapi import FastAPI, HTTPException
# import aiomysql
# import pandas as pd

# # Database connection details
# DB_CONFIG = {
#     'host': 'localhost',
#     'port': 3306,
#     'user': 'root',
#     'password': 'S@ndu=1996',
#     'db': 'quixellai_db',
# }

# app = FastAPI()

# async def get_db_connection():
#     # Establish a new database connection
#     conn = await aiomysql.connect(**DB_CONFIG)
#     return conn

# @app.post("/import-csv/")
# async def import_csv():
#     # Path to your CSV file
#     csv_file_path = 'recommendation-model/multi-category-dataset-recommendation.csv'
#     # Read the CSV file into a pandas DataFrame
#     data = pd.read_csv(csv_file_path)
    
#     async with await get_db_connection() as conn:
#         async with conn.cursor() as cursor:
#             insert_query = "INSERT INTO products (column1, column2, column3) VALUES (%s, %s, %s)"
#             try:
#                 # Iterate over the DataFrame rows
#                 for index, row in data.iterrows():
#                     # Execute the insert query for each row
#                     # Adjust these row accesses based on your CSV structure and table schema
#                     await cursor.execute(insert_query, (row['column1'], row['column2'], row['column3']))
#                 # Commit the transaction
#                 await conn.commit()
#             except Exception as e:
#                 await conn.rollback()  # Rollback the transaction in case of error
#                 raise HTTPException(status_code=400, detail=f"Error inserting data: {e}")

#     return {"message": "CSV data imported successfully"}
