from django.contrib.auth.views import LogoutView
from django.urls import path
from . import views

app_name = 'movies'

urlpatterns = [
    path('', views.movie_list, name='movie_list'),
    path('movie/<int:movie_id>/', views.movie_detail, name='movie_detail'),
    path('movie/<int:movie_id>/rate/', views.rate_movie, name='rate_movie'),  # Этот маршрут должен быть
    path('recommendations/', views.get_recommendations, name='recommendations'),
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('profile/', views.profile, name='profile'),
    path('search/', views.movie_search, name='movie_search'),
    path('logout/', views.logout_view, name='logout'),
    path('movie/<int:movie_id>/favorite/', views.add_to_favorites, name='add_to_favorites'),
    path('for-you/', views.MLRecommendationsView.as_view(), name='ml_recommendations'),

]
