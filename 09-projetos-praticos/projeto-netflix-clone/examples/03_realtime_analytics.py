#!/usr/bin/env python3
"""
Example 3: Real-time Analytics with Kafka
==========================================

This example demonstrates real-time video analytics:
1. Send playback events to Kafka
2. Process events in real-time
3. Calculate QoE metrics
4. Track concurrent viewers
5. Generate alerts

Author: Data Engineering Study Project
"""

import sys
from pathlib import Path
import logging
import json
import time
import random
from datetime import datetime
from threading import Thread

# Add project paths
sys.path.insert(0, str(Path(__file__).parent.parent / '07-analytics-metricas'))

from kafka_consumer import RealTimeAnalytics, SessionState, calculate_qoe_score

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def simulate_playback_session(producer, user_id, content_id, duration_min=5):
    """
    Simulate a single user's playback session

    Args:
        producer: Kafka producer
        user_id: User ID
        content_id: Content ID
        duration_min: Playback duration in minutes
    """
    from kafka import KafkaProducer

    session_id = f"session_{user_id}_{int(time.time())}"
    start_timestamp = int(time.time() * 1000)

    logger.info(f"[User {user_id}] Starting playback of content {content_id}")

    # 1. Send START event
    start_event = {
        'event_type': 'start',
        'user_id': user_id,
        'profile_id': user_id * 10,
        'content_id': content_id,
        'session_id': session_id,
        'timestamp': start_timestamp,
        'position_sec': 0.0,
        'bitrate_kbps': random.choice([3000, 5000, 8000]),
        'resolution': random.choice(['720p', '1080p', '4k']),
        'buffer_health_sec': 0.0,
        'buffering_events': 0,
        'dropped_frames': 0,
        'device_type': random.choice(['smart_tv', 'mobile', 'desktop']),
        'country': random.choice(['US', 'BR', 'UK']),
        'cdn_pop': random.choice(['us-east-1a', 'us-west-2b', 'eu-west-1a'])
    }

    producer.send('video.playback.events', value=start_event)
    logger.info(f"  → START event sent")

    # 2. Send HEARTBEAT events (every 30 seconds)
    heartbeat_interval = 30  # seconds
    total_heartbeats = int(duration_min * 60 / heartbeat_interval)

    buffering_events = 0
    dropped_frames = 0

    for i in range(total_heartbeats):
        time.sleep(heartbeat_interval)

        # Simulate occasional buffering
        if random.random() < 0.1:  # 10% chance
            buffering_events += 1
            buffer_health = random.uniform(0, 5)
            logger.info(f"  ⚠ Buffering occurred (total: {buffering_events})")
        else:
            buffer_health = random.uniform(10, 20)

        # Simulate occasional frame drops
        if random.random() < 0.15:  # 15% chance
            dropped_frames += random.randint(1, 5)

        heartbeat_event = {
            'event_type': 'heartbeat',
            'user_id': user_id,
            'profile_id': user_id * 10,
            'content_id': content_id,
            'session_id': session_id,
            'timestamp': int(time.time() * 1000),
            'position_sec': (i + 1) * heartbeat_interval,
            'bitrate_kbps': random.randint(4000, 8000),
            'resolution': start_event['resolution'],
            'buffer_health_sec': buffer_health,
            'buffering_events': buffering_events,
            'dropped_frames': dropped_frames,
            'device_type': start_event['device_type'],
            'country': start_event['country'],
            'cdn_pop': start_event['cdn_pop']
        }

        producer.send('video.playback.events', value=heartbeat_event)

        if (i + 1) % 5 == 0:
            progress = (i + 1) * heartbeat_interval / 60
            logger.info(f"  [User {user_id}] Progress: {progress:.1f} min")

    # 3. Send STOP event
    stop_event = {
        'event_type': 'stop',
        'user_id': user_id,
        'profile_id': user_id * 10,
        'content_id': content_id,
        'session_id': session_id,
        'timestamp': int(time.time() * 1000),
        'position_sec': total_heartbeats * heartbeat_interval,
        'bitrate_kbps': start_event['bitrate_kbps'],
        'resolution': start_event['resolution'],
        'buffer_health_sec': random.uniform(10, 20),
        'buffering_events': buffering_events,
        'dropped_frames': dropped_frames,
        'device_type': start_event['device_type'],
        'country': start_event['country'],
        'cdn_pop': start_event['cdn_pop']
    }

    producer.send('video.playback.events', value=stop_event)
    producer.flush()

    logger.info(f"  → STOP event sent")
    logger.info(f"[User {user_id}] Session completed ({duration_min} min)")


