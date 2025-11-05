#!/usr/bin/env python3
"""
Benchmark: Recommendation Engine Performance
============================================

Performance benchmarking for recommendation system.

Metrics:
- Prediction latency (single)
- Batch prediction throughput
- Top-N recommendation latency
- Training time
- Model size

Targets:
- Single prediction: <1ms
- Top-20 recommendations: <50ms (p99)
- Batch prediction: >10,000 predictions/sec

Author: Data Engineering Study Project
"""

import sys
from pathlib import Path
import time
import numpy as np
import pandas as pd
import statistics
from typing import List, Tuple
import logging

sys.path.insert(0, str(Path(__file__).parent.parent / '06-sistema-recomendacao'))

from recommendation_engine import MatrixFactorization, NeuralCollaborativeFiltering

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_dataset(n_users: int, n_items: int, n_interactions: int) -> pd.DataFrame:
    """Generate synthetic interaction data"""
    np.random.seed(42)

    return pd.DataFrame({
        'user_id': np.random.randint(1, n_users + 1, n_interactions),
        'content_id': np.random.randint(1, n_items + 1, n_interactions),
        'rating': np.random.choice([3, 4, 5], n_interactions, p=[0.2, 0.3, 0.5])
    }).drop_duplicates(subset=['user_id', 'content_id'])


def benchmark_single_prediction(model: MatrixFactorization, n_iterations: int = 10000) -> dict:
    """Benchmark single prediction latency"""
    logger.info(f"Benchmarking single predictions ({n_iterations:,} iterations)...")

    latencies = []

    for _ in range(n_iterations):
        user_id = np.random.randint(1, 1001)
        item_id = np.random.randint(1, 5001)

        start = time.perf_counter()
        model.predict(user_id, item_id)
        latency = time.perf_counter() - start

        latencies.append(latency * 1000)  # Convert to ms

    return {
        'mean': statistics.mean(latencies),
        'median': statistics.median(latencies),
        'p95': np.percentile(latencies, 95),
        'p99': np.percentile(latencies, 99),
        'min': min(latencies),
        'max': max(latencies)
    }


def benchmark_batch_prediction(model: MatrixFactorization, batch_size: int = 10000) -> dict:
    """Benchmark batch prediction throughput"""
    logger.info(f"Benchmarking batch predictions ({batch_size:,} predictions)...")

    # Generate test batch
    test_data = pd.DataFrame({
        'user_id': np.random.randint(1, 1001, batch_size),
        'content_id': np.random.randint(1, 5001, batch_size)
    })

    start = time.perf_counter()
    predictions = model.predict_batch(test_data)
    duration = time.perf_counter() - start

    throughput = batch_size / duration

    return {
        'batch_size': batch_size,
        'duration_sec': duration,
        'throughput': throughput,
        'avg_latency_ms': (duration / batch_size) * 1000
    }


def benchmark_top_n_recommendations(model: MatrixFactorization, n: int = 20, n_iterations: int = 1000) -> dict:
    """Benchmark top-N recommendation generation"""
    logger.info(f"Benchmarking top-{n} recommendations ({n_iterations:,} iterations)...")

    latencies = []

    for _ in range(n_iterations):
        user_id = np.random.randint(1, 1001)

        start = time.perf_counter()
        recommendations = model.recommend(user_id, n=n, exclude_seen=True)
        latency = time.perf_counter() - start

        latencies.append(latency * 1000)  # Convert to ms

    return {
        'n': n,
        'mean': statistics.mean(latencies),
        'median': statistics.median(latencies),
        'p95': np.percentile(latencies, 95),
        'p99': np.percentile(latencies, 99),
        'min': min(latencies),
        'max': max(latencies)
    }


def benchmark_training_time(interactions: pd.DataFrame, n_factors: int = 50, n_epochs: int = 20) -> dict:
    """Benchmark model training time"""
    logger.info(f"Benchmarking training time ({len(interactions):,} interactions, {n_epochs} epochs)...")

    model = MatrixFactorization(
        n_factors=n_factors,
        n_epochs=n_epochs,
        learning_rate=0.01,
        reg=0.02
    )

    start = time.perf_counter()
    model.fit(interactions, verbose=False)
    duration = time.perf_counter() - start

    return {
        'n_interactions': len(interactions),
        'n_factors': n_factors,
        'n_epochs': n_epochs,
        'duration_sec': duration,
        'interactions_per_sec': len(interactions) * n_epochs / duration
    }


