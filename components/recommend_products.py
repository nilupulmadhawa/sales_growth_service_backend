import joblib
import aiomysql
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, APIRouter
from typing import List
from lightfm.data import Dataset
from scipy.sparse import csr_matrix
from .database import get_db_connection
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

router = APIRouter()
dataset = Dataset()
# Load the pre-trained LightFM model
model = joblib.load('recommendation-model/recommendation_hybrid_model.pkl')

# Define feature indices (update based on your feature setup)
feature_indices = {
    'gender_male': 0,
    'age_25': 1,
    'location_Daegu': 2,
    'brand_Perry_Ellis': 3,
}
num_features = len(feature_indices)

async def get_user_data(conn, user_id: str):
    query = """
        SELECT u.id, u.age, u.gender, u.location, b.brand
        FROM users u
        JOIN brands b ON b.user_id = u.user_id
        WHERE u.user_id = %s
    """
    async with conn.cursor(aiomysql.DictCursor) as cur:
        await cur.execute(query, (user_id,))
        return await cur.fetchall()

async def get_all_users_data(conn):
    query = """
        SELECT u.id, u.age, u.gender, u.location, b.brand
        FROM users u
        JOIN brands b ON b.user_id = u.user_id
    """
    async with conn.cursor(aiomysql.DictCursor) as cur:
        await cur.execute(query)
        return await cur.fetchall()

async def get_product_data(conn):
    query = "SELECT * FROM products"
    async with conn.cursor(aiomysql.DictCursor) as cur:
        await cur.execute(query)
        return await cur.fetchall()

async def get_events_data(conn):
    query = """
        SELECT e.user_id, e.event_type, e.uri, 
        CAST(SUBSTRING_INDEX(e.uri, '/', -1) AS UNSIGNED) AS product_id
        FROM events e
        JOIN products p ON p.id = CAST(SUBSTRING_INDEX(e.uri, '/', -1) AS UNSIGNED)
    """
    async with conn.cursor(aiomysql.DictCursor) as cur:
        await cur.execute(query)
        return await cur.fetchall()

def create_feature_vector(user_demo_details):
    feature_vector = [0] * num_features
    for detail in user_demo_details:
        age, gender, location, brand = detail['age'], detail['gender'], detail['location'], detail['brand']
        age_feature = f'age_{age}'
        gender_feature = 'gender_male' if gender.lower() == 'm' else 'gender_female'
        location_feature = f'location_{location}'
        brand_feature = f'brand_{brand}'
        
        if age_feature in feature_indices:
            feature_vector[feature_indices[age_feature]] = 1
        if gender_feature in feature_indices:
            feature_vector[feature_indices[gender_feature]] = 1
        if location_feature in feature_indices:
            feature_vector[feature_indices[location_feature]] = 1
        if brand_feature in feature_indices:
            feature_vector[feature_indices[brand_feature]] = 1

    return csr_matrix([feature_vector])

def preprocess_data(users_df, products_df, events_df):
    event_type_weights = {
        'purchase': 3.0,   # High weight as it directly indicates a preference.
        'cart': 2.5,       # Adding to cart is a strong buying signal.
        'product': 2.0,    # Viewing a product shows interest.
        'department': 1.0, # Browsing a department shows mild interest.
        'cancel': 0.5,     # Cancelling might indicate disinterest.
        'home': 0.5        # Visiting the home page is generic, low informational value.
    }

    events_df['event_weight'] = events_df['event_type'].map(event_type_weights)

    events_df['product_id'] = events_df.apply(lambda row: int(row['uri'].split('/')[-1]) if '/product/' in row['uri'] else np.nan, axis=1)
    events_df = events_df.dropna(subset=['product_id', 'user_id'])
    events_df.loc[:, 'user_id'] = events_df['user_id'].astype(int)
    events_df.loc[:, 'product_id'] = events_df['product_id'].astype(int)

    filtered_events = events_df[events_df['user_id'].isin(users_df['id']) & events_df['product_id'].isin(products_df['id'])]

    users_df['age_group'] = pd.cut(users_df['age'], bins=[0, 18, 25, 35, 45, 55, 65, 100], labels=['0-18', '19-25', '26-35', '36-45', '46-55', '56-65', '65+'])

    dataset.fit(
        users=(x for x in users_df['id']),
        items=(x for x in products_df['id']),
        user_features=(f"{row['gender']}_{row['age_group']}_{row['location']}" for index, row in users_df.iterrows()),
        item_features=(f"{row['product_category']}_{row['product_Brand']}_{row['department']}" for index, row in products_df.iterrows())
    )

    (interactions_matrix, weights_matrix) = dataset.build_interactions(
        (row['user_id'], row['product_id'], row['event_weight'])
        for index, row in filtered_events.iterrows()
    )

    user_features = dataset.build_user_features(
        (row['id'], [f"{row['gender']}_{row['age_group']}_{row['location']}"])
        for index, row in users_df.iterrows()
    )

    item_features = dataset.build_item_features(
        (row['id'], [f"{row['product_category']}_{row['product_Brand']}_{row['department']}"])
        for index, row in products_df.iterrows()
    )

    return dataset, user_features, item_features, interactions_matrix, weights_matrix

