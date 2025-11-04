#!/usr/bin/env python3
"""
Netflix Clone - Feature Store
==============================

Feature store para ML usando Feast ou implementação custom.

Features:
- User features (demographics, behavior, preferences)
- Content features (metadata, popularity, quality)
- Interaction features (watch history, ratings, time spent)
- Contextual features (time of day, device, location)

Storage:
- Online: Redis (low latency, real-time serving)
- Offline: S3/Data Lake (batch training)

Author: Data Engineering Study Project
"""

import json
import logging
import redis
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from collections import defaultdict

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class Feature:
    """Feature definition"""
    name: str
    dtype: str  # 'int', 'float', 'string', 'list'
    description: str
    ttl_seconds: Optional[int] = None  # Time-to-live for online features

    def to_dict(self):
        return asdict(self)


@dataclass
class FeatureView:
    """Collection of related features"""
    name: str
    entity_type: str  # 'user', 'content', 'user_content'
    features: List[Feature]
    online: bool = True  # Enable online serving
    offline: bool = True  # Enable offline storage

    def to_dict(self):
        return {
            'name': self.name,
            'entity_type': self.entity_type,
            'features': [f.to_dict() for f in self.features],
            'online': self.online,
            'offline': self.offline
        }


class FeatureStore:
    """
    Feature store for ML features

    Architecture:
    - Online Store: Redis (real-time serving)
    - Offline Store: S3/Data Lake (batch training)

    Features are organized by entity (user, content, etc.)
    """

    def __init__(self, redis_host: str = 'localhost',
                 redis_port: int = 6379,
                 redis_db: int = 0):
        """Initialize feature store"""
        self.redis_client = redis.Redis(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            decode_responses=True
        )

        self.feature_views: Dict[str, FeatureView] = {}

        logger.info("Feature Store initialized")

    def register_feature_view(self, view: FeatureView):
        """Register feature view"""
        self.feature_views[view.name] = view
        logger.info(f"Registered feature view: {view.name}")

    def _get_redis_key(self, entity_type: str, entity_id: int, feature_name: str) -> str:
        """Generate Redis key for feature"""
        return f"features:{entity_type}:{entity_id}:{feature_name}"

    def set_feature(self, entity_type: str, entity_id: int,
                    feature_name: str, value: Any,
                    ttl_seconds: Optional[int] = None):
        """
        Set feature value in online store

        Args:
            entity_type: 'user', 'content', etc.
            entity_id: Entity ID
            feature_name: Feature name
            value: Feature value
            ttl_seconds: Optional TTL (default: no expiration)
        """
        key = self._get_redis_key(entity_type, entity_id, feature_name)

        # Serialize value
        if isinstance(value, (list, dict)):
            value = json.dumps(value)
        else:
            value = str(value)

        # Set in Redis
        if ttl_seconds:
            self.redis_client.setex(key, ttl_seconds, value)
        else:
            self.redis_client.set(key, value)

    def get_feature(self, entity_type: str, entity_id: int,
                    feature_name: str) -> Optional[Any]:
        """Get feature value from online store"""
        key = self._get_redis_key(entity_type, entity_id, feature_name)
        value = self.redis_client.get(key)

        if value is None:
            return None

        # Deserialize
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value

    def get_online_features(self, entity_type: str, entity_id: int,
                           feature_names: List[str]) -> Dict[str, Any]:
        """
        Get multiple features for entity (batch)

        Args:
            entity_type: Entity type
            entity_id: Entity ID
            feature_names: List of feature names

        Returns:
            Dictionary of feature name -> value
        """
        features = {}

        for feature_name in feature_names:
            value = self.get_feature(entity_type, entity_id, feature_name)
            features[feature_name] = value

        return features

    def set_batch_features(self, entity_type: str, entity_id: int,
                          features: Dict[str, Any],
                          ttl_seconds: Optional[int] = None):
        """Set multiple features at once"""
        for feature_name, value in features.items():
            self.set_feature(entity_type, entity_id, feature_name, value, ttl_seconds)

    def delete_features(self, entity_type: str, entity_id: int):
        """Delete all features for entity"""
        pattern = f"features:{entity_type}:{entity_id}:*"
        keys = self.redis_client.keys(pattern)

        if keys:
            self.redis_client.delete(*keys)
            logger.info(f"Deleted {len(keys)} features for {entity_type} {entity_id}")


