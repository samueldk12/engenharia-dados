#!/usr/bin/env python3
"""
Netflix Clone - Real-time Analytics with Apache Flink
======================================================

Processamento de eventos de streaming em tempo real para métricas de QoE.

Events:
- video.playback.start
- video.playback.heartbeat (every 30s)
- video.playback.stop
- video.buffering
- video.error

Metrics:
- Concurrent viewers (real-time)
- Video Start Time (VST) - p50, p95, p99
- Rebuffering ratio
- Completion rate
- Quality of Experience (QoE) score

Output:
- Redis (real-time metrics)
- Cassandra (time-series data)
- S3 (data lake)

Author: Data Engineering Study Project
"""

from pyflink.datastream import StreamExecutionEnvironment, TimeCharacteristic
from pyflink.datastream.window import TumblingProcessingTimeWindows, SlidingProcessingTimeWindows
from pyflink.datastream.functions import ProcessWindowFunction, MapFunction, KeyedProcessFunction
from pyflink.common.typeinfo import Types
from pyflink.common.time import Time
from pyflink.common.watermark_strategy import WatermarkStrategy

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
from collections import defaultdict
import statistics

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class PlaybackEvent:
    """Playback event from Kafka"""
    event_type: str  # 'start', 'heartbeat', 'stop', 'buffering', 'error'
    user_id: int
    profile_id: int
    content_id: int
    session_id: str
    timestamp: int  # Unix timestamp (ms)

    # Playback state
    position_sec: float
    bitrate_kbps: int
    resolution: str  # '1080p', '720p', etc.

    # Quality metrics
    buffer_health_sec: float  # Seconds of video buffered
    buffering_events: int  # Cumulative buffering events
    dropped_frames: int

    # Context
    device_type: str
    country: str
    cdn_pop: str  # CDN Point of Presence

    def to_dict(self):
        return asdict(self)

    @staticmethod
    def from_json(json_str: str):
        """Parse JSON to PlaybackEvent"""
        data = json.loads(json_str)
        return PlaybackEvent(**data)


@dataclass
class QoEMetrics:
    """Quality of Experience metrics"""
    content_id: int
    window_start: int
    window_end: int

    # Aggregated metrics
    view_count: int
    unique_viewers: int
    avg_bitrate_kbps: float
    avg_buffer_health_sec: float
    total_buffering_events: int
    total_rebuffering_duration_sec: float
    rebuffering_ratio: float  # % of time spent rebuffering
    avg_dropped_frames: float

    # Video Start Time (VST)
    vst_p50_ms: float
    vst_p95_ms: float
    vst_p99_ms: float

    # Completion rate
    plays_started: int
    plays_completed: int  # >70% watched
    completion_rate: float

    # QoE score (0-100)
    qoe_score: float

    def to_dict(self):
        return asdict(self)


class EventParser(MapFunction):
    """Parse JSON events from Kafka"""

    def map(self, value: str) -> PlaybackEvent:
        return PlaybackEvent.from_json(value)


class ConcurrentViewersCounter(KeyedProcessFunction):
    """
    Count concurrent viewers per content in real-time

    Maintains state of active sessions
    """

    def process_element(self, event: PlaybackEvent, ctx):
        # Track active sessions
        if event.event_type == 'start':
            # Session started
            state = ctx.get_state('active_sessions')
            sessions = state.value() or set()
            sessions.add(event.session_id)
            state.update(sessions)

        elif event.event_type == 'stop':
            # Session ended
            state = ctx.get_state('active_sessions')
            sessions = state.value() or set()
            sessions.discard(event.session_id)
            state.update(sessions)

        # Emit concurrent viewer count
        state = ctx.get_state('active_sessions')
        concurrent_viewers = len(state.value() or set())

        yield {
            'content_id': event.content_id,
            'timestamp': event.timestamp,
            'concurrent_viewers': concurrent_viewers
        }


