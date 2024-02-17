# views.py

from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from surprise import dump, SVD, Reader, Dataset, accuracy
from surprise.model_selection import train_test_split
from .models import MultiCategoryDataset  # Replace 'YourModel' with the actual name of your model
import os
import pandas as pd

# Load your collaborative filtering model same dir as views.py
loaded_collaborative_model = dump.load(os.path.join(os.path.dirname(__file__), 'collaborative_model.pkl'))[1]

def preprocess_data_for_collaborative_filtering(data):
    # Extract relevant columns
    columns_to_keep = ['user_id', 'event_type', 'category', 'product_name']
    df = data[columns_to_keep].copy()

    # Map event types to numerical ratings
    event_type_mapping = {
        'view': 1,
        'cart': 2,
        'purchase': 3
    }
    df['event_type_rating'] = df['event_type'].map(event_type_mapping)

    # Create a Surprise Reader and Dataset
    reader = Reader(rating_scale=(1, 3))
    surprise_data = Dataset.load_from_df(df[['user_id', 'product_name', 'event_type_rating']], reader)

    return surprise_data

def preprocess_and_get_trainset(data):
    surprise_data = preprocess_data_for_collaborative_filtering(data)

    # Split the dataset into train and test sets
    trainset, _ = train_test_split(surprise_data, test_size=0.2, random_state=42)

    return trainset

# Define a function to get collaborative filtering recommendations for a user
def collaborative_filtering_recommendation(user_id, loaded_collaborative_model, df, num_recommendations=5):
    # Predict ratings for all items (in this case, users)
    all_user_ids = df['user_id'].unique()
    candidate_user_ids = [uid for uid in all_user_ids if uid != user_id]

    predictions = [(uid, loaded_collaborative_model.predict(user_id, uid, r_ui=None, clip=False).est) for uid in candidate_user_ids]

    # Sort the predictions by estimated rating in descending order
    predictions.sort(key=lambda x: x[1], reverse=True)

    # Get the top N recommended users
    top_n_recommendations = predictions[:num_recommendations]

    return top_n_recommendations

# Assuming you have a model called 'YourModel'
all_objects = MultiCategoryDataset.objects.all()

# Create a DataFrame from the model data
df = pd.DataFrame(list(all_objects.values()))

# Step 1.3: Split "category_code" into "category" and "product_name"
split_category = df['category_code'].str.split('.', n=1, expand=True)
df['category'] = split_category[0]
df['product_name'] = split_category[1]

# Your Django view
@csrf_exempt
def get_user_recommendations(request):
    if request.method == 'POST':
        # Preprocess data and get the trainset
        trainset_collaborative = preprocess_and_get_trainset(df)

        # Get input data from the request
        user_id = request.POST.get('user_id')

        # Convert user_id to integer
        user_id = int(user_id)

        # Get collaborative filtering recommendations
        collaborative_recommendations = collaborative_filtering_recommendation(user_id, loaded_collaborative_model, df)

        # Convert int64 to int for JSON serialization
        collaborative_recommendations = [(int(uid), float(estimate)) for uid, estimate in collaborative_recommendations]

        # Return recommendations as JSON response
        return JsonResponse({'collaborative_recommendations': collaborative_recommendations})

    else:
        return JsonResponse({'error': 'Invalid request method'})
