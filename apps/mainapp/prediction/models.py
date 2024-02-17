# prediction/models.py
from django.db import models

class MultiCategoryDataset(models.Model):
    event_time = models.CharField(max_length=30)
    event_type = models.CharField(max_length=30)
    product_id = models.IntegerField()
    category_id = models.FloatField()
    category_code = models.CharField(max_length=30)
    brand = models.CharField(max_length=30)
    price = models.FloatField()
    user_id = models.IntegerField()
    user_session = models.CharField(max_length=30)
    age = models.IntegerField()
    gender = models.CharField(max_length=30)
    location = models.CharField(max_length=30)