def benchmark_model_size(model: MatrixFactorization) -> dict:
    """Estimate model memory footprint"""
    logger.info("Calculating model size...")

    # Size of user factors
    user_factors_size = model.user_factors.nbytes if model.user_factors is not None else 0

    # Size of item factors
    item_factors_size = model.item_factors.nbytes if model.item_factors is not None else 0

    # Size of biases
    user_bias_size = model.user_bias.nbytes if hasattr(model, 'user_bias') and model.user_bias is not None else 0
    item_bias_size = model.item_bias.nbytes if hasattr(model, 'item_bias') and model.item_bias is not None else 0

    total_size = user_factors_size + item_factors_size + user_bias_size + item_bias_size

    return {
        'user_factors_mb': user_factors_size / 1024**2,
        'item_factors_mb': item_factors_size / 1024**2,
        'total_mb': total_size / 1024**2,
        'n_users': model.user_factors.shape[0] if model.user_factors is not None else 0,
        'n_items': model.item_factors.shape[0] if model.item_factors is not None else 0,
        'n_factors': model.n_factors
    }


def run_benchmark_suite():
    """Run complete benchmark suite"""

    logger.info("=" * 80)
    logger.info("RECOMMENDATION ENGINE PERFORMANCE BENCHMARK")
    logger.info("=" * 80)

    # =====================
    # Setup
    # =====================

    logger.info("\nGenerating test dataset...")

    # Small dataset for quick iteration
    small_data = generate_dataset(n_users=1000, n_items=5000, n_interactions=50000)
    logger.info(f"  Small: {len(small_data):,} interactions")

    # Medium dataset (Netflix scale: millions of users/items)
    medium_data = generate_dataset(n_users=10000, n_items=20000, n_interactions=500000)
    logger.info(f"  Medium: {len(medium_data):,} interactions")

    # =====================
    # Benchmark 1: Training Time
    # =====================

    logger.info("\n" + "=" * 80)
    logger.info("BENCHMARK 1: Training Time")
    logger.info("=" * 80)

    # Train on small dataset
    training_results_small = benchmark_training_time(
        small_data,
        n_factors=50,
        n_epochs=20
    )

    logger.info(f"\nSmall dataset:")
    logger.info(f"  Duration: {training_results_small['duration_sec']:.2f}s")
    logger.info(f"  Throughput: {training_results_small['interactions_per_sec']:,.0f} interactions/sec")

    # Train model for subsequent benchmarks
    logger.info("\nTraining model for performance tests...")
    model = MatrixFactorization(n_factors=50, n_epochs=20, learning_rate=0.01, reg=0.02)
    model.fit(small_data, verbose=False)

    # =====================
    # Benchmark 2: Model Size
    # =====================

    logger.info("\n" + "=" * 80)
    logger.info("BENCHMARK 2: Model Size")
    logger.info("=" * 80)

    size_results = benchmark_model_size(model)

    logger.info(f"\n  Users: {size_results['n_users']:,}")
    logger.info(f"  Items: {size_results['n_items']:,}")
    logger.info(f"  Factors: {size_results['n_factors']}")
    logger.info(f"  User factors: {size_results['user_factors_mb']:.2f} MB")
    logger.info(f"  Item factors: {size_results['item_factors_mb']:.2f} MB")
    logger.info(f"  Total size: {size_results['total_mb']:.2f} MB")

    # =====================
    # Benchmark 3: Single Prediction Latency
    # =====================

    logger.info("\n" + "=" * 80)
    logger.info("BENCHMARK 3: Single Prediction Latency")
    logger.info("=" * 80)

    prediction_results = benchmark_single_prediction(model, n_iterations=10000)

    logger.info(f"\n  Mean: {prediction_results['mean']:.4f}ms")
    logger.info(f"  Median: {prediction_results['median']:.4f}ms")
    logger.info(f"  P95: {prediction_results['p95']:.4f}ms")
    logger.info(f"  P99: {prediction_results['p99']:.4f}ms")
    logger.info(f"  Min: {prediction_results['min']:.4f}ms")
    logger.info(f"  Max: {prediction_results['max']:.4f}ms")

    # Check target
    target = 1.0  # ms
    if prediction_results['p99'] < target:
        logger.info(f"  ✓ PASS: P99 latency ({prediction_results['p99']:.4f}ms) < {target}ms")
    else:
        logger.warning(f"  ✗ FAIL: P99 latency ({prediction_results['p99']:.4f}ms) >= {target}ms")

    # =====================
    # Benchmark 4: Batch Prediction Throughput
    # =====================

    logger.info("\n" + "=" * 80)
    logger.info("BENCHMARK 4: Batch Prediction Throughput")
    logger.info("=" * 80)

    batch_results = benchmark_batch_prediction(model, batch_size=10000)

    logger.info(f"\n  Batch size: {batch_results['batch_size']:,}")
    logger.info(f"  Duration: {batch_results['duration_sec']:.4f}s")
    logger.info(f"  Throughput: {batch_results['throughput']:,.0f} predictions/sec")
    logger.info(f"  Avg latency: {batch_results['avg_latency_ms']:.4f}ms")

    # Check target
    target_throughput = 10000  # predictions/sec
    if batch_results['throughput'] >= target_throughput:
        logger.info(f"  ✓ PASS: Throughput ({batch_results['throughput']:,.0f}/s) >= {target_throughput:,}/s")
    else:
        logger.warning(f"  ✗ FAIL: Throughput ({batch_results['throughput']:,.0f}/s) < {target_throughput:,}/s")

    # =====================
    # Benchmark 5: Top-N Recommendation Latency
    # =====================

    logger.info("\n" + "=" * 80)
    logger.info("BENCHMARK 5: Top-N Recommendation Latency")
    logger.info("=" * 80)

    recommendation_results = benchmark_top_n_recommendations(model, n=20, n_iterations=1000)

    logger.info(f"\n  Top-N: {recommendation_results['n']}")
    logger.info(f"  Mean: {recommendation_results['mean']:.2f}ms")
    logger.info(f"  Median: {recommendation_results['median']:.2f}ms")
    logger.info(f"  P95: {recommendation_results['p95']:.2f}ms")
    logger.info(f"  P99: {recommendation_results['p99']:.2f}ms")
    logger.info(f"  Min: {recommendation_results['min']:.2f}ms")
    logger.info(f"  Max: {recommendation_results['max']:.2f}ms")

    # Check target
    target_p99 = 50  # ms
    if recommendation_results['p99'] < target_p99:
        logger.info(f"  ✓ PASS: P99 latency ({recommendation_results['p99']:.2f}ms) < {target_p99}ms")
    else:
        logger.warning(f"  ✗ FAIL: P99 latency ({recommendation_results['p99']:.2f}ms) >= {target_p99}ms")

    # =====================
    # Summary
    # =====================

    logger.info("\n" + "=" * 80)
    logger.info("BENCHMARK SUMMARY")
    logger.info("=" * 80)

    logger.info("\nPerformance Targets:")
    logger.info(f"  Single prediction < 1ms:     {'✓ PASS' if prediction_results['p99'] < 1.0 else '✗ FAIL'}")
    logger.info(f"  Batch throughput > 10K/s:    {'✓ PASS' if batch_results['throughput'] >= 10000 else '✗ FAIL'}")
    logger.info(f"  Top-20 recs < 50ms (p99):    {'✓ PASS' if recommendation_results['p99'] < 50 else '✗ FAIL'}")

    logger.info("\nKey Metrics:")
    logger.info(f"  Training time: {training_results_small['duration_sec']:.2f}s")
    logger.info(f"  Model size: {size_results['total_mb']:.2f} MB")
    logger.info(f"  Prediction p99: {prediction_results['p99']:.4f}ms")
    logger.info(f"  Batch throughput: {batch_results['throughput']:,.0f} predictions/sec")
    logger.info(f"  Recommendation p99: {recommendation_results['p99']:.2f}ms")

    logger.info("\nProduction Readiness:")

    all_pass = (
        prediction_results['p99'] < 1.0 and
        batch_results['throughput'] >= 10000 and
        recommendation_results['p99'] < 50
    )

    if all_pass:
        logger.info("  ✓ ALL BENCHMARKS PASSED - Ready for production!")
    else:
        logger.warning("  ⚠ SOME BENCHMARKS FAILED - Optimization needed")

    # =====================
    # Recommendations
    # =====================

    logger.info("\n" + "=" * 80)
    logger.info("OPTIMIZATION RECOMMENDATIONS")
    logger.info("=" * 80)

    if prediction_results['p99'] >= 1.0:
        logger.info("\n  Single Prediction Latency:")
        logger.info("    - Use NumPy vectorization")
        logger.info("    - Pre-compute user/item factors")
        logger.info("    - Cache in Redis")

    if batch_results['throughput'] < 10000:
        logger.info("\n  Batch Throughput:")
        logger.info("    - Use NumPy matrix operations")
        logger.info("    - Parallelize with multiprocessing")
        logger.info("    - Use GPU acceleration")

    if recommendation_results['p99'] >= 50:
        logger.info("\n  Recommendation Latency:")
        logger.info("    - Pre-compute top-N offline")
        logger.info("    - Use approximate nearest neighbors (Annoy, FAISS)")
        logger.info("    - Reduce candidate pool size")
        logger.info("    - Cache popular recommendations")

    logger.info("")


if __name__ == '__main__':
    run_benchmark_suite()
