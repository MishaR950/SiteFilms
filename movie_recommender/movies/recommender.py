from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from .models import Movie, Rating, FavoriteMovie


class MLRecommender:
    def get_recommendations(self, user, n=12):
        print(f"Начало генерации рекомендаций для пользователя {user.username}")

        # Получаем избранные фильмы и оценки пользователя
        favorite_movies = FavoriteMovie.objects.filter(user=user).select_related('movie')
        user_ratings = Rating.objects.filter(user=user).select_related('movie')

        print(f"Найдено избранных фильмов: {favorite_movies.count()}")
        print(f"Найдено оценок: {user_ratings.count()}")

        if not (favorite_movies.exists() or user_ratings.exists()):
            print("Нет данных для рекомендаций")
            return []

        # Получаем все фильмы
        all_movies = list(Movie.objects.prefetch_related('genres').all())

        # Создаем описания фильмов для векторизации
        movie_features = []
        for movie in all_movies:
            features = []
            # Жанры (с повышенным весом)
            genres = ' '.join([genre.name + ' ' * 3 for genre in movie.genres.all()])
            features.append(genres)

            # Год выпуска
            features.append(f"year_{movie.release_year}")

            # Страна
            features.append(f"country_{movie.country}")

            # Название (с повышенным весом)
            features.append(movie.title + ' ' * 2)

            # Описание
            if movie.description:
                features.append(movie.description)

            movie_features.append(' '.join(features))

        # Векторизация текста
        vectorizer = TfidfVectorizer(stop_words='english')
        tfidf_matrix = vectorizer.fit_transform(movie_features)

        # Вычисляем схожесть
        similarity_matrix = cosine_similarity(tfidf_matrix)

        # Считаем итоговые оценки схожести
        user_movie_scores = np.zeros(len(all_movies))

        # Учитываем избранные фильмы
        for fav in favorite_movies:
            idx = all_movies.index(fav.movie)
            user_movie_scores += similarity_matrix[idx] * 1.0  # Вес для избранного

        # Учитываем оценки
        for rating in user_ratings:
            idx = all_movies.index(rating.movie)
            weight = rating.rating / 5.0  # Нормализуем оценку
            user_movie_scores += similarity_matrix[idx] * weight

        # Нормализуем оценки
        total_interactions = favorite_movies.count() + user_ratings.count()
        if total_interactions > 0:
            user_movie_scores = user_movie_scores / total_interactions

        # Создаем рекомендации
        rated_and_favorite_ids = set(favorite_movies.values_list('movie_id', flat=True)) | \
                                 set(user_ratings.values_list('movie_id', flat=True))

        recommendations = []
        for idx, score in enumerate(user_movie_scores):
            movie = all_movies[idx]
            if movie.id not in rated_and_favorite_ids:
                movie.ml_score = score * 100
                recommendations.append(movie)

        # Сортируем по оценке схожести
        recommendations.sort(key=lambda x: x.ml_score, reverse=True)

        print(f"Сгенерировано {len(recommendations[:n])} рекомендаций")
        return recommendations[:n]
