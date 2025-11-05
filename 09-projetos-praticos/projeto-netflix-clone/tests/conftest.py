#!/usr/bin/env python3
"""
Netflix Clone - Pytest Configuration
====================================

Shared fixtures for all test modules.

Author: Data Engineering Study Project
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, MagicMock
import redis
import psycopg2
from datetime import datetime, timedelta
import json

# Test data directory
TEST_DATA_DIR = Path(__file__).parent / 'data'
TEST_DATA_DIR.mkdir(exist_ok=True)


@pytest.fixture(scope='session')
def test_data_dir():
    """Temporary directory for test data"""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_video_file(test_data_dir):
    """Create a sample video file for testing"""
    # Create a dummy video file (1 second, 720p)
    video_path = test_data_dir / 'sample_video.mp4'

    # Use FFmpeg to generate a test pattern video
    import subprocess

    cmd = [
        'ffmpeg', '-f', 'lavfi',
        '-i', 'testsrc=duration=1:size=1280x720:rate=30',
        '-f', 'lavfi',
        '-i', 'sine=frequency=1000:duration=1',
        '-pix_fmt', 'yuv420p',
        '-c:v', 'libx264', '-preset', 'ultrafast',
        '-c:a', 'aac',
        str(video_path),
        '-y'
    ]

    try:
        subprocess.run(cmd, check=True, capture_output=True)
    except subprocess.CalledProcessError:
        # If FFmpeg is not available, create a dummy file
        video_path.write_bytes(b'dummy video content')

    yield video_path


@pytest.fixture
def mock_s3_client():
    """Mock boto3 S3 client"""
    mock_client = MagicMock()

    # Mock upload_file
    mock_client.upload_file.return_value = None

    # Mock generate_presigned_url
    mock_client.generate_presigned_url.return_value = 'https://s3.amazonaws.com/test-bucket/test-key?signature=xyz'

    # Mock head_object
    mock_client.head_object.return_value = {
        'ContentLength': 1024 * 1024,  # 1 MB
        'LastModified': datetime.now()
    }

    # Mock list_objects_v2
    mock_client.list_objects_v2.return_value = {
        'Contents': [
            {'Key': 'test-key-1', 'Size': 1024},
            {'Key': 'test-key-2', 'Size': 2048}
        ]
    }

    return mock_client


@pytest.fixture
def mock_redis_client():
    """Mock Redis client"""
    mock_redis = MagicMock()

    # In-memory storage for testing
    storage = {}

    def mock_get(key):
        return storage.get(key)

    def mock_set(key, value, ex=None):
        storage[key] = value
        return True

    def mock_setex(key, time, value):
        storage[key] = value
        return True

    def mock_exists(key):
        return 1 if key in storage else 0

    def mock_delete(*keys):
        for key in keys:
            storage.pop(key, None)
        return len(keys)

    mock_redis.get.side_effect = mock_get
    mock_redis.set.side_effect = mock_set
    mock_redis.setex.side_effect = mock_setex
    mock_redis.exists.side_effect = mock_exists
    mock_redis.delete.side_effect = mock_delete

    return mock_redis


@pytest.fixture
def mock_postgres_conn():
    """Mock PostgreSQL connection"""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()

    # Mock cursor
    mock_conn.cursor.return_value = mock_cursor
    mock_cursor.fetchone.return_value = (1, 'test_user', 'test@example.com')
    mock_cursor.fetchall.return_value = [
        (1, 'test_user_1', 'test1@example.com'),
        (2, 'test_user_2', 'test2@example.com')
    ]

    return mock_conn


@pytest.fixture
def sample_playback_event():
    """Sample playback event for analytics testing"""
    return {
        'event_type': 'heartbeat',
        'user_id': 12345,
        'profile_id': 123450,
        'content_id': 1001,
        'session_id': 'session_test_123',
        'timestamp': int(datetime.now().timestamp() * 1000),
        'position_sec': 120.0,
        'bitrate_kbps': 5000,
        'resolution': '1080p',
        'buffer_health_sec': 15.0,
        'buffering_events': 0,
        'dropped_frames': 0,
        'device_type': 'smart_tv',
        'country': 'US',
        'cdn_pop': 'us-east-1a'
    }


@pytest.fixture
def sample_viewing_history():
    """Sample viewing history for recommendation testing"""
    return [
        {
            'user_id': 1,
            'content_id': 101,
            'watch_date': datetime.now() - timedelta(days=1),
            'watch_duration_sec': 3600,
            'completion_percentage': 0.8,
            'rating': 5
        },
        {
            'user_id': 1,
            'content_id': 102,
            'watch_date': datetime.now() - timedelta(days=2),
            'watch_duration_sec': 5400,
            'completion_percentage': 1.0,
            'rating': 4
        },
        {
            'user_id': 1,
            'content_id': 103,
            'watch_date': datetime.now() - timedelta(days=3),
            'watch_duration_sec': 1800,
            'completion_percentage': 0.3,
            'rating': 3
        }
    ]


@pytest.fixture
def sample_content_metadata():
    """Sample content metadata"""
    return [
        {
            'content_id': 101,
            'title': 'Test Movie 1',
            'type': 'movie',
            'genres': ['action', 'thriller'],
            'duration_sec': 7200,
            'release_year': 2023,
            'rating': 'PG-13'
        },
        {
            'content_id': 102,
            'title': 'Test Series 1',
            'type': 'series',
            'genres': ['drama', 'crime'],
            'duration_sec': 3600,
            'release_year': 2022,
            'rating': 'TV-MA'
        },
        {
            'content_id': 103,
            'title': 'Test Documentary 1',
            'type': 'documentary',
            'genres': ['documentary', 'nature'],
            'duration_sec': 5400,
            'release_year': 2021,
            'rating': 'TV-G'
        }
    ]


@pytest.fixture
def mock_kafka_producer():
    """Mock Kafka producer"""
    mock_producer = MagicMock()

    # Track sent messages
    sent_messages = []

    def mock_send(topic, value, key=None):
        sent_messages.append({
            'topic': topic,
            'value': value,
            'key': key
        })
        # Return a future-like object
        future = MagicMock()
        future.get.return_value = MagicMock(topic=topic, partition=0, offset=len(sent_messages))
        return future

    mock_producer.send.side_effect = mock_send
    mock_producer.sent_messages = sent_messages

    return mock_producer


@pytest.fixture
def mock_kafka_consumer():
    """Mock Kafka consumer"""
    mock_consumer = MagicMock()

    # Sample messages
    messages = [
        MagicMock(
            topic='video.playback.events',
            partition=0,
            offset=i,
            key=b'test_key',
            value=json.dumps({
                'event_type': 'heartbeat',
                'user_id': 1000 + i,
                'content_id': 100 + (i % 10),
                'session_id': f'session_{i}',
                'timestamp': int((datetime.now() + timedelta(seconds=i)).timestamp() * 1000),
                'position_sec': i * 30.0,
                'bitrate_kbps': 5000,
                'resolution': '1080p',
                'buffer_health_sec': 15.0,
                'buffering_events': 0,
                'dropped_frames': 0,
                'device_type': 'smart_tv',
                'country': 'US',
                'cdn_pop': 'us-east-1a'
            }).encode('utf-8')
        )
        for i in range(10)
    ]

    mock_consumer.__iter__.return_value = iter(messages)

    return mock_consumer


# Helper functions for tests

def assert_video_file_valid(file_path: Path):
    """Assert that a video file is valid"""
    assert file_path.exists(), f"Video file does not exist: {file_path}"
    assert file_path.stat().st_size > 0, f"Video file is empty: {file_path}"


def assert_m3u8_playlist_valid(playlist_path: Path):
    """Assert that an HLS playlist is valid"""
    assert playlist_path.exists(), f"Playlist does not exist: {playlist_path}"

    content = playlist_path.read_text()
    assert content.startswith('#EXTM3U'), "Invalid M3U8 header"
    assert '#EXT-X-VERSION' in content, "Missing M3U8 version"


def create_test_user(conn, user_id: int = 1):
    """Create a test user in database"""
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO users (user_id, email, username, created_at)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (user_id) DO NOTHING
    """, (user_id, f'test{user_id}@example.com', f'testuser{user_id}', datetime.now()))
    conn.commit()
    return user_id


def create_test_content(conn, content_id: int = 1):
    """Create test content in database"""
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO content (content_id, title, type, genres, duration_sec, release_year)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (content_id) DO NOTHING
    """, (content_id, f'Test Content {content_id}', 'movie', ['action'], 7200, 2023))
    conn.commit()
    return content_id
