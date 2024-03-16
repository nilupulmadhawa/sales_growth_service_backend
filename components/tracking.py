from fastapi import APIRouter, HTTPException, BackgroundTasks
import aiomysql
from typing import Optional

# Assuming DB_CONFIG and get_db_connection() are defined as shown earlier
from .database import DB_CONFIG, get_db_connection

router = APIRouter()

async def record_impression(user_id: int, product_id: int):
    async with await get_db_connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "INSERT INTO impressions (user_id, product_id, impression_time) VALUES (%s, %s, NOW())",
                (user_id, product_id,)
            )
            await conn.commit()

async def record_click(user_id: int, product_id: int):
    async with await get_db_connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "INSERT INTO clicks (user_id, product_id, click_time) VALUES (%s, %s, NOW())",
                (user_id, product_id,)
            )
            await conn.commit()

@router.post("/impression/{user_id}/{product_id}")
async def track_impression(background_tasks: BackgroundTasks, user_id: int, product_id: int):
    background_tasks.add_task(record_impression, user_id, product_id)
    return {"message": "Impression recorded"}

@router.post("/click/{user_id}/{product_id}")
async def track_click(background_tasks: BackgroundTasks, user_id: int, product_id: int):
    background_tasks.add_task(record_click, user_id, product_id)
    return {"message": "Click recorded"}


# Continue in tracking.py or create a new metrics.py and adjust imports accordingly

@router.get("/metrics/{metric}")
async def get_metrics(metric: str):
    if metric not in ["impressions", "clicks"]:
        raise HTTPException(status_code=404, detail="Metric not found")

    async with await get_db_connection() as conn:
        async with conn.cursor() as cur:
            if metric == "impressions":
                await cur.execute("SELECT COUNT(*) FROM impressions")
            elif metric == "clicks":
                await cur.execute("SELECT COUNT(*) FROM clicks")

            (total,) = await cur.fetchone()
    return {metric: total}


@router.post("/update-conversion-rates/")
async def update_conversion_rates():
    async with await get_db_connection() as conn:
        async with conn.cursor() as cur:
            # Calculate conversion rates
            await cur.execute("""
                SELECT 
                    DATE_FORMAT(event_time, '%Y-%m') AS month,
                    SUM(event_type IN ('view', 'cart')) AS total_trials,
                    SUM(event_type = 'purchase') AS total_conversions,
                    (SUM(event_type = 'purchase') / SUM(event_type IN ('view', 'cart'))) * 100 AS conversion_rate
                FROM 
                    events
                GROUP BY 
                    month
                ORDER BY 
                    month;
            """)
            conversion_rates = await cur.fetchall()
            
            # Insert conversion rates into conversion_rates table
            for month, total_trials, total_conversions, conversion_rate in conversion_rates:
                await cur.execute("""
                    INSERT INTO conversion_rates (month, total_trials, total_conversions, conversion_rate)
                    VALUES (%s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                    total_trials = VALUES(total_trials),
                    total_conversions = VALUES(total_conversions),
                    conversion_rate = VALUES(conversion_rate)
                """, (month, total_trials, total_conversions, conversion_rate))
                await conn.commit()
    
    return {"message": "Conversion rates updated successfully"}

@router.get("/conversion-rates/")
async def get_conversion_rates():
    async with await get_db_connection() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute("""
                SELECT month, total_trials, total_conversions, conversion_rate
                FROM conversion_rates
                ORDER BY month;
            """)
            rates = await cur.fetchall()
    return rates