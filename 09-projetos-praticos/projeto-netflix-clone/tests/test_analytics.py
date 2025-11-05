#!/usr/bin/env python3
"""
Netflix Clone - Real-time Analytics Tests
=========================================

Unit tests for real-time analytics processing.

Author: Data Engineering Study Project
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import json
from datetime import datetime, timedelta
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / '07-analytics-metricas'))

from kafka_consumer import (
    RealTimeAnalytics,
    SessionState,
    calculate_qoe_score
)


class TestSessionState:
    """Test SessionState dataclass"""

    def test_session_creation(self):
        """Test creating a session state"""
        session = SessionState(
            user_id=1,
            profile_id=10,
            content_id=100,
            started_at=int(datetime.now().timestamp() * 1000)
        )

        assert session.user_id == 1
        assert session.profile_id == 10
        assert session.content_id == 100
        assert session.position_sec == 0.0
        assert session.buffering_events == 0

    def test_session_update(self):
        """Test updating session state"""
        session = SessionState(
            user_id=1,
            profile_id=10,
            content_id=100,
            started_at=int(datetime.now().timestamp() * 1000)
        )

        # Update playback position
        session.position_sec = 120.0
        session.buffering_events = 2
        session.bitrate_kbps = 5000

        assert session.position_sec == 120.0
        assert session.buffering_events == 2
        assert session.bitrate_kbps == 5000


class TestQoECalculation:
    """Test QoE score calculation"""

    def test_perfect_qoe_score(self):
        """Test QoE score for perfect playback"""
        score = calculate_qoe_score(
            vst_ms=500,  # Very fast start
            rebuffering_ratio=0.0,  # No rebuffering
            avg_bitrate_kbps=6000,  # High bitrate
            avg_buffer_health=20.0  # Healthy buffer
        )

        # Should be close to 100
        assert 95 <= score <= 100

    def test_poor_qoe_score(self):
        """Test QoE score for poor playback"""
        score = calculate_qoe_score(
            vst_ms=5000,  # Slow start
            rebuffering_ratio=0.05,  # 5% rebuffering
            avg_bitrate_kbps=1000,  # Low bitrate
            avg_buffer_health=2.0  # Poor buffer
        )

        # Should be low
        assert score < 50

    def test_qoe_score_bounds(self):
        """Test that QoE score is always 0-100"""
        # Extreme bad case
        score = calculate_qoe_score(
            vst_ms=30000,  # 30 seconds
            rebuffering_ratio=0.5,  # 50% rebuffering
            avg_bitrate_kbps=100,
            avg_buffer_health=0.5
        )

        assert 0 <= score <= 100


class TestRealTimeAnalytics:
    """Test RealTimeAnalytics class"""

    @patch('kafka.KafkaConsumer')
    @patch('redis.Redis')
    @patch('psycopg2.connect')
    def test_initialization(self, mock_pg, mock_redis, mock_kafka):
        """Test analytics initialization"""
        analytics = RealTimeAnalytics(
            kafka_bootstrap_servers='localhost:9092',
            redis_host='localhost',
            postgres_conn_str='postgresql://localhost/netflix'
        )

        assert analytics.consumer is not None
        assert analytics.redis_client is not None
        assert analytics.postgres_conn is not None
        assert len(analytics.active_sessions) == 0

    @patch('kafka.KafkaConsumer')
    @patch('redis.Redis')
    @patch('psycopg2.connect')
    def test_handle_start_event(self, mock_pg, mock_redis, mock_kafka):
        """Test handling playback start event"""
        analytics = RealTimeAnalytics(
            kafka_bootstrap_servers='localhost:9092',
            redis_host='localhost',
            postgres_conn_str='postgresql://localhost/netflix'
        )

        event = {
            'event_type': 'start',
            'user_id': 1,
            'profile_id': 10,
            'content_id': 100,
            'session_id': 'session_123',
            'timestamp': int(datetime.now().timestamp() * 1000),
            'position_sec': 0.0,
            'bitrate_kbps': 5000,
            'resolution': '1080p',
            'buffer_health_sec': 0.0,
            'buffering_events': 0,
            'dropped_frames': 0,
            'device_type': 'smart_tv',
            'country': 'US',
            'cdn_pop': 'us-east-1a'
        }

        analytics._handle_start_event(event)

        # Session should be created
        assert 'session_123' in analytics.active_sessions
        session = analytics.active_sessions['session_123']
        assert session.user_id == 1
        assert session.content_id == 100

        # Concurrent viewers should be incremented
        content_metrics = analytics.content_metrics[100]
        assert content_metrics['concurrent_viewers'] == 1

    @patch('kafka.KafkaConsumer')
    @patch('redis.Redis')
    @patch('psycopg2.connect')
    def test_handle_heartbeat_event(self, mock_pg, mock_redis, mock_kafka):
        """Test handling heartbeat event"""
        analytics = RealTimeAnalytics(
            kafka_bootstrap_servers='localhost:9092',
            redis_host='localhost',
            postgres_conn_str='postgresql://localhost/netflix'
        )

        # Create session first
        session_id = 'session_123'
        analytics.active_sessions[session_id] = SessionState(
            user_id=1,
            profile_id=10,
            content_id=100,
            started_at=int(datetime.now().timestamp() * 1000)
        )

        # Heartbeat after 30 seconds
        event = {
            'event_type': 'heartbeat',
            'session_id': session_id,
            'timestamp': int((datetime.now() + timedelta(seconds=30)).timestamp() * 1000),
            'position_sec': 30.0,
            'bitrate_kbps': 5000,
            'buffer_health_sec': 15.0,
            'buffering_events': 0,
            'dropped_frames': 0
        }

        analytics._handle_heartbeat_event(event)

        # Session should be updated
        session = analytics.active_sessions[session_id]
        assert session.position_sec == 30.0
        assert session.bitrate_kbps == 5000

        # VST should be calculated (time to first buffer)
        assert session.vst_ms is not None
        assert session.vst_ms > 0

    @patch('kafka.KafkaConsumer')
    @patch('redis.Redis')
    @patch('psycopg2.connect')
    def test_handle_stop_event(self, mock_pg, mock_redis, mock_kafka):
        """Test handling playback stop event"""
        mock_redis_client = MagicMock()
        mock_redis.return_value = mock_redis_client

        analytics = RealTimeAnalytics(
            kafka_bootstrap_servers='localhost:9092',
            redis_host='localhost',
            postgres_conn_str='postgresql://localhost/netflix'
        )

        # Create session
        session_id = 'session_123'
        start_time = int(datetime.now().timestamp() * 1000)

        analytics.active_sessions[session_id] = SessionState(
            user_id=1,
            profile_id=10,
            content_id=100,
            started_at=start_time
        )

        analytics.content_metrics[100]['concurrent_viewers'] = 1

        # Stop event
        event = {
            'event_type': 'stop',
            'session_id': session_id,
            'user_id': 1,
            'content_id': 100,
            'timestamp': start_time + 120000,  # 2 minutes later
            'position_sec': 120.0,
            'bitrate_kbps': 5000,
            'buffer_health_sec': 15.0,
            'buffering_events': 1,
            'dropped_frames': 3
        }

        analytics._handle_stop_event(event)

        # Session should be removed
        assert session_id not in analytics.active_sessions

        # Concurrent viewers should be decremented
        assert analytics.content_metrics[100]['concurrent_viewers'] == 0

    @patch('kafka.KafkaConsumer')
    @patch('redis.Redis')
    @patch('psycopg2.connect')
    def test_handle_buffering_event(self, mock_pg, mock_redis, mock_kafka):
        """Test handling buffering event"""
        analytics = RealTimeAnalytics(
            kafka_bootstrap_servers='localhost:9092',
            redis_host='localhost',
            postgres_conn_str='postgresql://localhost/netflix'
        )

        # Create session
        session_id = 'session_123'
        analytics.active_sessions[session_id] = SessionState(
            user_id=1,
            profile_id=10,
            content_id=100,
            started_at=int(datetime.now().timestamp() * 1000)
        )

        # Buffering event
        event = {
            'event_type': 'buffering',
            'session_id': session_id,
            'timestamp': int(datetime.now().timestamp() * 1000),
            'buffering_events': 2
        }

        analytics._handle_buffering_event(event)

        # Buffering count should be updated
        session = analytics.active_sessions[session_id]
        assert session.buffering_events == 2

    @patch('kafka.KafkaConsumer')
    @patch('redis.Redis')
    @patch('psycopg2.connect')
    def test_calculate_session_qoe(self, mock_pg, mock_redis, mock_kafka):
        """Test calculating QoE for a session"""
        analytics = RealTimeAnalytics(
            kafka_bootstrap_servers='localhost:9092',
            redis_host='localhost',
            postgres_conn_str='postgresql://localhost/netflix'
        )

        # Create session with metrics
        session = SessionState(
            user_id=1,
            profile_id=10,
            content_id=100,
            started_at=int(datetime.now().timestamp() * 1000)
        )

        session.vst_ms = 800  # Fast start
        session.bitrate_kbps = 5000  # Good bitrate
        session.buffer_health_sec = 15.0  # Healthy buffer
        session.buffering_events = 0  # No buffering
        session.position_sec = 120.0  # 2 minutes watched

        qoe_score = analytics._calculate_qoe_score(session)

        # Should be high score
        assert qoe_score > 85

    @patch('kafka.KafkaConsumer')
    @patch('redis.Redis')
    @patch('psycopg2.connect')
    def test_publish_metrics_to_redis(self, mock_pg, mock_redis, mock_kafka):
        """Test publishing metrics to Redis"""
        mock_redis_client = MagicMock()
        mock_redis.return_value = mock_redis_client

        analytics = RealTimeAnalytics(
            kafka_bootstrap_servers='localhost:9092',
            redis_host='localhost',
            postgres_conn_str='postgresql://localhost/netflix'
        )

        # Set content metrics
        analytics.content_metrics[100] = {
            'concurrent_viewers': 1500,
            'avg_vst_ms': 650,
            'qoe_score': 92.5
        }

        analytics._publish_metrics_to_redis(content_id=100)

        # Verify Redis setex was called
        assert mock_redis_client.setex.call_count >= 3  # One per metric

    @patch('kafka.KafkaConsumer')
    @patch('redis.Redis')
    @patch('psycopg2.connect')
    def test_save_session_to_postgres(self, mock_pg, mock_redis, mock_kafka):
        """Test saving session data to PostgreSQL"""
        mock_cursor = MagicMock()
        mock_pg.return_value.cursor.return_value = mock_cursor

        analytics = RealTimeAnalytics(
            kafka_bootstrap_servers='localhost:9092',
            redis_host='localhost',
            postgres_conn_str='postgresql://localhost/netflix'
        )

        session = SessionState(
            user_id=1,
            profile_id=10,
            content_id=100,
            started_at=int(datetime.now().timestamp() * 1000)
        )

        session.position_sec = 120.0
        session.vst_ms = 750
        session.buffering_events = 1

        analytics._save_session_to_postgres('session_123', session)

        # Verify INSERT was executed
        mock_cursor.execute.assert_called_once()
        sql = mock_cursor.execute.call_args[0][0]
        assert 'INSERT INTO' in sql or 'insert into' in sql.lower()

    @patch('kafka.KafkaConsumer')
    @patch('redis.Redis')
    @patch('psycopg2.connect')
    def test_cleanup_stale_sessions(self, mock_pg, mock_redis, mock_kafka):
        """Test cleaning up stale sessions"""
        analytics = RealTimeAnalytics(
            kafka_bootstrap_servers='localhost:9092',
            redis_host='localhost',
            postgres_conn_str='postgresql://localhost/netflix'
        )

        # Create old session (2 hours ago)
        old_session_id = 'old_session'
        analytics.active_sessions[old_session_id] = SessionState(
            user_id=1,
            profile_id=10,
            content_id=100,
            started_at=int((datetime.now() - timedelta(hours=2)).timestamp() * 1000)
        )

        # Create recent session
        recent_session_id = 'recent_session'
        analytics.active_sessions[recent_session_id] = SessionState(
            user_id=2,
            profile_id=20,
            content_id=200,
            started_at=int(datetime.now().timestamp() * 1000)
        )

        analytics._cleanup_stale_sessions()

        # Old session should be removed
        assert old_session_id not in analytics.active_sessions

        # Recent session should remain
        assert recent_session_id in analytics.active_sessions


class TestAnalyticsIntegration:
    """Integration tests for analytics pipeline"""

    @patch('kafka.KafkaConsumer')
    @patch('redis.Redis')
    @patch('psycopg2.connect')
    def test_full_session_lifecycle(self, mock_pg, mock_redis, mock_kafka):
        """Test complete session from start to stop"""
        mock_redis_client = MagicMock()
        mock_redis.return_value = mock_redis_client

        analytics = RealTimeAnalytics(
            kafka_bootstrap_servers='localhost:9092',
            redis_host='localhost',
            postgres_conn_str='postgresql://localhost/netflix'
        )

        session_id = 'test_session'
        start_time = int(datetime.now().timestamp() * 1000)

        # 1. Start event
        start_event = {
            'event_type': 'start',
            'user_id': 1,
            'profile_id': 10,
            'content_id': 100,
            'session_id': session_id,
            'timestamp': start_time,
            'position_sec': 0.0,
            'bitrate_kbps': 5000,
            'resolution': '1080p',
            'buffer_health_sec': 0.0,
            'buffering_events': 0,
            'dropped_frames': 0,
            'device_type': 'smart_tv',
            'country': 'US',
            'cdn_pop': 'us-east-1a'
        }

        analytics._handle_start_event(start_event)
        assert session_id in analytics.active_sessions

        # 2. Multiple heartbeat events
        for i in range(1, 5):
            heartbeat_event = {
                'event_type': 'heartbeat',
                'session_id': session_id,
                'timestamp': start_time + (i * 30000),  # Every 30 seconds
                'position_sec': i * 30.0,
                'bitrate_kbps': 5000,
                'buffer_health_sec': 15.0,
                'buffering_events': 0,
                'dropped_frames': 0
            }
            analytics._handle_heartbeat_event(heartbeat_event)

        # Session should be updated
        session = analytics.active_sessions[session_id]
        assert session.position_sec == 120.0  # 4 heartbeats * 30s

        # 3. Stop event
        stop_event = {
            'event_type': 'stop',
            'session_id': session_id,
            'user_id': 1,
            'content_id': 100,
            'timestamp': start_time + 120000,
            'position_sec': 120.0,
            'bitrate_kbps': 5000,
            'buffer_health_sec': 15.0,
            'buffering_events': 0,
            'dropped_frames': 0
        }

        analytics._handle_stop_event(stop_event)

        # Session should be removed
        assert session_id not in analytics.active_sessions

    @patch('kafka.KafkaConsumer')
    @patch('redis.Redis')
    @patch('psycopg2.connect')
    def test_concurrent_viewers_accuracy(self, mock_pg, mock_redis, mock_kafka):
        """Test concurrent viewer counting"""
        analytics = RealTimeAnalytics(
            kafka_bootstrap_servers='localhost:9092',
            redis_host='localhost',
            postgres_conn_str='postgresql://localhost/netflix'
        )

        content_id = 100
        timestamp = int(datetime.now().timestamp() * 1000)

        # Start 5 sessions for same content
        for i in range(5):
            event = {
                'event_type': 'start',
                'user_id': i,
                'profile_id': i * 10,
                'content_id': content_id,
                'session_id': f'session_{i}',
                'timestamp': timestamp,
                'position_sec': 0.0,
                'bitrate_kbps': 5000,
                'resolution': '1080p',
                'buffer_health_sec': 0.0,
                'buffering_events': 0,
                'dropped_frames': 0,
                'device_type': 'smart_tv',
                'country': 'US',
                'cdn_pop': 'us-east-1a'
            }
            analytics._handle_start_event(event)

        # Should have 5 concurrent viewers
        assert analytics.content_metrics[content_id]['concurrent_viewers'] == 5

        # Stop 2 sessions
        for i in range(2):
            event = {
                'event_type': 'stop',
                'session_id': f'session_{i}',
                'user_id': i,
                'content_id': content_id,
                'timestamp': timestamp + 60000,
                'position_sec': 60.0,
                'bitrate_kbps': 5000,
                'buffer_health_sec': 15.0,
                'buffering_events': 0,
                'dropped_frames': 0
            }
            analytics._handle_stop_event(event)

        # Should have 3 concurrent viewers now
        assert analytics.content_metrics[content_id]['concurrent_viewers'] == 3


# Pytest configuration

def pytest_configure(config):
    """Add custom markers"""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "performance: mark test as performance test"
    )