class UserFeatureGenerator:
    """Generate user features for recommendations"""

    def __init__(self, feature_store: FeatureStore):
        self.feature_store = feature_store

    def compute_user_features(self, user_id: int,
                             viewing_history: pd.DataFrame) -> Dict[str, Any]:
        """
        Compute user features from viewing history

        Features:
        - total_watch_hours
        - avg_session_duration
        - favorite_genres (top 3)
        - watch_time_of_day (morning, afternoon, evening, night)
        - completion_rate (% of content watched to completion)
        - binge_watching_score
        - days_since_signup
        - subscription_tier
        """
        features = {}

        # Total watch hours
        features['total_watch_hours'] = viewing_history['watch_duration_sec'].sum() / 3600

        # Average session duration
        sessions = viewing_history.groupby('session_id')['watch_duration_sec'].sum()
        features['avg_session_duration'] = sessions.mean() / 60  # minutes

        # Favorite genres (count by genre)
        genre_counts = defaultdict(int)
        for genres_str in viewing_history['genres'].dropna():
            for genre in genres_str.split(','):
                genre_counts[genre.strip()] += 1

        top_genres = sorted(genre_counts.items(), key=lambda x: x[1], reverse=True)[:3]
        features['favorite_genres'] = [genre for genre, _ in top_genres]

        # Watch time of day distribution
        time_of_day_counts = viewing_history['time_of_day'].value_counts()
        features['watch_time_distribution'] = time_of_day_counts.to_dict()

        # Completion rate
        completed = (viewing_history['watch_percentage'] >= 0.9).sum()
        total = len(viewing_history)
        features['completion_rate'] = completed / total if total > 0 else 0.0

        # Binge watching score (consecutive episodes in 24h)
        viewing_history = viewing_history.sort_values('started_at')
        binge_sessions = 0
        consecutive_episodes = 0

        for i in range(1, len(viewing_history)):
            prev = viewing_history.iloc[i - 1]
            curr = viewing_history.iloc[i]

            # Same series, within 24 hours
            if (prev['content_id'] == curr['content_id'] and
                (curr['started_at'] - prev['started_at']).total_seconds() < 86400):
                consecutive_episodes += 1
            else:
                if consecutive_episodes >= 3:  # 3+ episodes = binge session
                    binge_sessions += 1
                consecutive_episodes = 0

        features['binge_watching_score'] = binge_sessions

        # User profile features (placeholder - would come from user table)
        features['days_since_signup'] = 365  # Placeholder
        features['subscription_tier'] = 'premium'  # Placeholder

        return features

    def update_user_features(self, user_id: int, viewing_history: pd.DataFrame):
        """Compute and store user features"""
        features = self.compute_user_features(user_id, viewing_history)

        self.feature_store.set_batch_features(
            entity_type='user',
            entity_id=user_id,
            features=features,
            ttl_seconds=86400  # 24 hour TTL
        )

        logger.info(f"Updated features for user {user_id}")