def main():
    """
    Real-time analytics demonstration
    """

    # =====================
    # Configuration
    # =====================

    KAFKA_BOOTSTRAP_SERVERS = 'localhost:9092'
    REDIS_HOST = 'localhost'
    POSTGRES_CONN_STR = 'postgresql://netflix:netflix123@localhost:5432/netflix'

    # =====================
    # Step 1: Initialize Kafka Producer
    # =====================

    logger.info("=" * 60)
    logger.info("STEP 1: Initializing Kafka producer")
    logger.info("=" * 60)

    try:
        from kafka import KafkaProducer

        producer = KafkaProducer(
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            acks='all'  # Wait for all replicas
        )

        logger.info("✓ Kafka producer initialized")

    except Exception as e:
        logger.error(f"✗ Failed to initialize Kafka producer: {e}")
        logger.info("\nMake sure Kafka is running:")
        logger.info("  docker-compose up -d kafka")
        return

    # =====================
    # Step 2: Initialize Analytics Consumer
    # =====================

    logger.info("\n" + "=" * 60)
    logger.info("STEP 2: Initializing real-time analytics consumer")
    logger.info("=" * 60)

    try:
        analytics = RealTimeAnalytics(
            kafka_bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            redis_host=REDIS_HOST,
            postgres_conn_str=POSTGRES_CONN_STR
        )

        logger.info("✓ Analytics consumer initialized")

        # Start consumer in background thread
        consumer_thread = Thread(target=analytics.run, daemon=True)
        consumer_thread.start()

        logger.info("✓ Consumer thread started")

        # Give consumer time to connect
        time.sleep(2)

    except Exception as e:
        logger.error(f"✗ Failed to initialize analytics consumer: {e}")
        logger.info("\nMake sure services are running:")
        logger.info("  docker-compose up -d kafka redis postgres")
        return

    # =====================
    # Step 3: Simulate Playback Sessions
    # =====================

    logger.info("\n" + "=" * 60)
    logger.info("STEP 3: Simulating playback sessions")
    logger.info("=" * 60)

    # Simulate 5 concurrent users watching different content
    content_library = [101, 102, 103, 104, 105]

    logger.info("\nStarting 5 concurrent playback sessions...")
    logger.info("(This will take ~5 minutes)\n")

    threads = []

    for user_id in range(1, 6):
        content_id = random.choice(content_library)
        duration = random.randint(3, 7)  # 3-7 minutes

        thread = Thread(
            target=simulate_playback_session,
            args=(producer, user_id, content_id, duration),
            daemon=True
        )

        thread.start()
        threads.append(thread)

        # Stagger starts
        time.sleep(2)

    # =====================
    # Step 4: Monitor Metrics
    # =====================

    logger.info("\n" + "=" * 60)
    logger.info("STEP 4: Monitoring real-time metrics")
    logger.info("=" * 60)

    try:
        import redis

        redis_client = redis.Redis(host=REDIS_HOST, decode_responses=True)

        logger.info("\nMonitoring concurrent viewers (updating every 10s)...")
        logger.info("Press Ctrl+C to stop\n")

        monitor_duration = 300  # 5 minutes
        start_time = time.time()

        while time.time() - start_time < monitor_duration:
            time.sleep(10)

            logger.info("-" * 60)
            logger.info(f"Metrics at {datetime.now().strftime('%H:%M:%S')}:")
            logger.info("-" * 60)

            # Get concurrent viewers for each content
            for content_id in content_library:
                key = f'metrics:content:{content_id}:concurrent_viewers'
                viewers = redis_client.get(key)

                if viewers:
                    logger.info(f"  Content {content_id}: {viewers} concurrent viewers")

                    # Get QoE score
                    qoe_key = f'metrics:content:{content_id}:qoe_score'
                    qoe_score = redis_client.get(qoe_key)

                    if qoe_score:
                        qoe_float = float(qoe_score)
                        logger.info(f"    QoE Score: {qoe_float:.1f}/100")

                        if qoe_float < 70:
                            logger.warning(f"    ⚠ LOW QoE SCORE!")
                        else:
                            logger.info(f"    ✓ Good quality")

            logger.info("")

        # Wait for all sessions to complete
        logger.info("Waiting for all sessions to complete...")
        for thread in threads:
            thread.join(timeout=60)

    except KeyboardInterrupt:
        logger.info("\n\nMonitoring interrupted by user")

    except Exception as e:
        logger.error(f"Error during monitoring: {e}")

    # =====================
    # Step 5: Query Analytics Results
    # =====================

    logger.info("\n" + "=" * 60)
    logger.info("STEP 5: Querying analytics results from PostgreSQL")
    logger.info("=" * 60)

    try:
        import psycopg2

        conn = psycopg2.connect(POSTGRES_CONN_STR)
        cursor = conn.cursor()

        # Query session statistics
        cursor.execute("""
            SELECT
                content_id,
                COUNT(*) as session_count,
                AVG(watch_duration_sec) as avg_duration,
                AVG(buffering_events) as avg_buffering,
                AVG(qoe_score) as avg_qoe
            FROM playback_sessions
            WHERE created_at >= NOW() - INTERVAL '1 hour'
            GROUP BY content_id
            ORDER BY session_count DESC
        """)

        results = cursor.fetchall()

        if results:
            logger.info("\n✓ Session statistics (last hour):\n")
            logger.info(f"{'Content ID':<12} {'Sessions':<10} {'Avg Duration':<15} {'Avg Buffering':<15} {'Avg QoE':<10}")
            logger.info("-" * 70)

            for row in results:
                content_id, session_count, avg_duration, avg_buffering, avg_qoe = row
                logger.info(
                    f"{content_id:<12} {session_count:<10} "
                    f"{avg_duration/60:.1f} min{'':<7} "
                    f"{avg_buffering:.2f}{'':<12} "
                    f"{avg_qoe:.1f}/100"
                )
        else:
            logger.info("\n(No session data found)")

        cursor.close()
        conn.close()

    except Exception as e:
        logger.error(f"Error querying PostgreSQL: {e}")

    # =====================
    # Step 6: Generate Alerts
    # =====================

    logger.info("\n" + "=" * 60)
    logger.info("STEP 6: Alert examples")
    logger.info("=" * 60)

    logger.info("\nIn production, alerts would be sent to:")
    logger.info("  - Slack: #alerts-qoe channel")
    logger.info("  - PagerDuty: For critical issues")
    logger.info("  - Datadog: For monitoring dashboards")

    logger.info("\nAlert triggers:")
    logger.info("  ✓ QoE score < 70 → Warning")
    logger.info("  ✓ Rebuffering ratio > 2% → Critical")
    logger.info("  ✓ VST p95 > 3000ms → Warning")
    logger.info("  ✓ Concurrent viewers drop >50% → Critical")

    # =====================
    # Summary
    # =====================

    logger.info("\n" + "=" * 60)
    logger.info("REAL-TIME ANALYTICS DEMO COMPLETED!")
    logger.info("=" * 60)

    logger.info("\nWhat we demonstrated:")
    logger.info("  ✓ Sent playback events to Kafka")
    logger.info("  ✓ Processed events in real-time")
    logger.info("  ✓ Calculated QoE scores")
    logger.info("  ✓ Tracked concurrent viewers")
    logger.info("  ✓ Stored session data in PostgreSQL")
    logger.info("  ✓ Published metrics to Redis")

    logger.info("\nIn production:")
    logger.info("  - Scale to 1M+ events/minute")
    logger.info("  - Use Apache Flink for complex analytics")
    logger.info("  - Store time-series data in Cassandra")
    logger.info("  - Build Grafana dashboards")
    logger.info("  - Set up automated alerting")

    # Cleanup
    producer.close()
    logger.info("\n✓ Kafka producer closed")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\n\nDemo interrupted by user")
    except Exception as e:
        logger.error(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()
