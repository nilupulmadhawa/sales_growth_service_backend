import aiomysql
from fastapi import FastAPI, HTTPException

# Database connection details
DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'db': 'quixellai_db',
    'password': '123456789'
}

app = FastAPI()

async def get_db_connection():
    # Establish a new database connection
    conn = await aiomysql.connect(**DB_CONFIG)
    return conn