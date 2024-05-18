import aiomysql
from contextlib import asynccontextmanager
from dotenv import load_dotenv
load_dotenv()
import os

# Database connection details
DB_CONFIG = {
    'host': os.getenv("DB_HOST"),
    'port': int(os.getenv("DB_PORT")),  # Convert port to integer
    'user': os.getenv("DB_USERNAME"),
    'password': os.getenv("DB_PASSWORD"),
    'db': os.getenv("DB_NAME"),
}


@asynccontextmanager
async def get_db_connection():
    conn = await aiomysql.connect(**DB_CONFIG)
    try:
        yield conn
    finally:
        conn.close()