class QoEAggregator(ProcessWindowFunction):
    """
    Aggregate QoE metrics over time windows

    Window: 5 minutes (tumbling)
    """

    def process(self, key: int, context, elements) -> QoEMetrics:
        """
        Process window of events for a content_id

        Args:
            key: content_id
            context: Window context
            elements: Events in window

        Returns:
            QoEMetrics for the window
        """
        events = list(elements)

        if not events:
            return None

        content_id = key
        window_start = context.window().start
        window_end = context.window().end

        # Collect metrics
        unique_users = set()
        unique_sessions = set()
        bitrates = []
        buffer_healths = []
        buffering_events_total = 0
        dropped_frames_total = 0

        start_events = []
        stop_events = []
        vst_times = []  # Video Start Times

        for event in events:
            unique_users.add(event.user_id)
            unique_sessions.add(event.session_id)

            if event.bitrate_kbps > 0:
                bitrates.append(event.bitrate_kbps)

            buffer_healths.append(event.buffer_health_sec)
            buffering_events_total += event.buffering_events
            dropped_frames_total += event.dropped_frames

            if event.event_type == 'start':
                start_events.append(event)
            elif event.event_type == 'stop':
                stop_events.append(event)

        # Calculate VST (Video Start Time)
        # Time from 'start' event to first 'heartbeat' with buffer_health > 0
        session_vsts = {}
        for start_event in start_events:
            # Find first heartbeat for this session
            heartbeats = [
                e for e in events
                if e.session_id == start_event.session_id and
                e.event_type == 'heartbeat' and
                e.buffer_health_sec > 0
            ]

            if heartbeats:
                first_heartbeat = min(heartbeats, key=lambda e: e.timestamp)
                vst_ms = first_heartbeat.timestamp - start_event.timestamp
                session_vsts[start_event.session_id] = vst_ms
                vst_times.append(vst_ms)

        # Calculate completion rate
        # Session is "completed" if watch_percentage > 70%
        completed_sessions = 0
        for stop_event in stop_events:
            # Get content duration (placeholder - would come from DB)
            content_duration_sec = 7200  # 2 hours

            watch_percentage = stop_event.position_sec / content_duration_sec
            if watch_percentage > 0.7:
                completed_sessions += 1

        # Calculate rebuffering ratio
        # Estimate: buffering_events * avg_buffering_duration / total_watch_time
        avg_buffering_duration = 2.0  # seconds (estimated)
        total_buffering_time = buffering_events_total * avg_buffering_duration
        total_watch_time = len(events) * 30  # 30s per heartbeat
        rebuffering_ratio = total_buffering_time / total_watch_time if total_watch_time > 0 else 0.0

        # Calculate percentiles for VST
        if vst_times:
            vst_sorted = sorted(vst_times)
            vst_p50 = vst_sorted[int(len(vst_sorted) * 0.50)]
            vst_p95 = vst_sorted[int(len(vst_sorted) * 0.95)]
            vst_p99 = vst_sorted[int(len(vst_sorted) * 0.99)]
        else:
            vst_p50 = vst_p95 = vst_p99 = 0.0

        # Calculate QoE score (0-100)
        # Factors:
        # - VST (lower is better)
        # - Rebuffering ratio (lower is better)
        # - Bitrate (higher is better)
        # - Buffer health (higher is better)

        vst_score = max(0, 100 - vst_p95 / 20)  # Penalize VST > 2000ms
        rebuffering_score = max(0, 100 - rebuffering_ratio * 10000)
        bitrate_score = min(100, statistics.mean(bitrates) / 50) if bitrates else 0
        buffer_score = min(100, statistics.mean(buffer_healths) * 10)

        qoe_score = (
            vst_score * 0.3 +
            rebuffering_score * 0.4 +
            bitrate_score * 0.15 +
            buffer_score * 0.15
        )

        # Create metrics object
        metrics = QoEMetrics(
            content_id=content_id,
            window_start=window_start,
            window_end=window_end,
            view_count=len(events),
            unique_viewers=len(unique_users),
            avg_bitrate_kbps=statistics.mean(bitrates) if bitrates else 0,
            avg_buffer_health_sec=statistics.mean(buffer_healths) if buffer_healths else 0,
            total_buffering_events=buffering_events_total,
            total_rebuffering_duration_sec=total_buffering_time,
            rebuffering_ratio=rebuffering_ratio,
            avg_dropped_frames=dropped_frames_total / len(events) if events else 0,
            vst_p50_ms=vst_p50,
            vst_p95_ms=vst_p95,
            vst_p99_ms=vst_p99,
            plays_started=len(start_events),
            plays_completed=completed_sessions,
            completion_rate=completed_sessions / len(stop_events) if stop_events else 0.0,
            qoe_score=qoe_score
        )

        return metrics


class AlertingFunction(MapFunction):
    """
    Generate alerts based on QoE metrics

    Alerts:
    - QoE score < 70
    - Rebuffering ratio > 2%
    - VST p95 > 3000ms
    """

    def map(self, metrics: QoEMetrics) -> Optional[Dict]:
        alerts = []

        # Check QoE score
        if metrics.qoe_score < 70:
            alerts.append({
                'severity': 'warning',
                'metric': 'qoe_score',
                'value': metrics.qoe_score,
                'threshold': 70,
                'message': f'Low QoE score for content {metrics.content_id}: {metrics.qoe_score:.1f}'
            })

        # Check rebuffering
        if metrics.rebuffering_ratio > 0.02:  # >2%
            alerts.append({
                'severity': 'critical',
                'metric': 'rebuffering_ratio',
                'value': metrics.rebuffering_ratio,
                'threshold': 0.02,
                'message': f'High rebuffering for content {metrics.content_id}: {metrics.rebuffering_ratio:.2%}'
            })

        # Check VST
        if metrics.vst_p95_ms > 3000:  # >3 seconds
            alerts.append({
                'severity': 'warning',
                'metric': 'vst_p95',
                'value': metrics.vst_p95_ms,
                'threshold': 3000,
                'message': f'High VST for content {metrics.content_id}: {metrics.vst_p95_ms:.0f}ms'
            })

        if alerts:
            return {
                'content_id': metrics.content_id,
                'timestamp': metrics.window_end,
                'alerts': alerts
            }

        return None


