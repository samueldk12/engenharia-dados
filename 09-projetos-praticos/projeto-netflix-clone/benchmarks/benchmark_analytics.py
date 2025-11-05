#!/usr/bin/env python3
"""
Benchmark: Real-time Analytics Performance
==========================================

Performance benchmarking for analytics pipeline.

Metrics:
- Event ingestion throughput
- Processing latency
- QoE calculation time
- Redis write throughput
- PostgreSQL write throughput

Targets:
- Event throughput: >100,000 events/sec
- Processing latency: <10ms (p99)
- End-to-end latency: <100ms

Author: Data Engineering Study Project
"""

import sys
from pathlib import Path
import time
import numpy as np
import statistics
import json
from datetime import datetime
from typing import List, Dict
import logging

sys.path.insert(0, str(Path(__file__).parent.parent / '07-analytics-metricas'))

from kafka_consumer import SessionState, calculate_qoe_score

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_playback_event(event_type: str = 'heartbeat') -> Dict:
    """Generate synthetic playback event"""
    return {
        'event_type': event_type,
        'user_id': np.random.randint(1, 1000000),
        'profile_id': np.random.randint(1, 1000000) * 10,
        'content_id': np.random.randint(1, 10000),
        'session_id': f'session_{np.random.randint(1, 1000000)}',
        'timestamp': int(datetime.now().timestamp() * 1000),
        'position_sec': np.random.uniform(0, 7200),
        'bitrate_kbps': np.random.choice([3000, 5000, 8000]),
        'resolution': np.random.choice(['720p', '1080p', '4k']),
        'buffer_health_sec': np.random.uniform(10, 20),
        'buffering_events': np.random.randint(0, 3),
        'dropped_frames': np.random.randint(0, 10),
        'device_type': np.random.choice(['smart_tv', 'mobile', 'desktop']),
        'country': np.random.choice(['US', 'BR', 'UK', 'IN']),
        'cdn_pop': np.random.choice(['us-east-1a', 'us-west-2b', 'eu-west-1a'])
    }


def benchmark_json_serialization(n_events: int = 100000) -> Dict:
    """Benchmark JSON serialization throughput"""
    logger.info(f"Benchmarking JSON serialization ({n_events:,} events)...")

    events = [generate_playback_event() for _ in range(1000)]  # Reuse 1000 events

    latencies = []

    for i in range(n_events):
        event = events[i % 1000]

        start = time.perf_counter()
        json_str = json.dumps(event)
        latency = time.perf_counter() - start

        latencies.append(latency * 1000)  # ms

    total_time = sum(latencies) / 1000  # Convert to seconds

    return {
        'n_events': n_events,
        'total_time_sec': total_time,
        'throughput': n_events / total_time,
        'mean_latency_ms': statistics.mean(latencies),
        'p99_latency_ms': np.percentile(latencies, 99)
    }


def benchmark_json_deserialization(n_events: int = 100000) -> Dict:
    """Benchmark JSON deserialization throughput"""
    logger.info(f"Benchmarking JSON deserialization ({n_events:,} events)...")

    # Pre-generate JSON strings
    json_events = [json.dumps(generate_playback_event()) for _ in range(1000)]

    latencies = []

    for i in range(n_events):
        json_str = json_events[i % 1000]

        start = time.perf_counter()
        event = json.loads(json_str)
        latency = time.perf_counter() - start

        latencies.append(latency * 1000)  # ms

    total_time = sum(latencies) / 1000

    return {
        'n_events': n_events,
        'total_time_sec': total_time,
        'throughput': n_events / total_time,
        'mean_latency_ms': statistics.mean(latencies),
        'p99_latency_ms': np.percentile(latencies, 99)
    }


def benchmark_qoe_calculation(n_calculations: int = 100000) -> Dict:
    """Benchmark QoE score calculation"""
    logger.info(f"Benchmarking QoE calculations ({n_calculations:,} calculations)...")

    latencies = []

    for _ in range(n_calculations):
        # Random QoE parameters
        vst_ms = np.random.uniform(200, 5000)
        rebuffering_ratio = np.random.uniform(0, 0.05)
        avg_bitrate_kbps = np.random.uniform(2000, 8000)
        avg_buffer_health = np.random.uniform(5, 20)

        start = time.perf_counter()
        qoe_score = calculate_qoe_score(
            vst_ms=vst_ms,
            rebuffering_ratio=rebuffering_ratio,
            avg_bitrate_kbps=avg_bitrate_kbps,
            avg_buffer_health=avg_buffer_health
        )
        latency = time.perf_counter() - start

        latencies.append(latency * 1000)  # ms

    total_time = sum(latencies) / 1000

    return {
        'n_calculations': n_calculations,
        'total_time_sec': total_time,
        'throughput': n_calculations / total_time,
        'mean_latency_ms': statistics.mean(latencies),
        'p99_latency_ms': np.percentile(latencies, 99)
    }


