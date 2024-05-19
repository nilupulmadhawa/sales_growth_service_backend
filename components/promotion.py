import aiomysql
from fastapi import FastAPI, APIRouter
from fastapi.responses import JSONResponse
import pandas as pd
import joblib
from sklearn.preprocessing import LabelEncoder
from contextlib import asynccontextmanager
from decimal import Decimal
from datetime import datetime
import numpy as np  # Import numpy
from sklearn.impute import SimpleImputer  # Ensure both LabelEncoder and SimpleImputer are imported

# Assuming DB_CONFIG and get_db_connection are correctly defined in your .database module
from .database import DB_CONFIG, get_db_connection

app = FastAPI()
router = APIRouter()

@asynccontextmanager
async def get_db_connection():
    conn = await aiomysql.connect(**DB_CONFIG)
    try:
        yield conn
    finally:
        conn.close()

async def fetch_data():
    async with get_db_connection() as conn:
        cursor = await conn.cursor(aiomysql.DictCursor)
        await cursor.execute("""
            SELECT * FROM inventory_items 
            WHERE MONTH(created_at) = MONTH(CURRENT_DATE()) 
            AND (sold_at IS NULL OR sold_at = '')
        """)
        data = await cursor.fetchall()
        return pd.DataFrame(data)

def preprocess_data(data):
    # Convert 'created_at' and 'sold_at' to datetime, coercing errors
    data['created_at'] = pd.to_datetime(data['created_at'], errors='coerce')
    data['sold_at'] = pd.to_datetime(data['sold_at'], errors='coerce')
    
    # Extracting day of the week and week of the year from 'created_at'
    data['day_of_week'] = data['created_at'].dt.dayofweek
    data['week_of_year'] = data['created_at'].dt.isocalendar().week

    # Handling missing values
    numerical_imputer = SimpleImputer(strategy='median')
    categorical_imputer = SimpleImputer(strategy='most_frequent')
    data['cost'] = numerical_imputer.fit_transform(data[['cost']]).ravel()
    data['product_retail_price'] = numerical_imputer.fit_transform(data[['product_retail_price']]).ravel()
    if 'product_category' in data.columns:
        data['product_category'] = categorical_imputer.fit_transform(data['product_category'].values.reshape(-1, 1)).ravel()
    if 'product_department' in data.columns:
        data['product_department'] = categorical_imputer.fit_transform(data['product_department'].values.reshape(-1, 1)).ravel()
    
    # Encoding categorical variables
    encoder = LabelEncoder()
    if 'product_category' in data.columns:
        data['product_category_encoded'] = encoder.fit_transform(data['product_category'])
    if 'product_department' in data.columns:
        data['product_department_encoded'] = encoder.fit_transform(data['product_department'])

    # Convert NaT to None (which becomes 'null' in JSON)
    data['created_at'] = data['created_at'].apply(lambda x: x if not pd.isnull(x) else None)
    data['sold_at'] = data['sold_at'].apply(lambda x: x if not pd.isnull(x) else None)

    return data

@router.get("/predict-promotions")
async def predict_promotions():
    data = await fetch_data()
    data = preprocess_data(data)
    model = joblib.load('promotion/Promotion_model_new.pkl')  # Ensure this path is correct
    
    # Prepare features and target
    feature_columns = ['cost', 'product_category_encoded', 'product_department_encoded', 'day_of_week', 'week_of_year']
    features = data[feature_columns]

    # Predict using the model
    predictions = model.predict(features)

    # Adding predictions to the DataFrame
    data['is_promotion'] = predictions

    # Count of total predictions
    total_count = len(data)
    promotion_count = int(data['is_promotion'].sum())

    # Filter to get promotional products
    promotional_products = data[data['is_promotion'] == True]

    # Limit to 10 promotional products
    limited_promotional_products = promotional_products.head(10)
    
    # Select the required columns including product_id, product_name, and product_brand
    required_columns = ['product_id','created_at','sold_at', 'product_name', 'product_category','product_Brand', 'product_department',]
    if 'product_brand' in data.columns:
        required_columns.append('product_brand')
    limited_promotional_products = limited_promotional_products[required_columns]
    
    # Handle NaT and other non-serializable types, including int64
    limited_promotional_products_json = limited_promotional_products.applymap(
        lambda x: x.isoformat() if isinstance(x, datetime) else int(x) if isinstance(x, (np.integer, np.int64)) else x
    ).to_dict(orient='records')
    
    return JSONResponse(content={
        "total_items": total_count,
        "promotional_items_count": promotion_count,
        "limited_promotional_products_count": len(limited_promotional_products),
        "promotional_products": limited_promotional_products_json
    })

app.include_router(router)