def create_flink_job():
    """
    Create Flink streaming job for real-time analytics
    """
    # Initialize environment
    env = StreamExecutionEnvironment.get_execution_environment()
    env.set_stream_time_characteristic(TimeCharacteristic.ProcessingTime)
    env.set_parallelism(4)

    # Add Kafka connector
    from pyflink.datastream.connectors.kafka import FlinkKafkaConsumer, FlinkKafkaProducer
    from pyflink.common.serialization import SimpleStringSchema

    # Kafka source
    kafka_consumer = FlinkKafkaConsumer(
        topics='video.playback.events',
        deserialization_schema=SimpleStringSchema(),
        properties={
            'bootstrap.servers': 'localhost:9092',
            'group.id': 'flink-qoe-analytics'
        }
    )

    # Read events from Kafka
    events = env.add_source(kafka_consumer) \
        .map(EventParser(), output_type=Types.PICKLED_BYTE_ARRAY())

    # ==========================================
    # Pipeline 1: Concurrent Viewers (Real-time)
    # ==========================================

    concurrent_viewers = events \
        .key_by(lambda e: e.content_id) \
        .process(ConcurrentViewersCounter())

    # Write to Redis (real-time dashboard)
    # concurrent_viewers.add_sink(RedisSink(...))

    # ==========================================
    # Pipeline 2: QoE Metrics (5-minute windows)
    # ==========================================

    qoe_metrics = events \
        .key_by(lambda e: e.content_id) \
        .window(TumblingProcessingTimeWindows.of(Time.minutes(5))) \
        .process(QoEAggregator(), output_type=Types.PICKLED_BYTE_ARRAY())

    # Write to Cassandra (time-series storage)
    # qoe_metrics.add_sink(CassandraSink(...))

    # Write to S3 (data lake)
    # qoe_metrics.add_sink(S3Sink(...))

    # ==========================================
    # Pipeline 3: Alerting
    # ==========================================

    alerts = qoe_metrics \
        .map(AlertingFunction()) \
        .filter(lambda x: x is not None)

    # Write alerts to Slack/PagerDuty
    # alerts.add_sink(AlertingSink(...))

    # Print for debugging
    qoe_metrics.print()
    alerts.print()

    # Execute job
    env.execute('Netflix Real-time Analytics')


def create_kafka_producer_example():
    """
    Example: Send playback events to Kafka
    """
    from kafka import KafkaProducer
    import time
    import random

    producer = KafkaProducer(
        bootstrap_servers='localhost:9092',
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )

    # Simulate playback events
    session_id = f"session_{int(time.time())}"
    content_id = random.randint(1, 1000)
    user_id = random.randint(1, 10000)

    # Start event
    start_event = {
        'event_type': 'start',
        'user_id': user_id,
        'profile_id': user_id * 10,
        'content_id': content_id,
        'session_id': session_id,
        'timestamp': int(time.time() * 1000),
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

    producer.send('video.playback.events', start_event)
    logger.info(f"Sent start event for session {session_id}")

    # Heartbeat events (every 30 seconds)
    for i in range(10):
        time.sleep(30)

        heartbeat_event = {
            'event_type': 'heartbeat',
            'user_id': user_id,
            'profile_id': user_id * 10,
            'content_id': content_id,
            'session_id': session_id,
            'timestamp': int(time.time() * 1000),
            'position_sec': (i + 1) * 30.0,
            'bitrate_kbps': random.randint(4000, 6000),
            'resolution': '1080p',
            'buffer_health_sec': random.uniform(10, 20),
            'buffering_events': random.randint(0, 2),
            'dropped_frames': random.randint(0, 5),
            'device_type': 'smart_tv',
            'country': 'US',
            'cdn_pop': 'us-east-1a'
        }

        producer.send('video.playback.events', heartbeat_event)
        logger.info(f"Sent heartbeat {i+1} for session {session_id}")

    # Stop event
    stop_event = {
        'event_type': 'stop',
        'user_id': user_id,
        'profile_id': user_id * 10,
        'content_id': content_id,
        'session_id': session_id,
        'timestamp': int(time.time() * 1000),
        'position_sec': 300.0,
        'bitrate_kbps': 5000,
        'resolution': '1080p',
        'buffer_health_sec': 15.0,
        'buffering_events': 1,
        'dropped_frames': 3,
        'device_type': 'smart_tv',
        'country': 'US',
        'cdn_pop': 'us-east-1a'
    }

    producer.send('video.playback.events', stop_event)
    logger.info(f"Sent stop event for session {session_id}")

    producer.flush()
    producer.close()


# Example usage
if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == 'producer':
        # Run producer (send test events)
        logger.info("Starting Kafka producer...")
        create_kafka_producer_example()
    else:
        # Run Flink job
        logger.info("Starting Flink job...")
        create_flink_job()
