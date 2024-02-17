from django.urls import path
from . import views

urlpatterns = [
    path('get_user_recommendations/', views.get_user_recommendations, name='get_user_recommendations'),
]


