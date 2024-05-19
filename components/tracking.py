from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
import aiomysql
from typing import Optional, List
from models import UserInput, Metrics, Event

# Assuming DB_CONFIG and get_db_connection() are defined as shown earlier
from .database import DB_CONFIG, get_db_connection

router = APIRouter()

@router.post("/event/")
async def record_event(event: Event):
    query = """
        INSERT INTO events (user_id, product_id, event_type, event_time, uri) 
        VALUES (%s, %s, %s, NOW(), %s)
    """
    async with get_db_connection() as conn:
        async with conn.cursor() as cur:
            try:
                await cur.execute(query, (event.user_id, event.product_id, event.event_type, event.uri))
                await conn.commit()
            except Exception as e:
                await conn.rollback()
                raise HTTPException(status_code=500, detail=str(e))
    return {"message": "Event recorded successfully"}

@router.get("/metrics/{metric}")
async def get_metrics(metric: str):
    if metric not in ["impressions", "clicks"]:
        raise HTTPException(status_code=404, detail="Metric not found")

    async with get_db_connection() as conn:
        async with conn.cursor() as cur:
            if metric == "impressions":
                await cur.execute("SELECT COUNT(*) FROM events WHERE event_type IN ('purchase', 'cart', 'product', 'department', 'home')")
            elif metric == "clicks":
                await cur.execute("SELECT COUNT(*) FROM events WHERE event_type IN ('product', 'cart')")

            (total,) = await cur.fetchone()
    return {metric: total}



@router.get("/conversion-rates/", response_model=List[dict])
async def get_conversion_rates(year: Optional[int] = Query(None)):
    async with get_db_connection() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            query = """
                SELECT 
                    DATE_FORMAT(event_time, '%%Y-%%m') AS month,
                    MONTHNAME(event_time) AS month_name,
                    SUM(CASE 
                        WHEN event_type = 'purchase' THEN 3.0 
                        WHEN event_type = 'cart' THEN 2.5
                        WHEN event_type = 'product' THEN 2.0
                        WHEN event_type = 'department' THEN 1.0
                        WHEN event_type = 'cancel' THEN 0.5
                        WHEN event_type = 'home' THEN 0.5
                        ELSE 0 
                    END) AS total_trials,
                    SUM(CASE 
                        WHEN event_type = 'purchase' THEN 3.0
                        ELSE 0 
                    END) AS total_conversions,
                    (SUM(CASE 
                        WHEN event_type = 'purchase' THEN 3.0 
                        ELSE 0 
                    END) / SUM(CASE 
                        WHEN event_type IN ('purchase', 'cart', 'product', 'department', 'cancel', 'home') THEN 
                            CASE 
                                WHEN event_type = 'purchase' THEN 3.0
                                WHEN event_type = 'cart' THEN 2.5
                                WHEN event_type = 'product' THEN 2.0
                                WHEN event_type = 'department' THEN 1.0
                                WHEN event_type = 'cancel' THEN 0.5
                                WHEN event_type = 'home' THEN 0.5
                                ELSE 0 
                            END 
                        ELSE 0 
                    END)) * 100 AS conversion_rate
                FROM 
                    events
                WHERE
                    YEAR(event_time) = %s
                GROUP BY 
                    month, month_name
                ORDER BY 
                    month;
            """
            await cur.execute(query, (year,))
            rates = await cur.fetchall()
    return rates

# Function to insert event data into the events table
async def add_event(event: Event):
    async with get_db_connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "INSERT INTO events (user_id, product_id, event_type) VALUES (%s, %s, %s)",
                (event.user_id, event.product_id, event.event_type)
            )
            await conn.commit()

# API endpoint to add events
@router.post("/events/add")
async def add_event_route(event: Event):
    await add_event(event)
    return {"message": "Event added successfully"}


@router.post("/events/")
async def save_event(event: Event):
    query = """
        INSERT INTO events (user_id, event_type, event_time, uri) 
        VALUES (%s, %s, %s, %s)
    """
    async with get_db_connection() as conn:
        async with conn.cursor() as cur:
            try:
                await cur.execute(query, (event.user_id, event.event_type, event.event_time, event.uri))
                await conn.commit()
            except Exception as e:
                await conn.rollback()
                raise HTTPException(status_code=500, detail=str(e))
    return {"message": "Event saved successfully"}