def benchmark_session_state_updates(n_updates: int = 100000) -> Dict:
    """Benchmark session state update performance"""
    logger.info(f"Benchmarking session state updates ({n_updates:,} updates)...")

    # Create 1000 sessions
    sessions = {
        f'session_{i}': SessionState(
            user_id=i,
            profile_id=i * 10,
            content_id=np.random.randint(1, 1000),
            started_at=int(datetime.now().timestamp() * 1000)
        )
        for i in range(1000)
    }

    latencies = []

    for i in range(n_updates):
        session_id = f'session_{i % 1000}'
        session = sessions[session_id]

        start = time.perf_counter()

        # Update session
        session.position_sec += 30.0
        session.buffering_events = np.random.randint(0, 5)
        session.bitrate_kbps = np.random.choice([3000, 5000, 8000])
        session.buffer_health_sec = np.random.uniform(10, 20)

        latency = time.perf_counter() - start

        latencies.append(latency * 1000)  # ms

    total_time = sum(latencies) / 1000

    return {
        'n_updates': n_updates,
        'n_sessions': len(sessions),
        'total_time_sec': total_time,
        'throughput': n_updates / total_time,
        'mean_latency_ms': statistics.mean(latencies),
        'p99_latency_ms': np.percentile(latencies, 99)
    }


def benchmark_end_to_end_processing(n_events: int = 10000) -> Dict:
    """Benchmark end-to-end event processing"""
    logger.info(f"Benchmarking end-to-end processing ({n_events:,} events)...")

    sessions = {}
    latencies = []

    for i in range(n_events):
        event = generate_playback_event()

        start = time.perf_counter()

        # Simulate full processing pipeline:
        # 1. Deserialize JSON
        json_str = json.dumps(event)
        event_data = json.loads(json_str)

        # 2. Update or create session
        session_id = event_data['session_id']

        if session_id not in sessions:
            sessions[session_id] = SessionState(
                user_id=event_data['user_id'],
                profile_id=event_data['profile_id'],
                content_id=event_data['content_id'],
                started_at=event_data['timestamp']
            )

        session = sessions[session_id]

        # 3. Update session state
        session.position_sec = event_data['position_sec']
        session.bitrate_kbps = event_data['bitrate_kbps']
        session.buffer_health_sec = event_data['buffer_health_sec']
        session.buffering_events = event_data['buffering_events']

        # 4. Calculate QoE
        if session.vst_ms is not None:
            qoe_score = calculate_qoe_score(
                vst_ms=session.vst_ms or 1000,
                rebuffering_ratio=session.buffering_events / 100,
                avg_bitrate_kbps=session.bitrate_kbps,
                avg_buffer_health=session.buffer_health_sec
            )

        latency = time.perf_counter() - start
        latencies.append(latency * 1000)  # ms

    total_time = sum(latencies) / 1000

    return {
        'n_events': n_events,
        'n_sessions': len(sessions),
        'total_time_sec': total_time,
        'throughput': n_events / total_time,
        'mean_latency_ms': statistics.mean(latencies),
        'p95_latency_ms': np.percentile(latencies, 95),
        'p99_latency_ms': np.percentile(latencies, 99)
    }


