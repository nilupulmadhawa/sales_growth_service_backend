# -*- coding: utf-8 -*-
"""test.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1z2KryFUo5zJ0j3su2DV3U4QuOBOi_TCK
"""

!pip install lightfm

import pandas as pd
import numpy as np
from lightfm import LightFM
from lightfm.data import Dataset
from lightfm.evaluation import precision_at_k, auc_score, reciprocal_rank
from lightfm.cross_validation import random_train_test_split
import matplotlib.pyplot as plt
import joblib

from google.colab import drive
drive.mount('/content/drive')

# Load your data
users_df = pd.read_csv('/content/drive/MyDrive/recommendation_service_dataset/users.csv')
products_df = pd.read_csv('/content/drive/MyDrive/recommendation_service_dataset/products.csv')
events_df = pd.read_csv('/content/drive/MyDrive/recommendation_service_dataset/events.csv')

# Preprocessing
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

# Add age group feature to users
users_df['age_group'] = pd.cut(users_df['age'], bins=[0, 18, 25, 35, 45, 55, 65, 100], labels=['0-18', '19-25', '26-35', '36-45', '46-55', '56-65', '65+'])


print(filtered_events.head())
print(users_df.head())

from lightfm.data import Dataset

# Initialize the dataset
dataset = Dataset()

# Fit the dataset with the user IDs, item IDs, and declare the features to use
dataset.fit(
    users=(x for x in users_df['id']),
    items=(x for x in products_df['id']),
    user_features=(f"{row['gender']}_{row['age_group']}_{row['state']}" for index, row in users_df.iterrows()),
    item_features=(f"{row['category']}_{row['brand']}_{row['department']}" for index, row in products_df.iterrows())
)

(interactions_matrix, weights_matrix) = dataset.build_interactions(
    (row['user_id'], row['product_id'], row['event_weight'])
    for index, row in events_df.iterrows()
)

user_features = dataset.build_user_features(
    (row['id'], [f"{row['gender']}_{row['age_group']}_{row['state']}"])
    for index, row in users_df[users_df['id'].isin(filtered_events['user_id'])].iterrows()
)

item_features = dataset.build_item_features(
    (row['id'], [f"{row['category']}_{row['brand']}_{row['department']}"])
    for index, row in products_df.iterrows()
)

from scipy.sparse import csr_matrix

# Updated user features for a female user
features_dict = {
    'gender_male': 1,  # Assuming the model was trained with this feature
    'age_25': 1,
    'location_Daegu': 1,
    'brand_Perry_Ellis': 1
}

# Assuming the total number of features is known and indexed, update accordingly
num_features = 100  # This should match your model's feature setup
feature_indices = {
    'gender_male': 0,  # Update the index as per your model's feature indexing
    'age_25': 1,
    'location_Daegu': 2,
    'brand_Perry_Ellis': 3
}

# Create the feature vector based on the defined features
feature_vector = [0] * num_features
for feature, index in feature_indices.items():
    if feature in features_dict:
        feature_vector[index] = features_dict[feature]

# Convert to CSR matrix
user_features_csr = csr_matrix(feature_vector)

# Load the model
model = joblib.load('recommendation_hybrid_model.pkl')

# Predicting with a manually created CSR matrix
num_items = dataset.interactions_shape()[1]  # Number of items
new_user_predictions = model.predict(0, np.arange(num_items), user_features=user_features_csr, item_features=item_features)

# Output the predictions
print("Predictions:", new_user_predictions)

# Predicting with a manually created CSR matrix
num_items = dataset.interactions_shape()[1]  # Number of items
new_user_predictions = model.predict(0, np.arange(num_items), user_features=user_features_csr, item_features=item_features)

# Extract the indices of the top items based on scores
top_items_indices = np.argsort(-new_user_predictions)[:20]

# Get the IDs of the top items from the indices
top_item_ids = products_df.iloc[top_items_indices]['id']

# Fetch details for these top items from your products DataFrame
top_items_details = products_df[products_df['id'].isin(top_item_ids)][['id', 'name']]

# Output the top item details
print("Top Recommended Items:")
print(top_items_details)