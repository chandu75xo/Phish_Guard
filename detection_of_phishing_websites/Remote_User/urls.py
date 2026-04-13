from django.urls import path
from . import views

urlpatterns = [
    path('', views.landing, name='landing'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('predict/', views.predict_url_view, name='predict'),
    path('history/', views.history, name='history'),
    path('profile/', views.profile, name='profile'),
]