@router.get("/recommend/{user_id}", response_model=List[dict])
async def recommend_products(user_id: str):
    async with get_db_connection() as conn:
        # Fetch data
        user_data = await get_user_data(conn, user_id)
        if not user_data:
            logger.error(f"User not found: {user_id}")
            raise HTTPException(status_code=404, detail="User not found")
        
        product_data = await get_product_data(conn)
        products_df = pd.DataFrame(product_data)
        
        events_data = await get_events_data(conn)
        events_df = pd.DataFrame(events_data)

        user_df = pd.DataFrame(user_data)
        all_users_data = await get_all_users_data(conn)  # Fetch all users
        users_df = pd.DataFrame(all_users_data)

        # Preprocess data
        dataset, user_features, item_features, interactions_matrix, weights_matrix = preprocess_data(users_df, products_df, events_df)

        # Ensure the user ID exists in the dataset after preprocessing
        user_id_int = int(user_id)
        if user_id_int not in dataset.mapping()[0]:
            logger.error(f"User ID {user_id} not found in dataset after preprocessing")
            raise HTTPException(status_code=404, detail="User ID not found in dataset after preprocessing")

        # Get user mapping
        user_x = dataset.mapping()[0][user_id_int]

        scores = model.predict(user_x, np.arange(dataset.interactions_shape()[1]), user_features=user_features, item_features=item_features)
        top_items_indices = np.argsort(-scores)[:20]
        top_item_ids = [dataset.mapping()[2][i] for i in top_items_indices]
        
        # Filter products based on user's gender
        user_gender = 'men' if user_data[0]['gender'].lower() == 'm' else 'women'
        filtered_top_item_ids = [id for id in top_item_ids if products_df.loc[products_df['id'] == id, 'department'].values[0].lower() == user_gender]

        top_items_details = [{'id': id, 'product_name': products_df.loc[products_df['id'] == id, 'product_name'].values[0]} for id in filtered_top_item_ids]

        return top_items_details

@router.get("/similar_items/{item_id}", response_model=List[int])
async def get_similar_items(item_id: int):
    async with get_db_connection() as conn:
        if item_id not in dataset.mapping()[2]:
            raise HTTPException(status_code=404, detail="Item not found")
        
        item_features = dataset.build_item_features([(item_id, [])])

        similar_ids = similar_items(item_id, model, item_features)
        return similar_ids.tolist()

@router.get("/similar_users/{user_id}", response_model=List[int])
async def get_similar_users(user_id: str):
    async with get_db_connection() as conn:
        all_users_data = await get_all_users_data(conn)
        users_df = pd.DataFrame(all_users_data)
        user_id_int = int(user_id)
        logger.info(f"Checking for user ID {user_id_int} in dataset mappings")
        if user_id_int not in dataset.mapping()[0]:
            logger.error(f"User ID {user_id_int} not found in dataset mappings")
            raise HTTPException(status_code=404, detail="User not found")

        user_features = dataset.build_user_features([(user_id_int, [])])

        similar_ids = similar_users(user_id_int, model, user_features)
        return similar_ids.tolist()

def similar_items(item_id, model, item_features, N=10):
    item_bias, item_representations = model.get_item_representations(features=item_features)
    target_item_representation = item_representations[item_id]
    scores = item_representations.dot(target_item_representation)
    top_indices = np.argsort(-scores)[:N]
    return top_indices.tolist()

def similar_users(user_id, model, user_features, N=10):
    user_bias, user_representations = model.get_user_representations(features=user_features)
    target_user_representation = user_representations[user_id]
    scores = user_representations.dot(target_user_representation)
    top_indices = np.argsort(-scores)[:N]
    return top_indices.tolist()
