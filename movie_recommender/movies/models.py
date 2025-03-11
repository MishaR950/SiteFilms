from django.db import models
from django.contrib.auth.models import User


class Genre(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Movie(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    release_year = models.IntegerField()
    genres = models.ManyToManyField(Genre)
    country = models.CharField(max_length=100, default='Россия')  # Simple CharField for now
    poster = models.ImageField(upload_to='movie_posters/', null=True, blank=True)
    favorites = models.ManyToManyField(User, related_name='favorite_movies', blank=True)
    def __str__(self):
        return self.title


class Rating(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE)
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'movie')


class Country(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        verbose_name_plural = 'Countries'
        ordering = ['name']

    def __str__(self):
        return self.name

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()

    def __str__(self):
        return f"{self.user.username}'s profile"

class FavoriteMovie(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.movie.title}"


from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np


class ContentBasedRecommender:
    def __init__(self):
        self.vectorizer = TfidfVectorizer(stop_words='english')
        self.similarity_matrix = None
        self.movies = None

    def fit(self, movies):
        self.movies = movies
        # Создаем текстовое описание для каждого фильма
        movie_features = []
        for movie in movies:
            features = []
            features.extend([genre.name for genre in movie.genres.all()])
            features.append(str(movie.release_year))
            features.append(movie.title)
            movie_features.append(' '.join(features))

        # Создаем TF-IDF матрицу
        tfidf_matrix = self.vectorizer.fit_transform(movie_features)
        # Вычисляем матрицу схожести
        self.similarity_matrix = cosine_similarity(tfidf_matrix)

    def get_recommendations(self, user, n=12):
        if not self.similarity_matrix is not None:
            return []

        # Получаем избранные фильмы пользователя
        favorite_movies = user.favorite_movies.all()
        if not favorite_movies:
            return []

        # Вычисляем средний вектор схожести для всех избранных фильмов
        similarity_scores = np.zeros(len(self.movies))
        for fav_movie in favorite_movies:
            idx = list(self.movies).index(fav_movie)
            similarity_scores += self.similarity_matrix[idx]

        similarity_scores = similarity_scores / len(favorite_movies)

        # Получаем индексы наиболее похожих фильмов
        movie_indices = similarity_scores.argsort()[::-1]

        # Исключаем фильмы, которые уже в избранном
        recommended_movies = []
        fav_ids = set(favorite_movies.values_list('id', flat=True))

        for idx in movie_indices:
            movie = self.movies[idx]
            if movie.id not in fav_ids:
                movie.similarity_score = similarity_scores[idx] * 100
                recommended_movies.append(movie)
                if len(recommended_movies) == n:
                    break

        return recommended_movies
