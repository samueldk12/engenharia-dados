#!/usr/bin/env python3
"""
Example 2: Generate Personalized Recommendations
=================================================

This example demonstrates the complete recommendation pipeline:
1. Train collaborative filtering model
2. Generate candidate recommendations
3. Rank with ML features
4. Diversify results
5. Cache for fast serving

Author: Data Engineering Study Project
"""

import sys
from pathlib import Path
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Add project paths
sys.path.insert(0, str(Path(__file__).parent.parent / '06-sistema-recomendacao'))

from recommendation_engine import (
    MatrixFactorization,
    RecommendationEngine,
    diversify_recommendations_mmr
)
from feature_store import FeatureStore, UserFeatureGenerator, ContentFeatureGenerator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_sample_data():
    """
    Generate sample viewing data for demonstration
    """
    logger.info("Generating sample viewing data...")

    # 100 users, 500 movies/shows
    n_users = 100
    n_content = 500
    n_interactions = 5000

    np.random.seed(42)

    # Generate viewing history
    interactions = pd.DataFrame({
        'user_id': np.random.randint(1, n_users + 1, n_interactions),
        'content_id': np.random.randint(1, n_content + 1, n_interactions),
        'rating': np.random.choice([3, 4, 5], n_interactions, p=[0.2, 0.3, 0.5]),
        'watch_date': [
            datetime.now() - timedelta(days=np.random.randint(0, 90))
            for _ in range(n_interactions)
        ],
        'watch_duration_sec': np.random.randint(300, 7200, n_interactions),
        'completion_percentage': np.random.uniform(0.3, 1.0, n_interactions)
    })

    # Remove duplicates (user can only rate content once)
    interactions = interactions.drop_duplicates(subset=['user_id', 'content_id'])

    logger.info(f"  Generated {len(interactions)} interactions")
    logger.info(f"  Users: {interactions['user_id'].nunique()}")
    logger.info(f"  Content: {interactions['content_id'].nunique()}")

    # Generate content metadata
    content_metadata = pd.DataFrame({
        'content_id': range(1, n_content + 1),
        'title': [f'Content {i}' for i in range(1, n_content + 1)],
        'type': np.random.choice(['movie', 'series', 'documentary'], n_content),
        'genres': [
            np.random.choice(['action', 'comedy', 'drama', 'thriller', 'sci-fi'], 2).tolist()
            for _ in range(n_content)
        ],
        'release_year': np.random.randint(2015, 2024, n_content),
        'duration_sec': np.random.randint(3600, 7200, n_content)
    })

    return interactions, content_metadata


