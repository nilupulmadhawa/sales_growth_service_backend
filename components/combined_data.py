from fastapi import APIRouter, Depends
from typing import List
import aiomysql
from datetime import datetime

from models import UserProductPreference, Product
from .database import get_db_connection

router = APIRouter()

@router.post("/user-preference/")
async def save_user_product_preference(preference: UserProductPreference):
    query = """
        INSERT INTO user_preferences (user_id, product_id, category, product_name, created_at)
        VALUES (%s, %s, %s, %s, %s)
    """
    created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    async with get_db_connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(query, (preference.user_id, preference.product_id, preference.category, preference.product_name, created_at))
            await conn.commit()
    return {"message": "User preference saved successfully"}


@router.get("/categories/")
async def fetch_random_category():
    query = """
        SELECT DISTINCT product_category
        FROM products
        ORDER BY RAND()
        LIMIT 1
    """
    async with get_db_connection() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(query)
            category = await cur.fetchone()
            return category['product_category']

@router.get("/products/{category}/", response_model=List[Product])
async def fetch_random_products_by_category(category: str):
    query = """
        SELECT id, product_name, product_category, product_Brand
        FROM products
        WHERE product_category = %s
        ORDER BY RAND()
        LIMIT 3
    """
    async with get_db_connection() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(query, (category,))
            products = await cur.fetchall()
            return [Product(**product) for product in products]
