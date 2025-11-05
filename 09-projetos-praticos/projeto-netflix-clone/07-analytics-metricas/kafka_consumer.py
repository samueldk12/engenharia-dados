#!/usr/bin/env python3
"""
Netflix Clone - Kafka Consumer for Analytics
=============================================

Consome eventos de playback do Kafka e processa métricas em tempo real.

Alternativa mais simples ao Flink para ambientes menores.

Events consumed:
- video.playback.events (all playback events)

Metrics calculated:
- Concurrent viewers
- Video Start Time (VST)
- Rebuffering events
- Quality metrics

Output:
- Redis (real-time metrics)
- PostgreSQL (aggregated metrics)
- Logs (debugging)

Author: Data Engineering Study Project
"""

from kafka import KafkaConsumer
import redis
import psycopg2
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from collections import defaultdict
import statistics
import time
from threading import Thread, Lock

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class SessionState:
    """State for active playback session"""
    session_id: str
    user_id: int
    profile_id: int
    content_id: int
    device_type: str
    country: str

    # Timestamps
    started_at: datetime
    last_heartbeat_at: datetime

    # Playback metrics
    current_position_sec: float
    max_position_sec: float
    bitrates: List[int]
    buffering_events: int
    dropped_frames: int

    # Quality metrics
    vst_ms: Optional[int] = None  # Video Start Time

    def to_dict(self):
        return asdict(self)


