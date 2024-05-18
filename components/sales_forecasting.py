from fastapi import APIRouter, Depends, HTTPException, Body
from typing import List, Optional, Dict, Any
import aiomysql
from pydantic import BaseModel, Field 
from .database import DB_CONFIG, get_db_connection
from fastapi import HTTPException
import httpx  # httpx is used for making asynchronous HTTP requests
import requests
import json
import numpy as np
from decimal import Decimal
from datetime import datetime, timedelta

router = APIRouter()
# Router for sales forecasting
sales_forecasting_router = APIRouter()

#####################################################
# sales forcasting view
# Pydantic models
class MonthlySales(BaseModel):
    sale_year: int
    sale_month: int
    total_sales: float

@sales_forecasting_router.get("/monthly-sales")
async def get_monthly_sales() -> List[Dict[str, Any]]:
    async with await get_db_connection() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cursor:
            query = """
            SELECT 
                YEAR(order_date) AS sale_year,
                MONTH(order_date) AS sale_month,
                SUM(amount) AS total_sales
            FROM 
                sales
            GROUP BY 
                YEAR(order_date), 
                MONTH(order_date)
            ORDER BY 
                sale_year, 
                sale_month;
            """
            await cursor.execute(query)
            result = await cursor.fetchall()
            # Convert Decimal to float for JSON serialization
            return [{k: float(v) if isinstance(v, Decimal) else v for k, v in record.items()} for record in result]

async def get_predictions_sales(data: Dict[str, Any]) -> float:
    url = 'https://gpqyjq06wd.execute-api.us-east-1.amazonaws.com/SalesPredictions/Sales'
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=data)
        if response.status_code == 200:
            response_data = response.json()
            print(response_data, "response")
            sales = response_data["data"]["sales"]
            print(sales,"yesdsafdaf")
            return sales
        else:
            raise HTTPException(status_code=response.status_code, detail=response.text)

@sales_forecasting_router.get("/combined-sales")
async def get_combined_sales() -> List[Dict[str, Any]]:
    # Fetch actual sales data
    actual_sales = await get_monthly_sales()

    # Extract features from actual sales data
    features = [sale['total_sales'] for sale in actual_sales][-12:]  # last 12 months of sales

    # Create the payload for the prediction API
    payload = {
        "httpMethod": "POST",
        "body": {
            "records": features
        }
    }

    # Fetch predicted sales data
    predicted_sales_data = await get_predictions_sales(data=payload)

     # Combine actual and predicted sales
    combined_sales = actual_sales.copy()
    if combined_sales:
        last_entry = combined_sales[-1]
        last_year = last_entry['sale_year']
        last_month = last_entry['sale_month']

        # Calculate the next month and year
        last_date = datetime(year=last_year, month=last_month, day=1)
        next_month_date = last_date + timedelta(days=31)  # Adding 31 days to ensure the next month is reached
        next_month = next_month_date.month
        next_year = next_month_date.year

        combined_sales.append({
            "sale_year": next_year,
            "sale_month": next_month,
            "total_sales": float(predicted_sales_data)
        })
    else:
        # If there are no actual sales, start predicting from the current month and year
        current_date = datetime.now()
        combined_sales.append({
            "sale_year": current_date.year,
            "sale_month": current_date.month,
            "total_sales": float(predicted_sales_data)
        })

    return combined_sales

######### Data model for sales by product category
class CategorySales(BaseModel):
    product_category: str
    total_sales: float

# Endpoint for fetching sales by product category
@sales_forecasting_router.get("/category-sales", response_model=List[CategorySales])
async def get_sales_by_category() -> List[Dict[str, Any]]:
    async with await get_db_connection() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cursor:
            query = """
            SELECT 
                product_category,
                SUM(amount) AS total_sales
            FROM 
                sales
            GROUP BY 
                product_category
            """
            await cursor.execute(query)
            result = await cursor.fetchall()
            # Convert Decimal to float for JSON serialization and format the response
            formatted_result = [
                {
                    "product_category": record['product_category'],
                    "total_sales": float(record['total_sales'])
                } 
                for record in result if record['total_sales'] is not None
            ]
            return formatted_result
########################################