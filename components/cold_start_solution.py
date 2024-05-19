from fastapi import HTTPException, APIRouter
import joblib
import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix
from typing import List
from lightfm.data import Dataset
from .database import get_db_connection
import logging

router = APIRouter()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load model
model = joblib.load('recommendation-model/recommendation_hybrid_model.pkl')

# Define the feature indices and total number of features
feature_indices = {
    'gender_male': 0,
    'gender_female': 1,
    'age_25': 2,
    'location_Daegu': 3,
    'brand_Nike': 4,
    'brand_Gucci': 5,
    'brand_Adidas': 6,
    'brand_HUGO_BOSS': 7,
    'brand_ZOO_YORK': 8
    # Add other brands as needed
}
num_features = 100  # Ensure this matches your model's feature setup

# Preprocessing
event_type_weights = {
    'purchase': 3.0,   # High weight as it directly indicates a preference.
    'cart': 2.5,       # Adding to cart is a strong buying signal.
    'product': 2.0,    # Viewing a product shows interest.
    'department': 1.0, # Browsing a department shows mild interest.
    'cancel': 0.5,     # Cancelling might indicate disinterest.
    'home': 0.5        # Visiting the home page is generic, low informational value.
}

async def get_user_data():
    user_query = "SELECT id, age, gender, location FROM users"
    async with get_db_connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(user_query)
            return await cur.fetchall()

async def get_product_data():
    product_query = "SELECT product_id as id, product_category, product_Brand, department, product_name FROM products"
    async with get_db_connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(product_query)
            return await cur.fetchall()

async def get_event_data():
    event_query = """
        SELECT e.user_id, e.event_type, e.uri, 
        CAST(SUBSTRING_INDEX(e.uri, '/', -1) AS UNSIGNED) AS product_id
        FROM events e
        JOIN products p ON p.id = CAST(SUBSTRING_INDEX(e.uri, '/', -1) AS UNSIGNED)
    """
    async with get_db_connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(event_query)
            return await cur.fetchall()

async def get_user_demo_details(user_id: str):
    user_query = """
        SELECT u.age, u.gender, u.location, b.brand
        FROM users u
        JOIN brands b ON b.user_id = u.user_id
        WHERE u.user_id = %s
    """
    async with get_db_connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(user_query, (user_id,))
            return await cur.fetchall()

def create_feature_vector(user_demo_details):
    feature_vector = [0] * num_features
    for detail in user_demo_details:
        age, gender, location, brand = detail[0], detail[1], detail[2], detail[3]
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

async def preprocess_data():
    user_data = await get_user_data()
    product_data = await get_product_data()
    event_data = await get_event_data()

    users_df = pd.DataFrame(user_data, columns=['id', 'age', 'gender', 'location'])
    products_df = pd.DataFrame(product_data, columns=['id', 'product_category', 'product_Brand', 'department', 'product_name'])
    events_df = pd.DataFrame(event_data, columns=['user_id', 'event_type', 'uri', 'product_id'])
    products_df['id'] = products_df['id'].astype(int)  
    events_df['event_weight'] = events_df['event_type'].map(event_type_weights)
    events_df = events_df.dropna(subset=['product_id', 'user_id'])
    events_df['user_id'] = events_df['user_id'].astype(int)
    events_df['product_id'] = events_df['product_id'].astype(int)

    filtered_events = events_df[events_df['user_id'].isin(users_df['id']) & events_df['product_id'].isin(products_df['id'])]

    users_df['age_group'] = pd.cut(users_df['age'], bins=[0, 18, 25, 35, 45, 55, 65, 100], labels=['0-18', '19-25', '26-35', '36-45', '46-55', '56-65', '65+'])

    dataset = Dataset()
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

    return dataset, user_features, item_features, interactions_matrix, weights_matrix, products_df

@router.get("/recommend/{user_id}", response_model=List[dict])
async def recommend_products(user_id: str):
    dataset, user_features, item_features, interactions_matrix, weights_matrix, products_df = await preprocess_data()
    
    user_demo_details = await get_user_demo_details(user_id)
    if not user_demo_details:
        return []

    user_features_csr = create_feature_vector(user_demo_details)
    
    user_mapping = dataset.mapping()[0]
    item_mapping = dataset.mapping()[2]

    if int(user_id) in user_mapping:
        user_index = user_mapping[int(user_id)]
        user_predictions = model.predict(user_index, np.arange(item_features.shape[0]), user_features=user_features, item_features=item_features)
        logger.info(f"Existing user {user_id} found. Predictions calculated.")
    else:
        user_predictions = model.predict(0, np.arange(item_features.shape[0]), user_features=user_features_csr, item_features=item_features)
        logger.info(f"New user {user_id}. Cold start predictions calculated.")

    top_items_indices = np.argsort(-user_predictions)[:50]  # Get top 50 items first
    top_item_ids = [item_mapping[i] for i in top_items_indices]

    # Filter products based on user's gender
    user_gender = 'men' if user_demo_details[0][1].lower() == 'm' else 'women'
    filtered_top_item_ids = [id for id in top_item_ids if products_df.loc[products_df['id'] == id, 'department'].values[0].lower() == user_gender]

    # Ensure user's selected brands are included
    user_brands = set(detail[3] for detail in user_demo_details)
    brand_items_ids = products_df[(products_df['product_Brand'].isin(user_brands)) & (products_df['department'].str.lower() == user_gender)]['id'].tolist()
    combined_ids = list(set(filtered_top_item_ids + brand_items_ids))

    # Predict items based on the combined IDs and limit to top 10
    combined_predictions = model.predict(0, np.array(combined_ids), user_features=user_features_csr, item_features=item_features)
    top_combined_indices = np.argsort(-combined_predictions)[:10]
    top_combined_item_ids = [combined_ids[i] for i in top_combined_indices]

    top_items_details = [{'id': id, 'product_name': products_df.loc[products_df['id'] == id, 'product_name'].values[0]} for id in top_combined_item_ids]

    return top_items_details