class ContentFeatureGenerator:
    """Generate content features for recommendations"""

    def __init__(self, feature_store: FeatureStore):
        self.feature_store = feature_store

    def compute_content_features(self, content_id: int,
                                content_metadata: Dict,
                                viewing_stats: pd.DataFrame) -> Dict[str, Any]:
        """
        Compute content features

        Features:
        - view_count_7d (last 7 days)
        - view_count_30d (last 30 days)
        - view_count_all_time
        - avg_completion_rate
        - avg_rating
        - popularity_score (time-decayed)
        - trending_score
        - content_age_days
        - genres
        - duration_minutes
        - netflix_original
        """
        features = {}

        # View counts
        now = datetime.utcnow()
        views_7d = viewing_stats[viewing_stats['started_at'] >= now - timedelta(days=7)]
        views_30d = viewing_stats[viewing_stats['started_at'] >= now - timedelta(days=30)]

        features['view_count_7d'] = len(views_7d)
        features['view_count_30d'] = len(views_30d)
        features['view_count_all_time'] = len(viewing_stats)

        # Completion rate
        features['avg_completion_rate'] = viewing_stats['watch_percentage'].mean()

        # Rating
        features['avg_rating'] = viewing_stats['rating'].mean() if 'rating' in viewing_stats else 0.0

        # Popularity score (time-decayed)
        # More recent views have higher weight
        decay_factor = 0.9
        popularity = 0.0

        for i, row in views_7d.iterrows():
            days_ago = (now - row['started_at']).days
            weight = decay_factor ** days_ago
            popularity += weight

        features['popularity_score'] = popularity

        # Trending score (velocity of views)
        # Compare last 24h to previous 24h
        views_today = viewing_stats[viewing_stats['started_at'] >= now - timedelta(days=1)]
        views_yesterday = viewing_stats[
            (viewing_stats['started_at'] >= now - timedelta(days=2)) &
            (viewing_stats['started_at'] < now - timedelta(days=1))
        ]

        views_today_count = len(views_today)
        views_yesterday_count = len(views_yesterday)

        if views_yesterday_count > 0:
            features['trending_score'] = views_today_count / views_yesterday_count
        else:
            features['trending_score'] = views_today_count

        # Content metadata
        features['content_age_days'] = (
            datetime.utcnow() - content_metadata.get('release_date', datetime.utcnow())
        ).days

        features['genres'] = content_metadata.get('genres', [])
        features['duration_minutes'] = content_metadata.get('duration_minutes', 0)
        features['netflix_original'] = content_metadata.get('netflix_original', False)
        features['content_rating'] = content_metadata.get('content_rating', 'PG-13')

        return features

    def update_content_features(self, content_id: int,
                               content_metadata: Dict,
                               viewing_stats: pd.DataFrame):
        """Compute and store content features"""
        features = self.compute_content_features(content_id, content_metadata, viewing_stats)

        self.feature_store.set_batch_features(
            entity_type='content',
            entity_id=content_id,
            features=features,
            ttl_seconds=3600  # 1 hour TTL (updated frequently)
        )

        logger.info(f"Updated features for content {content_id}")


class InteractionFeatureGenerator:
    """Generate user-content interaction features"""

    def __init__(self, feature_store: FeatureStore):
        self.feature_store = feature_store

    def compute_interaction_features(self, user_id: int, content_id: int,
                                    user_history: pd.DataFrame) -> Dict[str, Any]:
        """
        Compute user-content interaction features

        Features:
        - has_watched (0/1)
        - watch_percentage (if watched)
        - days_since_watched
        - genre_affinity (user's affinity for content's genres)
        - similar_content_watched (count of similar content watched)
        """
        features = {}

        # Has watched?
        watched = user_history[user_history['content_id'] == content_id]
        features['has_watched'] = 1 if len(watched) > 0 else 0

        if len(watched) > 0:
            # Watch percentage
            features['watch_percentage'] = watched['watch_percentage'].max()

            # Days since watched
            last_watched = watched['started_at'].max()
            features['days_since_watched'] = (datetime.utcnow() - last_watched).days
        else:
            features['watch_percentage'] = 0.0
            features['days_since_watched'] = 9999

        # Genre affinity (placeholder - would compute from user's genre distribution)
        features['genre_affinity'] = 0.7  # Placeholder

        # Similar content watched (placeholder)
        features['similar_content_watched'] = 5  # Placeholder

        return features


