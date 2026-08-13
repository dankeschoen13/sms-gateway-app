from django.urls import path
from . import views

urlpatterns = [
    path('webhook/', views.sms_webhook, name='sms_webhook'),
    path('daily-report/', views.daily_report, name='daily_report'),
    path('weekly-report/', views.weekly_report, name='weekly_report')
]