from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate, logout
from django.db.models import Q
from django.views.generic import ListView
from .recommender import MLRecommender
from .models import Movie, Rating, Genre, Country, FavoriteMovie, ContentBasedRecommender
from .forms import UserRegistrationForm, LoginForm, ProfileForm
from django.views.decorators.csrf import csrf_protect


def movie_list(request):
    movies = Movie.objects.all()
    genres = Genre.objects.all()
    countries = Country.objects.all()
    user_favorites = []

    if request.user.is_authenticated:
        user_favorites = Movie.objects.filter(favoritemovie__user=request.user)

    selected_genre = request.GET.get('genre')
    selected_country = request.GET.get('country')
    selected_year = request.GET.get('year')
    selected_sort = request.GET.get('sort')

    if selected_genre:
        movies = movies.filter(genres__id=selected_genre)
    if selected_country:
        country_obj = Country.objects.get(id=selected_country)
        movies = movies.filter(country=country_obj)  # Filter using the Country object
    if selected_year:
        movies = movies.filter(release_year=selected_year)

    if selected_sort == 'year_desc':
        movies = movies.order_by('-release_year')
    elif selected_sort == 'year_asc':
        movies = movies.order_by('release_year')
    elif selected_sort == 'title':
        movies = movies.order_by('title')

    context = {
        'movies': movies.distinct(),
        'genres': genres,
        'countries': countries,
        'selected_genre': selected_genre,
        'selected_country': selected_country,
        'selected_year': selected_year,
        'selected_sort': selected_sort,
        'user_favorites': user_favorites,
    }
    return render(request, 'movies/movie_list.html', context)


def movie_detail(request, movie_id):
    movie = get_object_or_404(Movie, id=movie_id)
    user_rating = None
    if request.user.is_authenticated:
        user_rating = Rating.objects.filter(user=request.user, movie=movie).first()
    return render(request, 'movies/movie_detail.html', {
        'movie': movie,
        'user_rating': user_rating
    })


@login_required
def rate_movie(request, movie_id):
    movie = get_object_or_404(Movie, id=movie_id)

    if request.method == 'POST':
        rating = request.POST.get('rating')

        Rating.objects.update_or_create(
            user=request.user,
            movie=movie,
            defaults={'rating': rating}
        )

        messages.success(request, 'Ваша оценка сохранена!')
        return redirect('movies:movie_detail', movie_id=movie.id)

    return render(request, 'movies/rate_movie.html', {'movie': movie})


# views.py
@login_required
def get_recommendations(request):
    # Get user's favorite movies
    user_favorites = FavoriteMovie.objects.filter(user=request.user).values_list('movie', flat=True)

    # Get genres and countries from user's favorites
    favorite_genres = Genre.objects.filter(movie__favoritemovie__user=request.user).distinct()
    favorite_countries = Movie.objects.filter(favoritemovie__user=request.user).values_list('country',
                                                                                            flat=True).distinct()

    # Get recommended movies based on genres and countries
    recommended_movies = Movie.objects.filter(
        Q(genres__in=favorite_genres) | Q(country__in=favorite_countries)
    ).exclude(
        id__in=user_favorites  # Exclude movies that are already in favorites
    ).distinct()

    return render(request, 'movies/recommendations.html', {
        'movies': recommended_movies
    })


def register(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Регистрация успешна! Добро пожаловать!')
            return redirect('movies:movie_list')
    else:
        form = UserRegistrationForm()
    return render(request, 'movies/register.html', {'form': form})


def user_login(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Добро пожаловать, {username}!')
                return redirect('movies:movie_list')
            else:
                messages.error(request, 'Неверное имя пользователя или пароль')
    else:
        form = LoginForm()
    return render(request, 'movies/login.html', {'form': form})


def movie_search(request):
    query = request.GET.get('q', '')
    movies = Movie.objects.all()

    if query:
        movies = movies.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query) |
            Q(genres__name__icontains=query) |
            Q(country__icontains=query)
        ).distinct()

    context = {
        'movies': movies,
        'query': query,
    }
    return render(request, 'movies/search_results.html', context)


@login_required
def profile(request):
    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Ваш профиль обновлён!')
            return redirect('movies:profile')
    else:
        form = ProfileForm(instance=request.user)

    # Get favorites with their ratings
    favorite_movies = FavoriteMovie.objects.filter(user=request.user).select_related('movie')

    # Get all ratings for user's favorite movies
    ratings = Rating.objects.filter(
        user=request.user,
        movie__in=[fav.movie for fav in favorite_movies]
    ).select_related('movie')

    # Create a dictionary of movie_id: rating for easy access
    ratings_dict = {rating.movie_id: rating.rating for rating in ratings}

    # Add ratings to favorite movies
    for favorite in favorite_movies:
        favorite.current_rating = ratings_dict.get(favorite.movie.id)

    return render(request, 'movies/profile.html', {
        'form': form,
        'user_favorites': favorite_movies,
    })



@login_required
def add_to_favorites(request, movie_id):
    movie = get_object_or_404(Movie, id=movie_id)
    favorite = FavoriteMovie.objects.filter(user=request.user, movie=movie).first()

    if favorite:
        # Remove from favorites and delete rating
        favorite.delete()
        Rating.objects.filter(user=request.user, movie=movie).delete()
        messages.success(request, f"'{movie.title}' удален из избранного")
    else:
        # Add to favorites
        FavoriteMovie.objects.create(user=request.user, movie=movie)
        messages.success(request, f"'{movie.title}' добавлен в избранное")

    return redirect(request.META.get('HTTP_REFERER', 'movies:movie_list'))


@login_required
def remove_from_favorites(request, movie_id):
    movie = get_object_or_404(Movie, id=movie_id)
    favorite = FavoriteMovie.objects.filter(user=request.user, movie=movie).first()
    if favorite:
        favorite.delete()
        messages.success(request, f"Фильм '{movie.title}' удален из избранного!")
    else:
        messages.info(request, f"Фильм '{movie.title}' не был найден в избранном.")
    return redirect('movies:movie_list')

from django.contrib.auth import logout

@csrf_protect
def logout_view(request):
    if request.method == 'POST':
        logout(request)
        return redirect('movies:login')
    return redirect(request.META.get('HTTP_REFERER', 'movies:movie_list'))


class ContentRecommendationsView(LoginRequiredMixin, ListView):
    template_name = 'movies/ml_recommendations.html'
    context_object_name = 'recommended_movies'

    def get_queryset(self):
        # Инициализируем рекомендательную систему
        recommender = ContentBasedRecommender()
        # Получаем все фильмы
        movies = list(Movie.objects.all())
        # Обучаем модель
        recommender.fit(movies)
        # Получаем рекомендации
        return recommender.get_recommendations(self.request.user)


class MLRecommendationsView(LoginRequiredMixin, ListView):
    template_name = 'movies/ml_recommendations.html'
    context_object_name = 'recommended_movies'

    def get_queryset(self):
        # Check if user has any favorite movies
        user_favorites = FavoriteMovie.objects.filter(user=self.request.user)
        if not user_favorites.exists():
            return []

        recommender = MLRecommender()
        recommendations = recommender.get_recommendations(self.request.user)
        return recommendations


@login_required
def rate_movie(request, movie_id):
    if request.method == 'POST':
        movie = get_object_or_404(Movie, id=movie_id)
        rating_value = request.POST.get('rating')

        if rating_value:
            Rating.objects.update_or_create(
                user=request.user,
                movie=movie,
                defaults={'rating': rating_value}
            )
            return JsonResponse({'success': True, 'rating': rating_value})
    return JsonResponse({'success': False})