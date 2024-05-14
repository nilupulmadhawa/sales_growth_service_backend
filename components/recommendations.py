import os
import pandas as pd
import numpy as np
from fastapi import APIRouter, HTTPException
from fastapi import FastAPI, Depends
from pydantic import BaseModel
import joblib
from lightfm import LightFM
from lightfm.data import Dataset
import aiomysql
from .database import get_db_connection
from fastapi.exceptions import HTTPException


router = APIRouter()

model = None

def is_model_initialized(model):
    return hasattr(model, 'item_embeddings') and model.item_embeddings is not None

def get_model():
    global model
    if model is None:
        model_path = os.path.join('recommendation-model', 'recommendation_hybrid_model.joblib')
        try:
            model = joblib.load(model_path)
            if not hasattr(model, 'item_embeddings'):
                print("Model loaded but not properly initialized.")
                raise HTTPException(status_code=500, detail="Model not properly initialized")
        except FileNotFoundError:
            print("Model file not found")
            raise HTTPException(status_code=500, detail="Model file not found")
        except Exception as e:
            print(f"An unexpected error occurred: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    return model

class UserDemo(BaseModel):
    user_id: int
    num_recommendations: int

@router.post("/", response_model=list)
async def get_recommendations(user_input: UserDemo, model: LightFM = Depends(get_model)):
    if model is None:
        raise HTTPException(status_code=503, detail="Model is not available")
    return await recommendation(user_input.user_id, user_input.num_recommendations, model)

# Modification in the recommendation function to ensure it handles user mapping not found
async def recommendation(user_id: int, num_recommendations: int, model: LightFM):
    conn = await get_db_connection()
    try:
        user_data_result = await fetch_users(user_id, conn)
        if not user_data_result:
            raise HTTPException(status_code=404, detail="User data not found")

        dataset, interactions_matrix, weights_matrix, user_features, item_features = await load_data(conn)

        # Convert user_id to string if not already, to match dataset fitting
        user_id_str = str(user_id)
        user_x = dataset.mapping()[0].get(user_id_str)
        if user_x is None:
            raise HTTPException(status_code=404, detail="User mapping not found")

        scores = model.predict(user_x, np.arange(dataset.interactions_shape()[1]), user_features=user_features, item_features=item_features)
        top_items = np.argsort(-scores)[:num_recommendations]
        
        # Fetch known positives for the user
        known_positives = await fetch_known_positives(user_id, conn)
        
        # Return both top recommendations and known positives
        top_recommendations = [dataset.mapping()[2][i] for i in top_items]
        known_positives_list = [row['product_id'] for row in known_positives]
        
        return {
            "top_recommendations": top_recommendations,
            "known_positives": known_positives_list
        }
    finally:
        conn.close()

async def fetch_known_positives(user_id, conn):
    async with conn.cursor(aiomysql.DictCursor) as cursor:
        await cursor.execute("""
            SELECT e.product_id
            FROM events e
            WHERE e.user_id = %s;
        """, (user_id,))
        result = await cursor.fetchall()
        print("Known positives for user:", result)
        return result


async def fetch_users(user_id, conn):
    async with conn.cursor(aiomysql.DictCursor) as cursor:
        await cursor.execute("""
            SELECT u.user_id, u.age, u.gender, u.location, b.brand
            FROM users u
            JOIN brands b ON b.user_id = u.user_id
            WHERE u.user_id = %s;
        """, (user_id,))
        result = await cursor.fetchall()
        print("User data:", result)
        return result


async def fetch_products(conn):
    async with conn.cursor(aiomysql.DictCursor) as cursor:
        await cursor.execute("""
            SELECT p.product_id, p.product_name, p.product_category, p.product_brand
            FROM products p;
        """)
        result = await cursor.fetchall()
        # print("Products data:", result)
        return result

async def fetch_events(conn):
    async with conn.cursor(aiomysql.DictCursor) as cursor:
        await cursor.execute("""
            SELECT e.user_id, e.uri, e.event_type
            FROM events e;
        """)
        result = await cursor.fetchall()
        # print("Events data:", result)
        return result
    
async def fetch_all_users(conn):
    async with conn.cursor(aiomysql.DictCursor) as cursor:
        await cursor.execute("""
            SELECT u.user_id, u.age, u.gender, u.location, b.brand
            FROM users u
            JOIN brands b ON b.user_id = u.user_id;
        """)
        return await cursor.fetchall()
    

def fit_dataset(users_df, products_df, events_df):
    dataset = Dataset()

    # Ensure all user IDs and product IDs are considered as strings to prevent type mismatch issues
    user_ids = users_df['user_id'].astype(str)._append(events_df['user_id'].astype(str)).unique()
    item_ids = products_df['product_id'].astype(str)._append(events_df['product_id'].astype(str)).unique()

    # Fit dataset with all user and item IDs
    dataset.fit(
        users=user_ids,
        items=item_ids,
        user_features=user_features,
        item_features=item_features
    )

    # Check and fit missing item IDs
    missing_item_ids = set(predict_item_ids) - set(dataset.mapping()[2].keys())
    if missing_item_ids:
        dataset.fit_partial(items=list(missing_item_ids))

    return dataset




async def load_data(conn: aiomysql.Connection = Depends(get_db_connection)):
    try:
        # Fetch data from database
        users = await fetch_all_users(conn)
        products = await fetch_products(conn)
        events = await fetch_events(conn)

        # Convert fetched data to pandas DataFrames
        users_df = pd.DataFrame(users)
        products_df = pd.DataFrame(products)
        events_df = pd.DataFrame(events)

        # Preprocess events
        event_type_weights = {
            'purchase': 3.0, 'cart': 2.5, 'product': 2.0, 'department': 1.0, 'cancel': 0.5, 'home': 0.5
        }
        events_df['event_weight'] = events_df['event_type'].map(event_type_weights)
        events_df['product_id'] = events_df['uri'].apply(
            lambda uri: int(uri.split('/')[-1]) if '/product/' in uri else np.nan)

        events_df = events_df.dropna(subset=['product_id', 'user_id'])

        # Preprocess users
        users_df['age_group'] = pd.cut(users_df['age'], bins=[0, 18, 25, 35, 45, 55, 65, 100], labels=[
            '0-18', '19-25', '26-35', '36-45', '46-55', '56-65', '65+'])

        # Convert product_id to integer
        products_df['product_id'] = products_df['product_id'].astype(int)

        # For the events dataframe, ensure there's no missing product_id, then convert
        events_df.dropna(subset=['product_id'], inplace=True)
        events_df['product_id'] = events_df['product_id'].astype(int)

        # Fit dataset
        dataset = fit_dataset(users_df, products_df, events_df)

        # Build interaction data
        (interactions_matrix, weights_matrix) = dataset.build_interactions(
            ((row['user_id'], row['product_id'], row['event_weight']) for index, row in events_df.iterrows())
        )

        # Build user and item features
        user_features = dataset.build_user_features(
            (row['user_id'], [f"{row['gender']}_{row['age_group']}_{row['location']}"]) for index, row in users_df.iterrows())
        item_features = dataset.build_item_features(
            (row['product_id'], [f"{row['product_category']}_{row['product_brand']}"]) for index, row in products_df.iterrows())

        return dataset, interactions_matrix, weights_matrix, user_features, item_features
    finally:
        conn.close()
