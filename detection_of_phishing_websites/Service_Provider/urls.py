from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.admin_login, name='admin_login'),
    path('logout/', views.admin_logout, name='admin_logout'),
    path('dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('users/', views.view_users, name='admin_users'),
    path('train/', views.train_model, name='admin_train'),
    path('predictions/', views.view_predictions, name='admin_predictions'),
    path('analytics/', views.analytics, name='admin_analytics'),
    path('export/', views.download_excel, name='admin_export'),
]
