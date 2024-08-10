from django.urls import path
from . import views

urlpatterns = [
    path('linebot_cat/', views.linebot_webhook, name='callback'),
]