# Define feature views
def create_feature_views() -> List[FeatureView]:
    """Create standard feature views"""

    user_features = FeatureView(
        name='user_features',
        entity_type='user',
        features=[
            Feature('total_watch_hours', 'float', 'Total hours watched'),
            Feature('avg_session_duration', 'float', 'Average session duration (minutes)'),
            Feature('favorite_genres', 'list', 'Top 3 favorite genres'),
            Feature('completion_rate', 'float', 'Percentage of content completed'),
            Feature('binge_watching_score', 'int', 'Number of binge watching sessions'),
            Feature('days_since_signup', 'int', 'Days since account creation'),
            Feature('subscription_tier', 'string', 'Subscription tier (basic/standard/premium)'),
        ],
        online=True,
        offline=True
    )

    content_features = FeatureView(
        name='content_features',
        entity_type='content',
        features=[
            Feature('view_count_7d', 'int', 'Views in last 7 days'),
            Feature('view_count_30d', 'int', 'Views in last 30 days'),
            Feature('avg_completion_rate', 'float', 'Average completion rate'),
            Feature('avg_rating', 'float', 'Average user rating'),
            Feature('popularity_score', 'float', 'Time-decayed popularity score'),
            Feature('trending_score', 'float', 'Trending score (24h velocity)'),
            Feature('content_age_days', 'int', 'Days since release'),
            Feature('genres', 'list', 'Content genres'),
            Feature('duration_minutes', 'int', 'Content duration in minutes'),
            Feature('netflix_original', 'int', 'Is Netflix Original (0/1)'),
        ],
        online=True,
        offline=True
    )

    interaction_features = FeatureView(
        name='interaction_features',
        entity_type='user_content',
        features=[
            Feature('has_watched', 'int', 'User has watched this content (0/1)'),
            Feature('watch_percentage', 'float', 'Percentage watched'),
            Feature('days_since_watched', 'int', 'Days since last watched'),
            Feature('genre_affinity', 'float', 'User affinity for content genres'),
            Feature('similar_content_watched', 'int', 'Count of similar content watched'),
        ],
        online=True,
        offline=True
    )

    return [user_features, content_features, interaction_features]


# Example usage
if __name__ == '__main__':
    # Initialize feature store
    feature_store = FeatureStore(
        redis_host='localhost',
        redis_port=6379
    )

    # Register feature views
    for view in create_feature_views():
        feature_store.register_feature_view(view)

    # Create sample viewing history
    viewing_history = pd.DataFrame({
        'user_id': [123] * 10,
        'content_id': range(1, 11),
        'session_id': ['session1', 'session1', 'session2'] + ['session3'] * 7,
        'started_at': pd.date_range(end=datetime.utcnow(), periods=10, freq='1D'),
        'watch_duration_sec': np.random.randint(1800, 7200, 10),
        'watch_percentage': np.random.uniform(0.5, 1.0, 10),
        'genres': ['Action,Drama'] * 10,
        'time_of_day': ['evening'] * 10,
        'rating': np.random.uniform(3.5, 5.0, 10)
    })

    # Generate user features
    user_gen = UserFeatureGenerator(feature_store)
    user_gen.update_user_features(user_id=123, viewing_history=viewing_history)

    # Retrieve user features
    user_features = feature_store.get_online_features(
        entity_type='user',
        entity_id=123,
        feature_names=['total_watch_hours', 'favorite_genres', 'completion_rate']
    )

    print("\n" + "="*60)
    print("USER FEATURES (user_id=123)")
    print("="*60)
    for feature, value in user_features.items():
        print(f"{feature:30} {value}")

    # Generate content features
    content_metadata = {
        'release_date': datetime.utcnow() - timedelta(days=30),
        'genres': ['Action', 'Thriller'],
        'duration_minutes': 120,
        'netflix_original': True,
        'content_rating': 'R'
    }

    content_viewing_stats = pd.DataFrame({
        'content_id': [1] * 100,
        'started_at': pd.date_range(end=datetime.utcnow(), periods=100, freq='1H'),
        'watch_percentage': np.random.uniform(0.6, 1.0, 100),
        'rating': np.random.uniform(3.0, 5.0, 100)
    })

    content_gen = ContentFeatureGenerator(feature_store)
    content_gen.update_content_features(
        content_id=1,
        content_metadata=content_metadata,
        viewing_stats=content_viewing_stats
    )

    # Retrieve content features
    content_features = feature_store.get_online_features(
        entity_type='content',
        entity_id=1,
        feature_names=['view_count_7d', 'popularity_score', 'trending_score']
    )

    print("\n" + "="*60)
    print("CONTENT FEATURES (content_id=1)")
    print("="*60)
    for feature, value in content_features.items():
        print(f"{feature:30} {value}")
    print("="*60 + "\n")
