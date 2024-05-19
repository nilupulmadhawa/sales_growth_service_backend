from fastapi import APIRouter, HTTPException
import aiomysql
from typing import List
import pytz
from models import UserDemographic, UserUpdate

# Assuming DB_CONFIG and get_db_connection() are defined in your database module
from .database import get_db_connection

router = APIRouter()

async def fetch_user_demographic(user_id: str):
    query = """
        SELECT user_id, age, gender, location
        FROM users
        WHERE user_id = %s
    """
    async with get_db_connection() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(query, (user_id,))
            user_row = await cur.fetchone()
            if user_row:
                # Ensure that we are returning data with fields set to None if they are missing
                return UserDemographic(**user_row)
            else:
                # Return a UserDemographic instance with all fields set to None
                return UserDemographic()

@router.get("/demographics/{user_id}/", response_model=UserDemographic)
async def get_user_demographics(user_id: str):
    user_data = await fetch_user_demographic(user_id)
    return user_data

async def insert_brands(user_id: str, brands: list):
    query = "INSERT INTO brands (user_id, brand) VALUES (%s, %s)"
    async with get_db_connection() as conn:
        async with conn.cursor() as cur:
            for brand in brands:
                await cur.execute(query, (user_id, brand))
            await conn.commit()
            return True

@router.put("/demographics/update/{user_id}/")
async def update_user_demographics(user_id: str, user_update: UserUpdate):
    async with get_db_connection() as conn:
        async with conn.cursor() as cur:
            # Check if the user already exists
            await cur.execute("SELECT COUNT(*) FROM users WHERE user_id = %s", (user_id,))
            (count,) = await cur.fetchone()
            if count == 0:
                # Insert new user
                a=await cur.execute("INSERT INTO users (user_id, age, gender, location) VALUES (%s, %s, %s, %s)",
                                  (user_id, user_update.age, user_update.gender, user_update.location))
            else:
                # Update existing user
                await cur.execute("UPDATE users SET age = %s, gender = %s, location = %s WHERE user_id = %s",
                                  (user_update.age, user_update.gender, user_update.location, user_id))

            await insert_brands(user_id, user_update.brands)
            a=await conn.commit()
        print(a)
    return {"message": "User and brands updated successfully"}