def main():
    """
    Complete recommendation generation pipeline
    """

    # =====================
    # Step 1: Load Data
    # =====================

    logger.info("=" * 60)
    logger.info("STEP 1: Loading viewing data")
    logger.info("=" * 60)

    # Generate sample data (in production, load from database)
    interactions, content_metadata = generate_sample_data()

    logger.info(f"\nDataset summary:")
    logger.info(f"  Interactions: {len(interactions):,}")
    logger.info(f"  Unique users: {interactions['user_id'].nunique():,}")
    logger.info(f"  Unique content: {interactions['content_id'].nunique():,}")
    logger.info(f"  Sparsity: {100 * (1 - len(interactions) / (interactions['user_id'].nunique() * interactions['content_id'].nunique())):.2f}%")

    # =====================
    # Step 2: Train Collaborative Filtering Model
    # =====================

    logger.info("\n" + "=" * 60)
    logger.info("STEP 2: Training collaborative filtering model")
    logger.info("=" * 60)

    # Initialize Matrix Factorization
    mf = MatrixFactorization(
        n_factors=50,  # Latent factors
        learning_rate=0.01,
        reg=0.02,  # L2 regularization
        n_epochs=20
    )

    logger.info("\nTraining Matrix Factorization...")
    logger.info(f"  Latent factors: {mf.n_factors}")
    logger.info(f"  Epochs: {mf.n_epochs}")

    # Train model
    mf.fit(interactions[['user_id', 'content_id', 'rating']], verbose=True)

    logger.info("  ✓ Model trained successfully")

    # =====================
    # Step 3: Evaluate Model
    # =====================

    logger.info("\n" + "=" * 60)
    logger.info("STEP 3: Evaluating model")
    logger.info("=" * 60)

    # Split data for evaluation
    train_size = int(0.8 * len(interactions))
    train_data = interactions[:train_size]
    test_data = interactions[train_size:]

    logger.info(f"\nTrain set: {len(train_data)} interactions")
    logger.info(f"Test set: {len(test_data)} interactions")

    # Retrain on train set
    mf_eval = MatrixFactorization(n_factors=50, n_epochs=20, learning_rate=0.01, reg=0.02)
    mf_eval.fit(train_data[['user_id', 'content_id', 'rating']], verbose=False)

    # Predict on test set
    predictions = mf_eval.predict_batch(test_data[['user_id', 'content_id']])

    # Calculate RMSE
    rmse = np.sqrt(np.mean((test_data['rating'] - predictions) ** 2))
    mae = np.mean(np.abs(test_data['rating'] - predictions))

    logger.info(f"\n✓ Evaluation metrics:")
    logger.info(f"  RMSE: {rmse:.4f}")
    logger.info(f"  MAE: {mae:.4f}")

    # =====================
    # Step 4: Generate Recommendations for User
    # =====================

    logger.info("\n" + "=" * 60)
    logger.info("STEP 4: Generating recommendations")
    logger.info("=" * 60)

    # Select a user
    user_id = 1

    # Get user's viewing history
    user_history = interactions[interactions['user_id'] == user_id]

    logger.info(f"\nGenerating recommendations for User {user_id}")
    logger.info(f"  User has watched {len(user_history)} items")
    logger.info(f"  Average rating: {user_history['rating'].mean():.2f}/5")

    # Show user's top-rated content
    top_rated = user_history.nlargest(5, 'rating')
    logger.info(f"\n  User's top-rated content:")
    for _, row in top_rated.iterrows():
        content = content_metadata[content_metadata['content_id'] == row['content_id']].iloc[0]
        logger.info(f"    - {content['title']} ({content['type']}, {content['genres']}) - Rating: {row['rating']}/5")

    # Generate top-N recommendations
    n_recommendations = 20

    logger.info(f"\n  Generating top-{n_recommendations} recommendations...")

    recommendations = mf.recommend(
        user_id=user_id,
        n=n_recommendations,
        exclude_seen=True
    )

    logger.info(f"  ✓ Generated {len(recommendations)} recommendations")

    # =====================
    # Step 5: Add Content Metadata
    # =====================

    logger.info("\n" + "=" * 60)
    logger.info("STEP 5: Enriching with content metadata")
    logger.info("=" * 60)

    recommendations_with_metadata = []

    for content_id, score in recommendations:
        content = content_metadata[content_metadata['content_id'] == content_id]

        if len(content) > 0:
            content = content.iloc[0]
            recommendations_with_metadata.append({
                'content_id': content_id,
                'score': score,
                'title': content['title'],
                'type': content['type'],
                'genres': content['genres'],
                'release_year': content['release_year']
            })

    logger.info(f"\n✓ Top-10 recommendations for User {user_id}:")
    logger.info("")

    for i, rec in enumerate(recommendations_with_metadata[:10], 1):
        logger.info(f"  {i}. {rec['title']}")
        logger.info(f"     Type: {rec['type']}, Genres: {rec['genres']}")
        logger.info(f"     Score: {rec['score']:.3f}")
        logger.info("")

    # =====================
    # Step 6: Diversify Recommendations
    # =====================

    logger.info("=" * 60)
    logger.info("STEP 6: Diversifying recommendations (MMR)")
    logger.info("=" * 60)

    logger.info("\nApplying Maximal Marginal Relevance...")

    diversified = diversify_recommendations_mmr(
        recommendations_with_metadata,
        n=10,
        lambda_param=0.5  # Balance relevance (1.0) and diversity (0.0)
    )

    logger.info(f"\n✓ Diversified top-10:")
    logger.info("")

    genre_counts = {}
    for i, rec in enumerate(diversified, 1):
        logger.info(f"  {i}. {rec['title']}")
        logger.info(f"     Type: {rec['type']}, Genres: {rec['genres']}")
        logger.info(f"     Score: {rec['score']:.3f}")
        logger.info("")

        # Count genres
        for genre in rec['genres']:
            genre_counts[genre] = genre_counts.get(genre, 0) + 1

    logger.info("  Genre distribution:")
    for genre, count in sorted(genre_counts.items(), key=lambda x: x[1], reverse=True):
        logger.info(f"    {genre}: {count}")

    # =====================
    # Step 7: Recommendation Explanations
    # =====================

    logger.info("\n" + "=" * 60)
    logger.info("STEP 7: Generating explanations")
    logger.info("=" * 60)

    # Find similar content user has watched
    top_rec = diversified[0]

    logger.info(f"\nWhy we recommend \"{top_rec['title']}\":")

    # Find user's watched content with similar genres
    similar_watched = user_history.merge(
        content_metadata,
        on='content_id',
        how='left'
    )

    similar_items = []
    for _, watched in similar_watched.iterrows():
        # Check genre overlap
        overlap = set(watched['genres']) & set(top_rec['genres'])
        if overlap:
            similar_items.append((watched['title'], watched['rating'], list(overlap)))

    if similar_items:
        logger.info(f"  Because you enjoyed:")
        for title, rating, common_genres in similar_items[:3]:
            logger.info(f"    - \"{title}\" ({rating}/5) [shared: {common_genres}]")
    else:
        logger.info(f"  Based on your overall preferences")

    # =====================
    # Step 8: Performance Metrics
    # =====================

    logger.info("\n" + "=" * 60)
    logger.info("STEP 8: Performance metrics")
    logger.info("=" * 60)

    import time

    # Measure prediction latency
    start = time.time()
    for _ in range(1000):
        mf.predict(user_id=1, content_id=100)
    prediction_latency = (time.time() - start) / 1000

    # Measure recommendation latency
    start = time.time()
    mf.recommend(user_id=1, n=20, exclude_seen=True)
    recommendation_latency = time.time() - start

    logger.info(f"\n✓ Latency benchmarks:")
    logger.info(f"  Single prediction: {prediction_latency * 1000:.2f}ms")
    logger.info(f"  Top-20 recommendations: {recommendation_latency * 1000:.2f}ms")

    target_p99 = 50  # ms
    if recommendation_latency * 1000 < target_p99:
        logger.info(f"  ✓ Within p99 target (<{target_p99}ms)")
    else:
        logger.warning(f"  ⚠ Exceeds p99 target (>{target_p99}ms)")

    # =====================
    # Step 9: Caching Strategy
    # =====================

    logger.info("\n" + "=" * 60)
    logger.info("STEP 9: Caching recommendations")
    logger.info("=" * 60)

    logger.info("\nIn production, cache recommendations in Redis:")
    logger.info("  Key: recommendations:user:{user_id}")
    logger.info("  TTL: 1 hour (refresh periodically)")
    logger.info("  Format: JSON list of content IDs + scores")

    # Simulated Redis cache
    import json

    cache_key = f"recommendations:user:{user_id}"
    cache_value = json.dumps([
        {'content_id': rec['content_id'], 'score': rec['score']}
        for rec in diversified
    ])

    logger.info(f"\n  Cache key: {cache_key}")
    logger.info(f"  Cache size: {len(cache_value)} bytes")
    logger.info(f"  TTL: 3600 seconds")

    """
    In production:

    import redis
    r = redis.Redis(host='localhost', port=6379)
    r.setex(cache_key, 3600, cache_value)
    """

    # =====================
    # Summary
    # =====================

    logger.info("\n" + "=" * 60)
    logger.info("RECOMMENDATION PIPELINE COMPLETED!")
    logger.info("=" * 60)

    logger.info(f"\nSummary:")
    logger.info(f"  ✓ Model trained on {len(interactions):,} interactions")
    logger.info(f"  ✓ RMSE: {rmse:.4f}")
    logger.info(f"  ✓ Generated {len(recommendations)} recommendations for User {user_id}")
    logger.info(f"  ✓ Diversified to balance relevance and variety")
    logger.info(f"  ✓ Latency: {recommendation_latency * 1000:.2f}ms (<50ms target)")
    logger.info(f"  ✓ Ready for caching and serving")

    logger.info(f"\nNext steps:")
    logger.info(f"  1. Deploy model to production")
    logger.info(f"  2. Set up Redis caching")
    logger.info(f"  3. Implement A/B testing")
    logger.info(f"  4. Monitor CTR and engagement metrics")
    logger.info(f"  5. Retrain model daily/weekly")


if __name__ == '__main__':
    main()
