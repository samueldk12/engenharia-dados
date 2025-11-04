#!/usr/bin/env python3
"""
Netflix Clone - Recommendation Engine
======================================

Sistema de recomendação personalizado usando múltiplos algoritmos.

Algorithms:
- Collaborative Filtering (Matrix Factorization)
- Neural Collaborative Filtering
- Content-Based Filtering
- Hybrid Ranking (LambdaMART)

Pipeline:
1. Feature Engineering
2. Candidate Generation (retrieve ~500 items)
3. Ranking (score and rank top items)
4. Diversification (ensure variety)
5. Business Rules (promote Netflix originals, etc.)

Author: Data Engineering Study Project
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import logging
import pickle
from pathlib import Path

# ML libraries
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import MinMaxScaler
import torch
import torch.nn as nn
import torch.optim as optim

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class RecommendationResult:
    """Recommendation result"""
    content_id: int
    title: str
    score: float
    reason: str  # "Because you watched X", "Trending", etc.
    rank: int

    def to_dict(self):
        return asdict(self)


@dataclass
class UserContext:
    """User context for personalization"""
    user_id: int
    profile_id: int
    age: Optional[int] = None
    gender: Optional[str] = None
    country: str = 'US'
    device_type: str = 'web'
    time_of_day: str = 'evening'  # morning, afternoon, evening, night
    subscription_tier: str = 'standard'  # basic, standard, premium


class MatrixFactorization:
    """
    Collaborative Filtering using Matrix Factorization (SVD)

    Factorizes user-item interaction matrix into:
    - User latent factors
    - Item latent factors

    Prediction: rating ≈ user_factors · item_factors^T
    """

    def __init__(self, n_factors: int = 50, learning_rate: float = 0.01,
                 reg: float = 0.02, n_epochs: int = 20):
        """
        Args:
            n_factors: Number of latent factors
            learning_rate: Learning rate for SGD
            reg: Regularization parameter
            n_epochs: Number of training epochs
        """
        self.n_factors = n_factors
        self.learning_rate = learning_rate
        self.reg = reg
        self.n_epochs = n_epochs

        self.user_factors = None
        self.item_factors = None
        self.user_bias = None
        self.item_bias = None
        self.global_mean = 0.0

        self.user_id_map = {}
        self.item_id_map = {}

    def fit(self, interactions: pd.DataFrame):
        """
        Train matrix factorization model

        Args:
            interactions: DataFrame with columns [user_id, content_id, rating]
                         rating = implicit feedback (e.g., watch_percentage * 5)
        """
        logger.info(f"Training Matrix Factorization with {len(interactions)} interactions")

        # Create mappings
        unique_users = interactions['user_id'].unique()
        unique_items = interactions['content_id'].unique()

        self.user_id_map = {uid: idx for idx, uid in enumerate(unique_users)}
        self.item_id_map = {iid: idx for idx, iid in enumerate(unique_items)}

        n_users = len(unique_users)
        n_items = len(unique_items)

        # Initialize factors
        self.user_factors = np.random.normal(0, 0.1, (n_users, self.n_factors))
        self.item_factors = np.random.normal(0, 0.1, (n_items, self.n_factors))
        self.user_bias = np.zeros(n_users)
        self.item_bias = np.zeros(n_items)
        self.global_mean = interactions['rating'].mean()

        # Training loop (Stochastic Gradient Descent)
        for epoch in range(self.n_epochs):
            epoch_loss = 0.0

            # Shuffle interactions
            shuffled = interactions.sample(frac=1).reset_index(drop=True)

            for _, row in shuffled.iterrows():
                user_idx = self.user_id_map[row['user_id']]
                item_idx = self.item_id_map[row['content_id']]
                rating = row['rating']

                # Predict
                prediction = (
                    self.global_mean +
                    self.user_bias[user_idx] +
                    self.item_bias[item_idx] +
                    np.dot(self.user_factors[user_idx], self.item_factors[item_idx])
                )

                # Error
                error = rating - prediction
                epoch_loss += error ** 2

                # Update biases
                self.user_bias[user_idx] += self.learning_rate * (error - self.reg * self.user_bias[user_idx])
                self.item_bias[item_idx] += self.learning_rate * (error - self.reg * self.item_bias[item_idx])

                # Update factors
                user_factor_update = self.learning_rate * (error * self.item_factors[item_idx] - self.reg * self.user_factors[user_idx])
                item_factor_update = self.learning_rate * (error * self.user_factors[user_idx] - self.reg * self.item_factors[item_idx])

                self.user_factors[user_idx] += user_factor_update
                self.item_factors[item_idx] += item_factor_update

            # Log progress
            rmse = np.sqrt(epoch_loss / len(shuffled))
            if (epoch + 1) % 5 == 0:
                logger.info(f"Epoch {epoch + 1}/{self.n_epochs}, RMSE: {rmse:.4f}")

        logger.info("Training complete")

    def predict(self, user_id: int, content_id: int) -> float:
        """Predict rating for user-item pair"""
        if user_id not in self.user_id_map or content_id not in self.item_id_map:
            return self.global_mean

        user_idx = self.user_id_map[user_id]
        item_idx = self.item_id_map[content_id]

        prediction = (
            self.global_mean +
            self.user_bias[user_idx] +
            self.item_bias[item_idx] +
            np.dot(self.user_factors[user_idx], self.item_factors[item_idx])
        )

        return prediction

    def recommend(self, user_id: int, n: int = 10,
                  exclude_seen: List[int] = None) -> List[Tuple[int, float]]:
        """
        Recommend top N items for user

        Returns:
            List of (content_id, score) tuples
        """
        if user_id not in self.user_id_map:
            logger.warning(f"User {user_id} not in training data")
            return []

        user_idx = self.user_id_map[user_id]

        # Calculate scores for all items
        scores = (
            self.global_mean +
            self.user_bias[user_idx] +
            self.item_bias +
            np.dot(self.user_factors[user_idx], self.item_factors.T)
        )

        # Exclude already seen items
        if exclude_seen:
            for item_id in exclude_seen:
                if item_id in self.item_id_map:
                    item_idx = self.item_id_map[item_id]
                    scores[item_idx] = -np.inf

        # Get top N
        top_indices = np.argsort(scores)[::-1][:n]

        # Map back to content IDs
        reverse_item_map = {idx: iid for iid, idx in self.item_id_map.items()}
        recommendations = [
            (reverse_item_map[idx], scores[idx])
            for idx in top_indices
        ]

        return recommendations

    def save(self, path: str):
        """Save model to disk"""
        model_data = {
            'user_factors': self.user_factors,
            'item_factors': self.item_factors,
            'user_bias': self.user_bias,
            'item_bias': self.item_bias,
            'global_mean': self.global_mean,
            'user_id_map': self.user_id_map,
            'item_id_map': self.item_id_map,
            'params': {
                'n_factors': self.n_factors,
                'learning_rate': self.learning_rate,
                'reg': self.reg,
                'n_epochs': self.n_epochs
            }
        }

        with open(path, 'wb') as f:
            pickle.dump(model_data, f)

        logger.info(f"Model saved to {path}")

    @classmethod
    def load(cls, path: str):
        """Load model from disk"""
        with open(path, 'rb') as f:
            model_data = pickle.load(f)

        model = cls(**model_data['params'])
        model.user_factors = model_data['user_factors']
        model.item_factors = model_data['item_factors']
        model.user_bias = model_data['user_bias']
        model.item_bias = model_data['item_bias']
        model.global_mean = model_data['global_mean']
        model.user_id_map = model_data['user_id_map']
        model.item_id_map = model_data['item_id_map']

        logger.info(f"Model loaded from {path}")
        return model


class NeuralCollaborativeFiltering(nn.Module):
    """
    Neural Collaborative Filtering using Deep Learning

    Architecture:
    - User embedding layer
    - Item embedding layer
    - Deep neural network with multiple hidden layers
    - Output: predicted rating/interaction score
    """

    def __init__(self, n_users: int, n_items: int,
                 embedding_dim: int = 64,
                 hidden_layers: List[int] = [128, 64, 32]):
        super().__init__()

        self.n_users = n_users
        self.n_items = n_items
        self.embedding_dim = embedding_dim

        # Embeddings
        self.user_embedding = nn.Embedding(n_users, embedding_dim)
        self.item_embedding = nn.Embedding(n_items, embedding_dim)

        # MLP layers
        layers = []
        input_dim = embedding_dim * 2

        for hidden_dim in hidden_layers:
            layers.append(nn.Linear(input_dim, hidden_dim))
            layers.append(nn.ReLU())
            layers.append(nn.Dropout(0.2))
            input_dim = hidden_dim

        layers.append(nn.Linear(input_dim, 1))
        layers.append(nn.Sigmoid())  # Output between 0 and 1

        self.mlp = nn.Sequential(*layers)

        # Initialize weights
        self._init_weights()

    def _init_weights(self):
        """Initialize embeddings with normal distribution"""
        nn.init.normal_(self.user_embedding.weight, std=0.01)
        nn.init.normal_(self.item_embedding.weight, std=0.01)

    def forward(self, user_ids: torch.Tensor, item_ids: torch.Tensor) -> torch.Tensor:
        """
        Forward pass

        Args:
            user_ids: User IDs (batch_size,)
            item_ids: Item IDs (batch_size,)

        Returns:
            Predicted scores (batch_size, 1)
        """
        user_embeds = self.user_embedding(user_ids)
        item_embeds = self.item_embedding(item_ids)

        # Concatenate embeddings
        x = torch.cat([user_embeds, item_embeds], dim=1)

        # Pass through MLP
        output = self.mlp(x)

        return output

    def predict(self, user_id: int, item_id: int) -> float:
        """Predict score for single user-item pair"""
        self.eval()
        with torch.no_grad():
            user_tensor = torch.LongTensor([user_id])
            item_tensor = torch.LongTensor([item_id])
            score = self.forward(user_tensor, item_tensor).item()
        return score


class RecommendationEngine:
    """
    Complete recommendation engine combining multiple algorithms
    """

    def __init__(self):
        self.matrix_factorization = None
        self.neural_cf = None
        self.content_features = None  # Content-based features
        self.trending_cache = {}  # Cache for trending content

        logger.info("Recommendation Engine initialized")

    def train_collaborative_filtering(self, interactions: pd.DataFrame):
        """
        Train collaborative filtering model

        Args:
            interactions: DataFrame with [user_id, content_id, rating]
        """
        logger.info("Training Collaborative Filtering...")

        self.matrix_factorization = MatrixFactorization(
            n_factors=50,
            learning_rate=0.01,
            reg=0.02,
            n_epochs=20
        )

        self.matrix_factorization.fit(interactions)

        logger.info("Collaborative Filtering training complete")

    def generate_candidates(self, user_id: int, context: UserContext,
                           n_candidates: int = 500) -> List[Tuple[int, float, str]]:
        """
        Generate candidate items from multiple sources

        Sources:
        - Collaborative Filtering (personalized)
        - Trending content (time-decayed popularity)
        - Continue Watching
        - Similar to recently watched
        - New releases

        Returns:
            List of (content_id, score, source) tuples
        """
        logger.info(f"Generating {n_candidates} candidates for user {user_id}")

        candidates = []

        # 1. Collaborative Filtering (personalized recommendations)
        if self.matrix_factorization:
            cf_recs = self.matrix_factorization.recommend(user_id, n=200)
            candidates.extend([
                (content_id, score, 'personalized')
                for content_id, score in cf_recs
            ])

        # 2. Trending content
        trending = self._get_trending_content(context.country, n=100)
        candidates.extend([
            (content_id, score, 'trending')
            for content_id, score in trending
        ])

        # 3. Continue watching (high priority)
        continue_watching = self._get_continue_watching(user_id, context.profile_id)
        candidates.extend([
            (content_id, 100.0, 'continue_watching')  # High score
            for content_id in continue_watching
        ])

        # 4. Similar to recently watched
        recent_watched = self._get_recent_watched(user_id, context.profile_id, n=5)
        for watched_id in recent_watched:
            similar = self._get_similar_content(watched_id, n=20)
            candidates.extend([
                (content_id, score, f'similar_to_{watched_id}')
                for content_id, score in similar
            ])

        # 5. New releases (filtered by preferences)
        new_releases = self._get_new_releases(context, n=50)
        candidates.extend([
            (content_id, score, 'new_release')
            for content_id, score in new_releases
        ])

        # Remove duplicates (keep highest score)
        unique_candidates = {}
        for content_id, score, source in candidates:
            if content_id not in unique_candidates or score > unique_candidates[content_id][0]:
                unique_candidates[content_id] = (score, source)

        # Convert back to list
        final_candidates = [
            (content_id, score, source)
            for content_id, (score, source) in unique_candidates.items()
        ]

        # Sort by score
        final_candidates.sort(key=lambda x: x[1], reverse=True)

        logger.info(f"Generated {len(final_candidates)} unique candidates")

        return final_candidates[:n_candidates]

    def rank_candidates(self, candidates: List[Tuple[int, float, str]],
                       user_id: int, context: UserContext) -> List[RecommendationResult]:
        """
        Rank candidates using ML ranking model

        Features for ranking:
        - Candidate score
        - User-content affinity
        - Content popularity
        - Recency
        - Time of day match
        - Device type compatibility
        - Business rules (promote Netflix originals)

        Returns:
            Ranked list of recommendations
        """
        logger.info(f"Ranking {len(candidates)} candidates")

        ranked = []

        for rank, (content_id, base_score, source) in enumerate(candidates):
            # Get content metadata
            content_meta = self._get_content_metadata(content_id)

            if not content_meta:
                continue

            # Calculate ranking features
            features = self._extract_ranking_features(
                user_id, content_id, base_score, source, context, content_meta
            )

            # Apply ranking model (simplified - in production use LambdaMART/XGBoost)
            final_score = self._calculate_final_score(features)

            # Create recommendation
            reason = self._generate_reason(source, content_meta)

            ranked.append(RecommendationResult(
                content_id=content_id,
                title=content_meta.get('title', f'Content {content_id}'),
                score=final_score,
                reason=reason,
                rank=0  # Will be set after sorting
            ))

        # Sort by final score
        ranked.sort(key=lambda x: x.score, reverse=True)

        # Set ranks
        for rank, rec in enumerate(ranked):
            rec.rank = rank + 1

        logger.info(f"Ranking complete, top item: {ranked[0].title if ranked else 'None'}")

        return ranked

    def recommend(self, user_id: int, context: UserContext,
                  n: int = 20) -> List[RecommendationResult]:
        """
        End-to-end recommendation

        Args:
            user_id: User ID
            context: User context
            n: Number of recommendations

        Returns:
            List of recommendations
        """
        logger.info(f"Generating recommendations for user {user_id}")

        # Generate candidates
        candidates = self.generate_candidates(user_id, context, n_candidates=500)

        # Rank candidates
        ranked = self.rank_candidates(candidates, user_id, context)

        # Diversification
        diversified = self._diversify_recommendations(ranked[:n * 2])

        # Apply business rules
        final = self._apply_business_rules(diversified, context)

        logger.info(f"Returning {len(final[:n])} recommendations")

        return final[:n]

    def _get_trending_content(self, country: str, n: int = 100) -> List[Tuple[int, float]]:
        """Get trending content with time decay"""
        # Placeholder: In production, query from real-time analytics
        # Time-decayed view count over last 7 days
        return [(i, 50.0 - i * 0.1) for i in range(1, n + 1)]

    def _get_continue_watching(self, user_id: int, profile_id: int) -> List[int]:
        """Get content user is currently watching"""
        # Placeholder: Query from database
        return []

    def _get_recent_watched(self, user_id: int, profile_id: int, n: int = 5) -> List[int]:
        """Get recently watched content"""
        # Placeholder: Query from viewing history
        return [101, 102, 103, 104, 105]

    def _get_similar_content(self, content_id: int, n: int = 20) -> List[Tuple[int, float]]:
        """Get similar content based on features"""
        # Placeholder: Use content-based similarity (genre, actors, etc.)
        return [(content_id + i, 40.0 - i) for i in range(1, n + 1)]

    def _get_new_releases(self, context: UserContext, n: int = 50) -> List[Tuple[int, float]]:
        """Get new releases filtered by user preferences"""
        # Placeholder: Query recent content matching user preferences
        return [(200 + i, 45.0 - i * 0.5) for i in range(n)]

    def _get_content_metadata(self, content_id: int) -> Optional[Dict]:
        """Get content metadata"""
        # Placeholder: Query from database
        return {
            'content_id': content_id,
            'title': f'Content {content_id}',
            'genres': ['Action', 'Drama'],
            'rating': 4.2,
            'duration_minutes': 120,
            'release_year': 2023,
            'netflix_original': content_id % 3 == 0
        }

    def _extract_ranking_features(self, user_id: int, content_id: int,
                                  base_score: float, source: str,
                                  context: UserContext,
                                  content_meta: Dict) -> Dict:
        """Extract features for ranking model"""
        return {
            'base_score': base_score,
            'content_rating': content_meta.get('rating', 3.0),
            'content_age_days': (datetime.now().year - content_meta.get('release_year', 2020)) * 365,
            'is_netflix_original': 1.0 if content_meta.get('netflix_original') else 0.0,
            'premium_tier': 1.0 if context.subscription_tier == 'premium' else 0.0,
            'source_is_personalized': 1.0 if source == 'personalized' else 0.0,
            'source_is_trending': 1.0 if source == 'trending' else 0.0,
        }

    def _calculate_final_score(self, features: Dict) -> float:
        """Calculate final ranking score"""
        # Simplified scoring (in production, use trained LambdaMART/XGBoost)
        score = (
            features['base_score'] * 0.5 +
            features['content_rating'] * 10.0 +
            features['is_netflix_original'] * 5.0 +
            features['source_is_personalized'] * 10.0 +
            features['source_is_trending'] * 3.0
        )
        return score

    def _generate_reason(self, source: str, content_meta: Dict) -> str:
        """Generate recommendation reason"""
        if source == 'continue_watching':
            return "Continue Watching"
        elif source == 'personalized':
            return "Top Picks for You"
        elif source == 'trending':
            return "Trending Now"
        elif source.startswith('similar_to'):
            return f"Because you watched..."
        elif source == 'new_release':
            return "New Release"
        else:
            return "Recommended"

    def _diversify_recommendations(self, recommendations: List[RecommendationResult]) -> List[RecommendationResult]:
        """Ensure genre diversity in recommendations"""
        # Placeholder: Implement MMR (Maximal Marginal Relevance) for diversity
        return recommendations

    def _apply_business_rules(self, recommendations: List[RecommendationResult],
                             context: UserContext) -> List[RecommendationResult]:
        """Apply business rules (e.g., promote Netflix originals)"""
        # Placeholder: Boost Netflix originals, filter by subscription tier
        return recommendations


# Example usage
if __name__ == '__main__':
    # Create sample interaction data
    np.random.seed(42)

    n_users = 1000
    n_items = 500
    n_interactions = 10000

    interactions = pd.DataFrame({
        'user_id': np.random.randint(1, n_users + 1, n_interactions),
        'content_id': np.random.randint(1, n_items + 1, n_interactions),
        'rating': np.random.uniform(3.0, 5.0, n_interactions)
    })

    # Initialize engine
    engine = RecommendationEngine()

    # Train collaborative filtering
    engine.train_collaborative_filtering(interactions)

    # Get recommendations
    user_context = UserContext(
        user_id=123,
        profile_id=456,
        age=30,
        gender='M',
        country='US',
        device_type='smart_tv',
        time_of_day='evening',
        subscription_tier='premium'
    )

    recommendations = engine.recommend(
        user_id=123,
        context=user_context,
        n=20
    )

    # Print results
    print("\n" + "="*80)
    print("RECOMMENDATIONS FOR USER 123")
    print("="*80)

    for rec in recommendations[:10]:
        print(f"{rec.rank}. {rec.title}")
        print(f"   Score: {rec.score:.2f} | {rec.reason}")
        print()
