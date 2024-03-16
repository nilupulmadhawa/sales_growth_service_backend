from fastapi import FastAPI
import pickle
from pydantic import BaseModel
import pandas as pd
from surprise import Reader, Dataset
import aiomysql
import asyncio

app = FastAPI()

class UserInput(BaseModel):
    age: float
    gender: str
    location: str
    num_recommendations: int = 5 

with open("recommendation-model/recommendation_model.pkl", "rb") as f:
    model = pickle.load(f)

# Load the data to be used for recommendations
data = pd.read_csv('recommendation-model/multi-category-dataset-recommendation.csv')

def map_event_type(event_type: str) -> float:
    mapping = {'view': 1.0, 'cart': 2.0, 'purchase': 3.0}
    return mapping.get(event_type, 0.0)

def collaborative_filtering_recommendation(age: float, gender: str, location: str, num_recommendations: int = 5):
    df = data.dropna(subset=['category_code']).copy()  
    
    df['product_name'] = df['category_code'].str.split('.').str[-1]

    df['event_type_binary'] = df['event_type'].apply(map_event_type)

    df['pseudo_user_id'] = df['user_id'].astype(str) 

    user_data = df[(df['age'] == age) & (df['gender'].str.lower() == gender.lower()) & (df['location'] == location)]

    reader = Reader(rating_scale=(1, 3))  
    dataset = Dataset.load_from_df(user_data[['pseudo_user_id', 'product_name', 'event_type_binary']], reader)

    trainset = dataset.build_full_trainset()
    testset = trainset.build_anti_testset()

    predictions = model.test(testset)

    # Sort the predictions based on estimated ratings and then filter out only unique product names
    unique_recommendations = set()
    recommendations_list = []
    
    for uid, iid, true_r, est, _ in sorted(predictions, key=lambda x: x.est, reverse=True):
        if iid not in unique_recommendations:
            unique_recommendations.add(iid)
            recommendations_list.append(iid)
        if len(recommendations_list) == num_recommendations:
            break

    return recommendations_list

@app.post("/recommendations/")
async def get_recommendations(user_input: UserInput):
    age = user_input.age
    gender = user_input.gender
    location = user_input.location
    num_recommendations = user_input.num_recommendations

    recommendations = collaborative_filtering_recommendation(age, gender, location, num_recommendations)

    return {"recommendations": recommendations}


class Metrics(BaseModel):
    impressions: int
    clicks: int

# Example data
metrics_data = Metrics(impressions=3450, clicks=7890)

@app.get("/metrics/impressions")
async def get_impressions():
    return {"impressions": metrics_data.impressions}

@app.get("/metrics/clicks")
async def get_clicks():
    return {"clicks": metrics_data.clicks}


# Database connection details
DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'your_username',
    'password': 'your_password',
    'db': 'recommendation_system',
}

async def get_db_connection():
    conn = await aiomysql.connect(**DB_CONFIG)
    return conn

@app.post("/track/impression")
async def track_impression():
    async with await get_db_connection() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute("INSERT INTO impressions (created_at) VALUES (CURRENT_TIMESTAMP)")
            await conn.commit()
    return {"message": "Impression tracked"}

@app.post("/track/click")
async def track_click():
    async with await get_db_connection() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute("INSERT INTO clicks (created_at) VALUES (CURRENT_TIMESTAMP)")
            await conn.commit()
    return {"message": "Click tracked"}

@app.get("/metrics")
async def get_metrics():
    async with await get_db_connection() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute("SELECT COUNT(*) FROM impressions")
            impressions_count = await cursor.fetchone()
            await cursor.execute("SELECT COUNT(*) FROM clicks")
            clicks_count = await cursor.fetchone()
    return {"impressions": impressions_count[0], "clicks": clicks_count[0]}
