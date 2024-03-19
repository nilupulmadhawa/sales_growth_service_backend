from fastapi import APIRouter, Depends
import aiomysql
from typing import List
import pytz

from models import UserProductPreference, Product

# Assuming DB_CONFIG and get_db_connection() are defined in your database module
from .database import get_db_connection

router = APIRouter()


async def fetch_combined_data(start_date: str = None, end_date: str = None):
    query = """
        SELECT 
            p.product_name, 
            p.product_category as category_code, 
            p.product_Brand as brand, 
            u.age, 
            u.gender, 
            u.location, 
            e.event_type, 
            e.event_time
        FROM events e
        JOIN users u ON e.user_id = u.user_id
        JOIN products p ON e.product_id = p.product_id
    """

    query_params = []
    if start_date and end_date:
        # Convert start_date and end_date to proper format
        start_date = start_date + "T00:00:00"
        end_date = end_date + "T23:59:59"

        # Convert start_date and end_date to the appropriate time zone
        timezone = pytz.timezone('Your_Time_Zone')  # Replace 'Your_Time_Zone' with the appropriate time zone
        start_date = timezone.localize(datetime.fromisoformat(start_date)).astimezone(pytz.UTC)
        end_date = timezone.localize(datetime.fromisoformat(end_date)).astimezone(pytz.UTC)

        # Add condition for date range filtering
        query += " WHERE e.event_time BETWEEN %s AND %s"
        query_params.extend([start_date, end_date])

    async with await get_db_connection() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(query, query_params)
            result = await cur.fetchall()
    return result

@router.get("/combined-data/", response_model=List)
async def combined_data_route():
    data = await fetch_cxoxmbined_data()
    return data

@router.post("/user-preference/")
async def save_user_product_preference(preference: UserProductPreference):
    query = "INSERT INTO user_preferences (user_id, product_id) VALUES (%s, %s)"
    async with await get_db_connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(query, (preference.user_id, preference.product_id))
            await conn.commit()
    return {"message": "User preference saved successfully"}


# get a category randomly from the database product table
@router.get("/categories/")
async def fetch_random_category():
    query = """
        SELECT DISTINCT product_category
        FROM products
        ORDER BY RAND()
        LIMIT 1
    """
    async with await get_db_connection() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(query)
            category = await cur.fetchone()
            return category['category']

@router.get("/products/{category}/", response_model=List[Product])
async def fetch_random_products_by_category(category: str):
    query = """
        SELECT id, name, category, image_url
        FROM products
        WHERE category = %s
        ORDER BY RAND()
        LIMIT 3
    """
    async with await get_db_connection() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(query, (category,))
            products = await cur.fetchall()
            return [Product(**product) for product in products]