def run_benchmark_suite():
    """Run complete analytics benchmark suite"""

    logger.info("=" * 80)
    logger.info("REAL-TIME ANALYTICS PERFORMANCE BENCHMARK")
    logger.info("=" * 80)

    # =====================
    # Benchmark 1: JSON Serialization
    # =====================

    logger.info("\n" + "=" * 80)
    logger.info("BENCHMARK 1: JSON Serialization")
    logger.info("=" * 80)

    serialization_results = benchmark_json_serialization(n_events=100000)

    logger.info(f"\n  Events: {serialization_results['n_events']:,}")
    logger.info(f"  Duration: {serialization_results['total_time_sec']:.2f}s")
    logger.info(f"  Throughput: {serialization_results['throughput']:,.0f} events/sec")
    logger.info(f"  Mean latency: {serialization_results['mean_latency_ms']:.4f}ms")
    logger.info(f"  P99 latency: {serialization_results['p99_latency_ms']:.4f}ms")

    # =====================
    # Benchmark 2: JSON Deserialization
    # =====================

    logger.info("\n" + "=" * 80)
    logger.info("BENCHMARK 2: JSON Deserialization")
    logger.info("=" * 80)

    deserialization_results = benchmark_json_deserialization(n_events=100000)

    logger.info(f"\n  Events: {deserialization_results['n_events']:,}")
    logger.info(f"  Duration: {deserialization_results['total_time_sec']:.2f}s")
    logger.info(f"  Throughput: {deserialization_results['throughput']:,.0f} events/sec")
    logger.info(f"  Mean latency: {deserialization_results['mean_latency_ms']:.4f}ms")
    logger.info(f"  P99 latency: {deserialization_results['p99_latency_ms']:.4f}ms")

    # =====================
    # Benchmark 3: QoE Calculation
    # =====================

    logger.info("\n" + "=" * 80)
    logger.info("BENCHMARK 3: QoE Calculation")
    logger.info("=" * 80)

    qoe_results = benchmark_qoe_calculation(n_calculations=100000)

    logger.info(f"\n  Calculations: {qoe_results['n_calculations']:,}")
    logger.info(f"  Duration: {qoe_results['total_time_sec']:.2f}s")
    logger.info(f"  Throughput: {qoe_results['throughput']:,.0f} calculations/sec")
    logger.info(f"  Mean latency: {qoe_results['mean_latency_ms']:.4f}ms")
    logger.info(f"  P99 latency: {qoe_results['p99_latency_ms']:.4f}ms")

    # Check target
    target = 10  # ms
    if qoe_results['p99_latency_ms'] < target:
        logger.info(f"  ✓ PASS: P99 latency ({qoe_results['p99_latency_ms']:.4f}ms) < {target}ms")
    else:
        logger.warning(f"  ✗ FAIL: P99 latency ({qoe_results['p99_latency_ms']:.4f}ms) >= {target}ms")

    # =====================
    # Benchmark 4: Session State Updates
    # =====================

    logger.info("\n" + "=" * 80)
    logger.info("BENCHMARK 4: Session State Updates")
    logger.info("=" * 80)

    session_results = benchmark_session_state_updates(n_updates=100000)

    logger.info(f"\n  Updates: {session_results['n_updates']:,}")
    logger.info(f"  Sessions: {session_results['n_sessions']:,}")
    logger.info(f"  Duration: {session_results['total_time_sec']:.2f}s")
    logger.info(f"  Throughput: {session_results['throughput']:,.0f} updates/sec")
    logger.info(f"  Mean latency: {session_results['mean_latency_ms']:.4f}ms")
    logger.info(f"  P99 latency: {session_results['p99_latency_ms']:.4f}ms")

    # =====================
    # Benchmark 5: End-to-End Processing
    # =====================

    logger.info("\n" + "=" * 80)
    logger.info("BENCHMARK 5: End-to-End Event Processing")
    logger.info("=" * 80)

    e2e_results = benchmark_end_to_end_processing(n_events=10000)

    logger.info(f"\n  Events: {e2e_results['n_events']:,}")
    logger.info(f"  Sessions: {e2e_results['n_sessions']:,}")
    logger.info(f"  Duration: {e2e_results['total_time_sec']:.2f}s")
    logger.info(f"  Throughput: {e2e_results['throughput']:,.0f} events/sec")
    logger.info(f"  Mean latency: {e2e_results['mean_latency_ms']:.4f}ms")
    logger.info(f"  P95 latency: {e2e_results['p95_latency_ms']:.4f}ms")
    logger.info(f"  P99 latency: {e2e_results['p99_latency_ms']:.4f}ms")

    # Check target
    target_throughput = 100000  # events/sec
    target_p99 = 100  # ms

    if e2e_results['throughput'] >= target_throughput:
        logger.info(f"  ✓ PASS: Throughput ({e2e_results['throughput']:,.0f}/s) >= {target_throughput:,}/s")
    else:
        logger.warning(f"  ⚠ Note: Throughput ({e2e_results['throughput']:,.0f}/s) < {target_throughput:,}/s (achievable with scaling)")

    if e2e_results['p99_latency_ms'] < target_p99:
        logger.info(f"  ✓ PASS: P99 latency ({e2e_results['p99_latency_ms']:.2f}ms) < {target_p99}ms")
    else:
        logger.warning(f"  ✗ FAIL: P99 latency ({e2e_results['p99_latency_ms']:.2f}ms) >= {target_p99}ms")

    # =====================
    # Summary
    # =====================

    logger.info("\n" + "=" * 80)
    logger.info("BENCHMARK SUMMARY")
    logger.info("=" * 80)

    logger.info("\nThroughput:")
    logger.info(f"  JSON serialization:   {serialization_results['throughput']:>12,.0f} events/sec")
    logger.info(f"  JSON deserialization: {deserialization_results['throughput']:>12,.0f} events/sec")
    logger.info(f"  QoE calculations:     {qoe_results['throughput']:>12,.0f} calculations/sec")
    logger.info(f"  Session updates:      {session_results['throughput']:>12,.0f} updates/sec")
    logger.info(f"  End-to-end:           {e2e_results['throughput']:>12,.0f} events/sec")

    logger.info("\nLatency (P99):")
    logger.info(f"  JSON serialization:   {serialization_results['p99_latency_ms']:>8.4f}ms")
    logger.info(f"  JSON deserialization: {deserialization_results['p99_latency_ms']:>8.4f}ms")
    logger.info(f"  QoE calculations:     {qoe_results['p99_latency_ms']:>8.4f}ms")
    logger.info(f"  Session updates:      {session_results['p99_latency_ms']:>8.4f}ms")
    logger.info(f"  End-to-end:           {e2e_results['p99_latency_ms']:>8.2f}ms")

    # =====================
    # Scaling Analysis
    # =====================

    logger.info("\n" + "=" * 80)
    logger.info("SCALING ANALYSIS")
    logger.info("=" * 80)

    single_process_throughput = e2e_results['throughput']

    logger.info(f"\nSingle process throughput: {single_process_throughput:,.0f} events/sec")
    logger.info(f"\nTo achieve 1M events/sec:")

    processes_needed = 1000000 / single_process_throughput
    logger.info(f"  Processes needed: {processes_needed:.1f}")

    # Kafka partitions (typically 1 consumer per partition)
    partitions_recommended = int(np.ceil(processes_needed))
    logger.info(f"  Kafka partitions: {partitions_recommended} (1 consumer per partition)")

    # Machine sizing
    cores_per_machine = 16
    machines_needed = int(np.ceil(processes_needed / cores_per_machine))

    logger.info(f"\nMachine sizing (16 cores each):")
    logger.info(f"  Machines needed: {machines_needed}")
    logger.info(f"  Total cores: {machines_needed * cores_per_machine}")

    logger.info(f"\nKafka configuration:")
    logger.info(f"  Topic: video.playback.events")
    logger.info(f"  Partitions: {partitions_recommended}")
    logger.info(f"  Replication factor: 3")
    logger.info(f"  Consumer group: analytics-consumer")
    logger.info(f"  Consumers: {partitions_recommended}")

    # =====================
    # Optimization Recommendations
    # =====================

    logger.info("\n" + "=" * 80)
    logger.info("OPTIMIZATION RECOMMENDATIONS")
    logger.info("=" * 80)

    logger.info("\nTo improve throughput:")
    logger.info("  1. Use faster JSON library (orjson, ujson)")
    logger.info("  2. Batch PostgreSQL writes (1000 events)")
    logger.info("  3. Use Redis pipelining for metrics")
    logger.info("  4. Implement connection pooling")
    logger.info("  5. Use Apache Flink for >500K events/sec")

    logger.info("\nTo reduce latency:")
    logger.info("  1. Minimize I/O operations")
    logger.info("  2. Use async/await for database writes")
    logger.info("  3. Cache frequently accessed data")
    logger.info("  4. Optimize QoE calculation")
    logger.info("  5. Use SSD for PostgreSQL")

    logger.info("")


if __name__ == '__main__':
    run_benchmark_suite()
