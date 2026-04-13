from django.contrib import admin
from .models import UserProfile, URLPrediction, ModelAccuracy

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'country', 'city', 'created_at']

@admin.register(URLPrediction)
class URLPredictionAdmin(admin.ModelAdmin):
    list_display = ['user', 'url', 'result', 'checked_at']
    list_filter = ['result']

@admin.register(ModelAccuracy)
class ModelAccuracyAdmin(admin.ModelAdmin):
    list_display = ['model_name', 'accuracy', 'trained_at']
