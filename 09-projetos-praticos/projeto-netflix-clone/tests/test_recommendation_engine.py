#!/usr/bin/env python3
"""
Netflix Clone - Recommendation Engine Tests
==========================================

Unit tests for recommendation system.

Author: Data Engineering Study Project
"""

import pytest
import numpy as np
import pandas as pd
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / '06-sistema-recomendacao'))

from recommendation_engine import (
    MatrixFactorization,
    RecommendationEngine,
    diversify_recommendations_mmr
)


class TestMatrixFactorization:
    """Test Matrix Factorization algorithm"""

    def test_initialization(self):
        """Test MF model initialization"""
        mf = MatrixFactorization(
            n_factors=10,
            learning_rate=0.01,
            reg=0.02,
            n_epochs=5
        )

        assert mf.n_factors == 10
        assert mf.learning_rate == 0.01
        assert mf.reg == 0.02
        assert mf.n_epochs == 5

    def test_fit_basic(self):
        """Test training on simple data"""
        # Create simple interaction data
        interactions = pd.DataFrame({
            'user_id': [1, 1, 2, 2, 3],
            'content_id': [101, 102, 101, 103, 102],
            'rating': [5, 4, 5, 3, 4]
        })

        mf = MatrixFactorization(n_factors=5, n_epochs=10)
        mf.fit(interactions)

        # Verify factors were created
        assert mf.user_factors is not None
        assert mf.item_factors is not None
        assert mf.user_factors.shape[1] == 5  # n_factors
        assert mf.item_factors.shape[1] == 5

    def test_predict(self):
        """Test prediction after training"""
        interactions = pd.DataFrame({
            'user_id': [1, 1, 2, 2, 3, 3],
            'content_id': [101, 102, 101, 103, 102, 103],
            'rating': [5, 4, 5, 3, 4, 5]
        })

        mf = MatrixFactorization(n_factors=5, n_epochs=20)
        mf.fit(interactions)

        # Predict for user 1, item 101 (should be ~5)
        prediction = mf.predict(user_id=1, content_id=101)

        assert isinstance(prediction, (int, float))
        assert 1 <= prediction <= 5  # Rating range

    def test_predict_batch(self):
        """Test batch predictions"""
        interactions = pd.DataFrame({
            'user_id': [1, 1, 2, 2],
            'content_id': [101, 102, 101, 103],
            'rating': [5, 4, 5, 3]
        })

        mf = MatrixFactorization(n_factors=5, n_epochs=10)
        mf.fit(interactions)

        # Batch predict
        test_data = pd.DataFrame({
            'user_id': [1, 2, 1],
            'content_id': [103, 102, 101]
        })

        predictions = mf.predict_batch(test_data)

        assert len(predictions) == 3
        assert all(1 <= p <= 5 for p in predictions)

    def test_recommend_top_n(self):
        """Test generating top-N recommendations"""
        interactions = pd.DataFrame({
            'user_id': [1, 1, 1, 2, 2],
            'content_id': [101, 102, 103, 101, 104],
            'rating': [5, 4, 3, 5, 4]
        })

        mf = MatrixFactorization(n_factors=5, n_epochs=20)
        mf.fit(interactions)

        # Get top-3 recommendations for user 1
        recommendations = mf.recommend(user_id=1, n=3, exclude_seen=True)

        assert len(recommendations) <= 3
        # Should not include items user has already rated
        seen_items = {101, 102, 103}
        assert all(item_id not in seen_items for item_id, _ in recommendations)

    def test_convergence(self):
        """Test that training loss decreases"""
        interactions = pd.DataFrame({
            'user_id': [1, 1, 2, 2, 3, 3] * 5,
            'content_id': [101, 102, 101, 103, 102, 103] * 5,
            'rating': [5, 4, 5, 3, 4, 5] * 5
        })

        mf = MatrixFactorization(n_factors=10, n_epochs=50, learning_rate=0.01)
        mf.fit(interactions, verbose=False)

        # Calculate RMSE on training data
        predictions = mf.predict_batch(interactions)
        rmse = np.sqrt(np.mean((interactions['rating'] - predictions) ** 2))

        # RMSE should be reasonably low after training
        assert rmse < 2.0


