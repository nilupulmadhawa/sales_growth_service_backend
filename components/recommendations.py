import pandas as pd
import pickle
from surprise import Reader, Dataset
from fastapi import APIRouter
from pydantic import BaseModel  # Ensure you have a Pydantic model for UserDemo

# Adjust the import path as necessary
from .database import get_db_connection

router = APIRouter()

# Load the recommendation model and data
with open("recommendation-model/recommendation_model.pkl", "rb") as f:
    model = pickle.load(f)

data = pd.read_csv('recommendation-model/multi-category-dataset-recommendation.csv')

def map_event_type(event_type: str) -> float:
    mapping = {'view': 1.0, 'cart': 2.0, 'purchase': 3.0}
    return mapping.get(event_type, 0.0)

# Define the UserDemo model correctly with required fields
class UserDemo(BaseModel):
    user_id: str
    num_recommendations: int

async def collaborative_filtering_recommendation(user_id: str, num_recommendations: int = 5):
    async def get_user(user_id: str):
        user_query = """
            SELECT u.age, u.gender, u.location, b.brand
            FROM users u
            JOIN brands b ON b.user_id = u.user_id
            WHERE u.user_id = %s
        """
        async with await get_db_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(user_query, (user_id,))
                return await cur.fetchall()

    # Await the result of get_user
    user_data_result = await get_user(user_id)
    if not user_data_result:
        return []

    print(user_data_result, num_recommendations)
    user_data = pd.DataFrame(user_data_result)
    age, gender, location, brand = user_data.iloc[0]

    df = data.dropna(subset=['category_code', 'brand']).copy()
    df['product_name'] = df['category_code'].str.split('.').str[-1]
    df['event_type_binary'] = df['event_type'].apply(map_event_type)
    df['pseudo_user_id'] = df['user_id'].astype(str)

    # Filter based on the provided user input and optionally the brand
    user_data = df[(df['age'] == age) & (df['gender'].str.lower() == gender.lower()) & (df['location'].str.lower() == location.lower())]
    if brand:
        user_data = user_data[user_data['brand'].str.lower() == brand.lower()]

    reader = Reader(rating_scale=(1, 3))
    dataset = Dataset.load_from_df(user_data[['pseudo_user_id', 'product_name', 'event_type_binary']], reader)

    trainset = dataset.build_full_trainset()
    testset = trainset.build_anti_testset()

    predictions = model.test(testset)

    # Process predictions to generate recommendations
    unique_recommendations = set()
    recommendations_list = []

    for uid, iid, true_r, est, _ in sorted(predictions, key=lambda x: x.est, reverse=True):
        if iid not in unique_recommendations:
            unique_recommendations.add(iid)
            recommendations_list.append(iid)

        if len(recommendations_list) == num_recommendations:
            break

    return recommendations_list

@router.post("/", response_model=list)
async def get_recommendations(user_input: UserDemo):
    recommendations = await collaborative_filtering_recommendation(
        user_id=user_input.user_id,
        num_recommendations=user_input.num_recommendations
    )
    return recommendations