class RealTimeAnalytics:
    """
    Real-time analytics engine consuming from Kafka

    Maintains in-memory state of active sessions
    Calculates metrics in real-time
    Publishes to Redis for dashboards
    """

    def __init__(self, kafka_bootstrap_servers: str = 'localhost:9092',
                 redis_host: str = 'localhost',
                 redis_port: int = 6379,
                 postgres_conn_str: str = None):
        """
        Initialize analytics engine

        Args:
            kafka_bootstrap_servers: Kafka bootstrap servers
            redis_host: Redis host for real-time metrics
            redis_port: Redis port
            postgres_conn_str: PostgreSQL connection string
        """
        # Kafka consumer
        self.consumer = KafkaConsumer(
            'video.playback.events',
            bootstrap_servers=kafka_bootstrap_servers,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            group_id='analytics-consumer',
            auto_offset_reset='latest',
            enable_auto_commit=True
        )

        # Redis for real-time metrics
        self.redis_client = redis.Redis(
            host=redis_host,
            port=redis_port,
            decode_responses=True
        )

        # PostgreSQL for aggregated metrics
        self.postgres_conn_str = postgres_conn_str

        # In-memory state
        self.active_sessions: Dict[str, SessionState] = {}
        self.state_lock = Lock()

        # Metrics cache
        self.content_metrics: Dict[int, Dict] = defaultdict(lambda: {
            'concurrent_viewers': 0,
            'total_views_today': 0,
            'avg_vst_ms': 0,
            'rebuffering_events': 0,
            'qoe_score': 100.0
        })

        logger.info("Real-time Analytics initialized")

    def process_event(self, event: Dict):
        """Process single playback event"""
        event_type = event['event_type']

        if event_type == 'start':
            self._handle_start_event(event)
        elif event_type == 'heartbeat':
            self._handle_heartbeat_event(event)
        elif event_type == 'stop':
            self._handle_stop_event(event)
        elif event_type == 'buffering':
            self._handle_buffering_event(event)
        elif event_type == 'error':
            self._handle_error_event(event)

    def _handle_start_event(self, event: Dict):
        """Handle playback start event"""
        session_id = event['session_id']

        with self.state_lock:
            # Create session state
            self.active_sessions[session_id] = SessionState(
                session_id=session_id,
                user_id=event['user_id'],
                profile_id=event['profile_id'],
                content_id=event['content_id'],
                device_type=event['device_type'],
                country=event['country'],
                started_at=datetime.fromtimestamp(event['timestamp'] / 1000),
                last_heartbeat_at=datetime.fromtimestamp(event['timestamp'] / 1000),
                current_position_sec=event['position_sec'],
                max_position_sec=event['position_sec'],
                bitrates=[event['bitrate_kbps']],
                buffering_events=event['buffering_events'],
                dropped_frames=event['dropped_frames']
            )

            # Increment concurrent viewers
            content_id = event['content_id']
            self.content_metrics[content_id]['concurrent_viewers'] += 1
            self.content_metrics[content_id]['total_views_today'] += 1

        # Publish to Redis
        self._publish_concurrent_viewers(event['content_id'])

        logger.info(f"Session started: {session_id} (content: {event['content_id']})")

    def _handle_heartbeat_event(self, event: Dict):
        """Handle heartbeat event (sent every 30s during playback)"""
        session_id = event['session_id']

        with self.state_lock:
            if session_id not in self.active_sessions:
                logger.warning(f"Heartbeat for unknown session: {session_id}")
                return

            session = self.active_sessions[session_id]

            # Update session state
            session.last_heartbeat_at = datetime.fromtimestamp(event['timestamp'] / 1000)
            session.current_position_sec = event['position_sec']
            session.max_position_sec = max(session.max_position_sec, event['position_sec'])
            session.bitrates.append(event['bitrate_kbps'])
            session.buffering_events += event.get('buffering_events', 0)
            session.dropped_frames += event.get('dropped_frames', 0)

            # Calculate VST (Video Start Time) on first heartbeat with buffer
            if session.vst_ms is None and event['buffer_health_sec'] > 0:
                vst_ms = event['timestamp'] - int(session.started_at.timestamp() * 1000)
                session.vst_ms = vst_ms

                # Update content metrics
                content_id = session.content_id
                current_avg_vst = self.content_metrics[content_id]['avg_vst_ms']

                # Running average
                if current_avg_vst == 0:
                    self.content_metrics[content_id]['avg_vst_ms'] = vst_ms
                else:
                    # Exponential moving average
                    alpha = 0.1
                    self.content_metrics[content_id]['avg_vst_ms'] = (
                        alpha * vst_ms + (1 - alpha) * current_avg_vst
                    )

                logger.info(f"VST calculated: {vst_ms}ms (session: {session_id})")

    def _handle_stop_event(self, event: Dict):
        """Handle playback stop event"""
        session_id = event['session_id']

        with self.state_lock:
            if session_id not in self.active_sessions:
                logger.warning(f"Stop for unknown session: {session_id}")
                return

            session = self.active_sessions[session_id]

            # Calculate watch duration
            watch_duration_sec = session.max_position_sec - 0

            # Calculate completion rate (placeholder - need content duration from DB)
            content_duration_sec = 7200  # Placeholder: 2 hours
            completion_percentage = min(1.0, session.max_position_sec / content_duration_sec)

            # Calculate QoE score
            qoe_score = self._calculate_qoe_score(session)

            # Update content metrics
            content_id = session.content_id
            self.content_metrics[content_id]['concurrent_viewers'] -= 1
            self.content_metrics[content_id]['rebuffering_events'] += session.buffering_events

            # Remove session from active sessions
            del self.active_sessions[session_id]

        # Publish updated metrics
        self._publish_concurrent_viewers(content_id)
        self._publish_qoe_metrics(content_id)

        # Store viewing history to database
        self._store_viewing_history(session, completion_percentage, qoe_score)

        logger.info(f"Session stopped: {session_id} (watched: {watch_duration_sec:.0f}s, "
                   f"completion: {completion_percentage:.1%}, QoE: {qoe_score:.1f})")

    def _handle_buffering_event(self, event: Dict):
        """Handle buffering event"""
        session_id = event['session_id']

        with self.state_lock:
            if session_id in self.active_sessions:
                session = self.active_sessions[session_id]
                session.buffering_events += 1

                # Increment content-level metric
                content_id = session.content_id
                self.content_metrics[content_id]['rebuffering_events'] += 1

        logger.warning(f"Buffering event: {session_id}")

    def _handle_error_event(self, event: Dict):
        """Handle error event"""
        session_id = event['session_id']
        error_code = event.get('error_code', 'unknown')

        logger.error(f"Playback error: {session_id} (error: {error_code})")

        # Could send alert here
        self._send_alert('playback_error', {
            'session_id': session_id,
            'error_code': error_code,
            'content_id': event.get('content_id'),
            'timestamp': event['timestamp']
        })

    def _calculate_qoe_score(self, session: SessionState) -> float:
        """
        Calculate Quality of Experience score (0-100)

        Factors:
        - VST (Video Start Time)
        - Rebuffering events
        - Average bitrate
        - Dropped frames
        """
        # VST score (lower is better)
        if session.vst_ms:
            vst_score = max(0, 100 - session.vst_ms / 20)
        else:
            vst_score = 50

        # Rebuffering score (fewer is better)
        rebuffering_score = max(0, 100 - session.buffering_events * 10)

        # Bitrate score (higher is better)
        avg_bitrate = statistics.mean(session.bitrates) if session.bitrates else 0
        bitrate_score = min(100, avg_bitrate / 50)

        # Dropped frames score (fewer is better)
        dropped_frames_score = max(0, 100 - session.dropped_frames)

        # Weighted average
        qoe_score = (
            vst_score * 0.3 +
            rebuffering_score * 0.4 +
            bitrate_score * 0.2 +
            dropped_frames_score * 0.1
        )

        return qoe_score

    def _publish_concurrent_viewers(self, content_id: int):
        """Publish concurrent viewers to Redis"""
        concurrent = self.content_metrics[content_id]['concurrent_viewers']

        # Set in Redis with TTL
        key = f"concurrent_viewers:{content_id}"
        self.redis_client.set(key, concurrent, ex=300)  # 5 minute TTL

        # Also publish to pub/sub for real-time updates
        self.redis_client.publish(f"metrics:{content_id}", json.dumps({
            'metric': 'concurrent_viewers',
            'content_id': content_id,
            'value': concurrent,
            'timestamp': int(time.time())
        }))

    def _publish_qoe_metrics(self, content_id: int):
        """Publish QoE metrics to Redis"""
        metrics = self.content_metrics[content_id]

        # Set in Redis
        key = f"qoe_metrics:{content_id}"
        self.redis_client.hmset(key, metrics)
        self.redis_client.expire(key, 3600)  # 1 hour TTL

    def _store_viewing_history(self, session: SessionState,
                               completion_percentage: float,
                               qoe_score: float):
        """Store viewing history to PostgreSQL"""
        if not self.postgres_conn_str:
            return

        try:
            conn = psycopg2.connect(self.postgres_conn_str)
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO viewing_history_hot (
                    user_id, profile_id, content_id, session_id,
                    started_at, ended_at, watch_duration_sec,
                    max_position_sec, completion_percentage,
                    avg_bitrate_kbps, buffering_events,
                    dropped_frames, qoe_score,
                    device_type, country
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
            """, (
                session.user_id,
                session.profile_id,
                session.content_id,
                session.session_id,
                session.started_at,
                session.last_heartbeat_at,
                (session.last_heartbeat_at - session.started_at).total_seconds(),
                session.max_position_sec,
                completion_percentage,
                statistics.mean(session.bitrates) if session.bitrates else 0,
                session.buffering_events,
                session.dropped_frames,
                qoe_score,
                session.device_type,
                session.country
            ))

            conn.commit()
            cursor.close()
            conn.close()

        except Exception as e:
            logger.error(f"Failed to store viewing history: {e}")

    def _send_alert(self, alert_type: str, data: Dict):
        """Send alert (to Slack, PagerDuty, etc.)"""
        # Placeholder - integrate with alerting system
        logger.warning(f"ALERT [{alert_type}]: {json.dumps(data)}")

    def cleanup_stale_sessions(self):
        """Remove sessions inactive for >5 minutes"""
        now = datetime.utcnow()
        stale_threshold = timedelta(minutes=5)

        with self.state_lock:
            stale_sessions = [
                session_id
                for session_id, session in self.active_sessions.items()
                if now - session.last_heartbeat_at > stale_threshold
            ]

            for session_id in stale_sessions:
                session = self.active_sessions[session_id]
                content_id = session.content_id

                # Decrement concurrent viewers
                self.content_metrics[content_id]['concurrent_viewers'] -= 1

                # Remove session
                del self.active_sessions[session_id]

                logger.info(f"Removed stale session: {session_id}")

                # Publish updated metrics
                self._publish_concurrent_viewers(content_id)

    def run(self):
        """Main loop: consume events from Kafka"""
        logger.info("Starting real-time analytics consumer...")

        # Start cleanup thread
        cleanup_thread = Thread(target=self._cleanup_loop, daemon=True)
        cleanup_thread.start()

        # Consume events
        try:
            for message in self.consumer:
                event = message.value
                self.process_event(event)

        except KeyboardInterrupt:
            logger.info("Shutting down...")
        finally:
            self.consumer.close()

    def _cleanup_loop(self):
        """Background thread to cleanup stale sessions"""
        while True:
            time.sleep(60)  # Every minute
            self.cleanup_stale_sessions()


# Example usage
if __name__ == '__main__':
    analytics = RealTimeAnalytics(
        kafka_bootstrap_servers='localhost:9092',
        redis_host='localhost',
        redis_port=6379,
        postgres_conn_str='postgresql://user:password@localhost:5432/netflix'
    )

    analytics.run()