class TestRecommendationEngine:
    """Test RecommendationEngine class"""

    @patch('redis.Redis')
    @patch('psycopg2.connect')
    def test_initialization(self, mock_pg, mock_redis):
        """Test recommendation engine initialization"""
        engine = RecommendationEngine(
            redis_host='localhost',
            postgres_conn_str='postgresql://localhost/netflix'
        )

        assert engine.redis_client is not None
        assert engine.postgres_conn is not None

    @patch('redis.Redis')
    @patch('psycopg2.connect')
    def test_generate_candidates_collaborative(self, mock_pg, mock_redis):
        """Test candidate generation from collaborative filtering"""
        # Mock MF model
        mock_mf = MagicMock()
        mock_mf.recommend.return_value = [
            (201, 4.8),
            (202, 4.6),
            (203, 4.5)
        ]

        engine = RecommendationEngine(
            redis_host='localhost',
            postgres_conn_str='postgresql://localhost/netflix'
        )
        engine.mf_model = mock_mf

        candidates = engine.generate_candidates_collaborative(
            user_id=1,
            n=200
        )

        assert len(candidates) <= 200
        assert all('content_id' in c and 'score' in c for c in candidates)

    @patch('redis.Redis')
    @patch('psycopg2.connect')
    def test_generate_candidates_trending(self, mock_pg, mock_redis):
        """Test generating trending content candidates"""
        # Mock database query
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            (301, 1000),  # content_id, view_count
            (302, 800),
            (303, 600)
        ]
        mock_pg.return_value.cursor.return_value = mock_cursor

        engine = RecommendationEngine(
            redis_host='localhost',
            postgres_conn_str='postgresql://localhost/netflix'
        )

        candidates = engine.generate_candidates_trending(n=100)

        assert len(candidates) <= 100
        # Should be sorted by view count (descending)
        scores = [c['score'] for c in candidates]
        assert scores == sorted(scores, reverse=True)

    @patch('redis.Redis')
    @patch('psycopg2.connect')
    def test_generate_candidates_continue_watching(self, mock_pg, mock_redis):
        """Test continue watching candidates"""
        # Mock database query
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            (401, 0.3, 1800),  # content_id, completion, last_position
            (402, 0.5, 2700)
        ]
        mock_pg.return_value.cursor.return_value = mock_cursor

        engine = RecommendationEngine(
            redis_host='localhost',
            postgres_conn_str='postgresql://localhost/netflix'
        )

        candidates = engine.generate_candidates_continue_watching(user_id=1, n=10)

        assert len(candidates) <= 10
        assert all(c['completion'] < 0.9 for c in candidates)

    @patch('redis.Redis')
    @patch('psycopg2.connect')
    def test_generate_all_candidates(self, mock_pg, mock_redis):
        """Test generating candidates from all sources"""
        engine = RecommendationEngine(
            redis_host='localhost',
            postgres_conn_str='postgresql://localhost/netflix'
        )

        # Mock individual candidate generators
        engine.generate_candidates_collaborative = MagicMock(return_value=[
            {'content_id': 501, 'score': 0.9, 'source': 'cf'}
        ] * 200)

        engine.generate_candidates_trending = MagicMock(return_value=[
            {'content_id': 601, 'score': 0.8, 'source': 'trending'}
        ] * 100)

        engine.generate_candidates_continue_watching = MagicMock(return_value=[
            {'content_id': 701, 'score': 1.0, 'source': 'continue'}
        ] * 10)

        engine.generate_candidates_similar = MagicMock(return_value=[
            {'content_id': 801, 'score': 0.85, 'source': 'similar'}
        ] * 100)

        engine.generate_candidates_new_releases = MagicMock(return_value=[
            {'content_id': 901, 'score': 0.7, 'source': 'new'}
        ] * 50)

        context = {'device': 'smart_tv', 'time': 'evening'}
        candidates = engine.generate_candidates(user_id=1, context=context, n=500)

        # Should have ~500 candidates from all sources
        assert 450 <= len(candidates) <= 500

    @patch('redis.Redis')
    @patch('psycopg2.connect')
    def test_rank_candidates(self, mock_pg, mock_redis):
        """Test ranking candidates with features"""
        engine = RecommendationEngine(
            redis_host='localhost',
            postgres_conn_str='postgresql://localhost/netflix'
        )

        # Mock feature extraction
        engine.extract_features = MagicMock(return_value=pd.DataFrame({
            'content_id': [1, 2, 3],
            'cf_score': [0.9, 0.8, 0.7],
            'popularity': [100, 200, 150],
            'recency': [1, 5, 10]
        }))

        # Mock ranking model
        mock_ranker = MagicMock()
        mock_ranker.predict.return_value = np.array([0.95, 0.85, 0.80])
        engine.ranking_model = mock_ranker

        candidates = [
            {'content_id': 1, 'score': 0.9},
            {'content_id': 2, 'score': 0.8},
            {'content_id': 3, 'score': 0.7}
        ]

        ranked = engine.rank_candidates(
            candidates=candidates,
            user_id=1,
            context={}
        )

        # Should be ranked by model prediction
        assert len(ranked) == 3
        # First item should have highest score
        assert ranked[0]['ranking_score'] >= ranked[1]['ranking_score']

    @patch('redis.Redis')
    @patch('psycopg2.connect')
    def test_full_recommendation_pipeline(self, mock_pg, mock_redis):
        """Test complete recommendation pipeline"""
        engine = RecommendationEngine(
            redis_host='localhost',
            postgres_conn_str='postgresql://localhost/netflix'
        )

        # Mock each stage
        engine.generate_candidates = MagicMock(return_value=[
            {'content_id': i, 'score': 0.8} for i in range(500)
        ])

        engine.rank_candidates = MagicMock(return_value=[
            {'content_id': i, 'ranking_score': 0.9 - i * 0.001} for i in range(500)
        ])

        engine.diversify_recommendations = MagicMock(return_value=[
            {'content_id': i, 'ranking_score': 0.9} for i in range(20)
        ])

        # Get recommendations
        recommendations = engine.get_recommendations(
            user_id=1,
            n=20,
            context={'device': 'mobile'}
        )

        assert len(recommendations) == 20
        # Verify pipeline was called
        engine.generate_candidates.assert_called_once()
        engine.rank_candidates.assert_called_once()


