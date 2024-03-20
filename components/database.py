import aiomysql
from fastapi import FastAPI, HTTPException

# Database connection details
DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': 'S@ndu=1996',
    'db': 'quixellai_db'
}

app = FastAPI()

async def get_db_connection():
    # Establish a new database connection
    conn = await aiomysql.connect(**DB_CONFIG)
    return conn