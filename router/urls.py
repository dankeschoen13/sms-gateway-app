from django.urls import path
from . import views

urlpatterns = [
    path('webhook/', views.sms_webhook, name='sms_webhook'),
    path('report/', views.sms_report, name='daily_report'),
]