class TestDiversification:
    """Test recommendation diversification"""

    def test_mmr_diversification(self):
        """Test MMR (Maximal Marginal Relevance) diversification"""
        # Create candidate recommendations with genres
        candidates = [
            {'content_id': 1, 'score': 0.95, 'genres': ['action', 'thriller']},
            {'content_id': 2, 'score': 0.93, 'genres': ['action', 'adventure']},
            {'content_id': 3, 'score': 0.90, 'genres': ['action', 'sci-fi']},
            {'content_id': 4, 'score': 0.88, 'genres': ['comedy']},
            {'content_id': 5, 'score': 0.85, 'genres': ['drama']},
            {'content_id': 6, 'score': 0.82, 'genres': ['horror']},
        ]

        # Diversify to top 4
        diversified = diversify_recommendations_mmr(
            candidates,
            n=4,
            lambda_param=0.5  # Balance relevance and diversity
        )

        assert len(diversified) == 4

        # First item should be highest scored
        assert diversified[0]['content_id'] == 1

        # Should include diverse genres (not all action)
        genres = [item['genres'][0] for item in diversified]
        unique_genres = set(genres)
        assert len(unique_genres) >= 2  # At least 2 different genres

    def test_diversification_lambda_extreme_cases(self):
        """Test MMR with extreme lambda values"""
        candidates = [
            {'content_id': i, 'score': 1.0 - i * 0.1, 'genres': ['genre' + str(i % 3)]}
            for i in range(10)
        ]

        # Lambda = 1.0 (pure relevance, no diversity)
        pure_relevance = diversify_recommendations_mmr(candidates, n=5, lambda_param=1.0)
        # Should be top 5 by score
        assert [c['content_id'] for c in pure_relevance] == [0, 1, 2, 3, 4]

        # Lambda = 0.0 (pure diversity, no relevance)
        pure_diversity = diversify_recommendations_mmr(candidates, n=5, lambda_param=0.0)
        # Should maximize genre diversity
        genres = [c['genres'][0] for c in pure_diversity]
        # Can't guarantee order, but should have diverse genres


