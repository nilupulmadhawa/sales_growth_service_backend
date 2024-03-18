import pandas as pd
import pickle
from surprise import Reader, Dataset
from fastapi import APIRouter
from .models import UserInput  

router = APIRouter()

# Load the recommendation model and data
with open("recommendation-model/recommendation_model.pkl", "rb") as f:
    model = pickle.load(f)

data = pd.read_csv('recommendation-model/multi-category-dataset-recommendation.csv')

def map_event_type(event_type: str) -> float:
    mapping = {'view': 1.0, 'cart': 2.0, 'purchase': 3.0}
    return mapping.get(event_type, 0.0)

def collaborative_filtering_recommendation(age: float, gender: str, location: str, num_recommendations: int = 5):
    df = data.dropna(subset=['category_code']).copy()
    df['product_name'] = df['category_code'].str.split('.').str[-1]
    df['event_type_binary'] = df['event_type'].apply(map_event_type)
    df['pseudo_user_id'] = df['user_id'].astype(str)

    # Filter user_data based on the provided user input
    user_data = df[(df['age'] == age) & (df['gender'].str.lower() == gender.lower()) & (df['location'].str.lower() == location.lower())]

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

@router.post("/", response_model=list)  # Adjust endpoint as needed
async def get_recommendations(user_input: UserInput):
    recommendations = collaborative_filtering_recommendation(
        age=user_input.age,
        gender=user_input.gender,
        location=user_input.location,
        num_recommendations=user_input.num_recommendations
    )
    return recommendations
