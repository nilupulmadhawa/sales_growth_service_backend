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


@router.get("/metrics/trial-conversion-rate")
async def get_trial_conversion_rate():
    async with await get_db_connection() as conn:
        async with conn.cursor() as cur:
            # Example SQL query, adjust based on your actual database schema
            await cur.execute("""
                SELECT 
                    MONTH(date_field) AS month,
                    SUM(case when event_type = 'trial' then 1 else 0 end) AS total_trials,
                    SUM(case when event_type = 'conversion' then 1 else 0 end) AS total_conversions
                FROM 
                    events_table
                GROUP BY 
                    MONTH(date_field)
            """)
            result = await cur.fetchall()
            # Calculate conversion rate
            conversion_rates = {row[0]: (row[2] / row[1] if row[1] > 0 else 0) for row in result}
    return conversion_rates