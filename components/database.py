import aiomysql
from contextlib import asynccontextmanager

# Database connection details
DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': 'S@ndu=1996',
    'db': 'quixellai_db',
}

@asynccontextmanager
async def get_db_connection():
    conn = await aiomysql.connect(**DB_CONFIG)
    try:
        yield conn
    finally:
        conn.close()
