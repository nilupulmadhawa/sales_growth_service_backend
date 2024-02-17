from rest_framework import serializers
from . models import *


class MultiCategoryDatasetSerializer(serializers.ModelSerializer):
    class Meta:
        model = MultiCategoryDataset
        fields = ['event_time', 'event_type', 'product_id', 'category_id', 'category_code', 'brand', 'price', 'user_id', 'user_session', 'age','gender', 'location']
    