class TestRecommendationCaching:
    """Test recommendation caching"""

    @patch('redis.Redis')
    @patch('psycopg2.connect')
    def test_cache_recommendations(self, mock_pg, mock_redis_class):
        """Test caching recommendations in Redis"""
        mock_redis = MagicMock()
        mock_redis_class.return_value = mock_redis

        engine = RecommendationEngine(
            redis_host='localhost',
            postgres_conn_str='postgresql://localhost/netflix'
        )

        recommendations = [
            {'content_id': 1, 'score': 0.9},
            {'content_id': 2, 'score': 0.8}
        ]

        engine.cache_recommendations(user_id=1, recommendations=recommendations, ttl=3600)

        # Verify Redis set was called
        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args

        assert 'recommendations:user:1' in call_args[0][0]
        assert call_args[0][1] == 3600  # TTL

    @patch('redis.Redis')
    @patch('psycopg2.connect')
    def test_get_cached_recommendations(self, mock_pg, mock_redis_class):
        """Test retrieving cached recommendations"""
        import json

        cached_data = json.dumps([
            {'content_id': 1, 'score': 0.9},
            {'content_id': 2, 'score': 0.8}
        ])

        mock_redis = MagicMock()
        mock_redis.get.return_value = cached_data.encode('utf-8')
        mock_redis_class.return_value = mock_redis

        engine = RecommendationEngine(
            redis_host='localhost',
            postgres_conn_str='postgresql://localhost/netflix'
        )

        cached = engine.get_cached_recommendations(user_id=1)

        assert cached is not None
        assert len(cached) == 2
        assert cached[0]['content_id'] == 1


# Performance tests

@pytest.mark.performance
class TestRecommendationPerformance:
    """Test recommendation performance"""

    def test_prediction_latency(self):
        """Test that predictions are fast enough"""
        import time

        # Create large dataset
        n_users = 1000
        n_items = 5000
        n_interactions = 50000

        np.random.seed(42)
        interactions = pd.DataFrame({
            'user_id': np.random.randint(1, n_users, n_interactions),
            'content_id': np.random.randint(1, n_items, n_interactions),
            'rating': np.random.randint(1, 6, n_interactions)
        })

        mf = MatrixFactorization(n_factors=20, n_epochs=5)

        # Train
        start = time.time()
        mf.fit(interactions, verbose=False)
        train_time = time.time() - start

        print(f"Training time: {train_time:.2f}s")

        # Predict (should be fast)
        start = time.time()
        for _ in range(1000):
            mf.predict(user_id=1, content_id=100)
        predict_time = (time.time() - start) / 1000

        print(f"Average prediction time: {predict_time * 1000:.2f}ms")

        # Prediction should be <1ms
        assert predict_time < 0.001

    def test_recommendation_latency(self):
        """Test that top-N recommendations are fast"""
        import time

        interactions = pd.DataFrame({
            'user_id': np.random.randint(1, 100, 5000),
            'content_id': np.random.randint(1, 500, 5000),
            'rating': np.random.randint(1, 6, 5000)
        })

        mf = MatrixFactorization(n_factors=20, n_epochs=5)
        mf.fit(interactions, verbose=False)

        # Generate recommendations (target <50ms)
        start = time.time()
        recommendations = mf.recommend(user_id=1, n=20)
        recommend_time = time.time() - start

        print(f"Recommendation time: {recommend_time * 1000:.2f}ms")

        # Should be <50ms for 20 recommendations
        assert recommend_time < 0.05
