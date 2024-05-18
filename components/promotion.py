import aiomysql
from fastapi import FastAPI
from fastapi.responses import JSONResponse
import pandas as pd
import joblib
from sklearn.preprocessing import LabelEncoder
from contextlib import asynccontextmanager
from fastapi import APIRouter
from .database import DB_CONFIG, get_db_connection

app = FastAPI()

router = APIRouter()


# Fetch data from the database
async def fetch_data():
    async with get_db_connection() as conn:
        cursor = await conn.cursor(aiomysql.DictCursor)
        await cursor.execute("SELECT * FROM inventory_items")
        data = await cursor.fetchall()
        return pd.DataFrame(data)

# Endpoint to predict promotions
@router.get("/predict-promotions/")
async def predict_promotions():
    data = await fetch_data()
    model = joblib.load('promotion/Promotion_model.pkl')
    
    # Data preprocessing
    data['created_at'] = pd.to_datetime(data['created_at'], errors='coerce')
    data['sold_at'] = pd.to_datetime(data['sold_at'], errors='coerce')
    data['month'] = data['created_at'].dt.month_name()
    data['day_of_week'] = data['created_at'].dt.dayofweek
    data['week_of_year'] = data['created_at'].dt.isocalendar().week

    # Encoding
    encoder = LabelEncoder()
    data['product_category_encoded'] = encoder.fit_transform(data['product_category'])
    data['product_department_encoded'] = encoder.fit_transform(data['product_department'])

    # Feature selection and prediction
    features = data[['cost', 'product_category_encoded', 'product_department_encoded', 'day_of_week', 'week_of_year']]
    predictions = model.predict(features)
    promotional_products = data[predictions == True]

    # Return results as JSON
    return JSONResponse(content=promotional_products.to_dict(orient='records'))

