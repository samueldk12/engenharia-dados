# Netflix Clone - Test Suite

Comprehensive automated test suite for the Netflix Clone project.

## Test Coverage

### Unit Tests
- **Video Transcoder** (`test_video_transcoder.py`): 18 tests
  - Profile creation and bitrate ladder
  - FFmpeg command generation
  - HLS playlist generation
  - Error handling
  - Hardware acceleration

- **Storage Manager** (`test_storage_manager.py`): 20 tests
  - S3 and GCS providers
  - File upload/download
  - Presigned URLs
  - Directory uploads (parallel and sequential)
  - CDN invalidation
  - Metadata handling

- **Recommendation Engine** (`test_recommendation_engine.py`): 22 tests
  - Matrix Factorization algorithm
  - Candidate generation from multiple sources
  - Ranking with ML features
  - Diversification (MMR algorithm)
  - Caching
  - Performance benchmarks

- **Real-time Analytics** (`test_analytics.py`): 15 tests
  - Event processing (start, heartbeat, stop, buffering)
  - Session state management
  - QoE score calculation
  - Concurrent viewer tracking
  - Redis metrics publishing
  - PostgreSQL data persistence

**Total: 75+ tests**

## Setup

### Install Test Dependencies

```bash
cd tests
pip install -r requirements.txt
```

### Install Main Project Dependencies

```bash
cd ..
pip install -r requirements.txt
```

## Running Tests

### Run All Tests

```bash
pytest
```

### Run Specific Test File

```bash
pytest test_video_transcoder.py
pytest test_storage_manager.py
pytest test_recommendation_engine.py
pytest test_analytics.py
```

### Run Specific Test Class

```bash
pytest test_video_transcoder.py::TestVideoProfile
pytest test_storage_manager.py::TestS3Provider
```

### Run Specific Test Function

```bash
pytest test_video_transcoder.py::TestVideoProfile::test_video_profile_creation
```

### Run with Verbose Output

```bash
pytest -v
```

### Run with Test Coverage

```bash
pytest --cov=. --cov-report=html --cov-report=term
```

Open `htmlcov/index.html` to view detailed coverage report.

### Run in Parallel (faster)

```bash
pytest -n 4  # Run on 4 CPU cores
```

### Run Only Fast Tests (exclude slow/integration tests)

```bash
pytest -m "not integration and not performance"
```

### Run Only Integration Tests

```bash
pytest -m integration
```

### Run Only Performance Tests

```bash
pytest -m performance
```

## Test Markers

Tests are organized with markers:

- `@pytest.mark.integration` - Requires external services (Kafka, Redis, PostgreSQL)
- `@pytest.mark.performance` - Performance benchmarks
- `@pytest.mark.slow` - Tests taking >1 second

## Test Structure

```
tests/
├── conftest.py              # Shared fixtures and test configuration
├── pytest.ini               # Pytest configuration
├── requirements.txt         # Test dependencies
├── test_video_transcoder.py # Video processing tests
├── test_storage_manager.py  # Storage layer tests
├── test_recommendation_engine.py  # ML recommendation tests
├── test_analytics.py        # Real-time analytics tests
└── data/                    # Test data (generated)
```

## Fixtures

Shared fixtures available in all tests (from `conftest.py`):

### File Fixtures
- `test_data_dir` - Temporary directory for test files
- `sample_video_file` - Sample video for transcoding tests

### Mock Fixtures
- `mock_s3_client` - Mocked boto3 S3 client
- `mock_redis_client` - Mocked Redis client
- `mock_postgres_conn` - Mocked PostgreSQL connection
- `mock_kafka_producer` - Mocked Kafka producer
- `mock_kafka_consumer` - Mocked Kafka consumer

### Data Fixtures
- `sample_playback_event` - Sample playback event for analytics
- `sample_viewing_history` - Sample viewing history for recommendations
- `sample_content_metadata` - Sample content metadata

## Writing New Tests

### Example Test

```python
import pytest
from pathlib import Path

def test_example(test_data_dir, mock_s3_client):
    """Test description"""
    # Arrange
    test_file = test_data_dir / 'test.txt'
    test_file.write_text('Hello')

    # Act
    result = some_function(test_file)

    # Assert
    assert result is True
```

### Using Markers

```python
@pytest.mark.integration
def test_real_database():
    """Test requiring real database"""
    pass

@pytest.mark.performance
def test_latency():
    """Performance benchmark test"""
    import time
    start = time.time()
    # ... operation ...
    latency = time.time() - start
    assert latency < 0.1  # <100ms
```

## Continuous Integration

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:14
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

      redis:
        image: redis:7
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r tests/requirements.txt

      - name: Run tests
        run: pytest --cov=. --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

## Troubleshooting

### FFmpeg Not Found

Some video transcoder tests require FFmpeg:

```bash
# Ubuntu/Debian
sudo apt-get install ffmpeg

# macOS
brew install ffmpeg

# Or skip integration tests
pytest -m "not integration"
```

### Import Errors

Ensure project modules are in Python path:

```bash
export PYTHONPATH="${PYTHONPATH}:/path/to/projeto-netflix-clone"
```

Or run tests from project root:

```bash
python -m pytest tests/
```

### Slow Tests

Run only fast unit tests:

```bash
pytest -m "not slow and not integration"
```

Or increase timeout:

```bash
pytest --timeout=600  # 10 minutes
```

## Test Metrics

### Expected Performance
- **Total test runtime**: <30 seconds (unit tests only)
- **With integration tests**: <2 minutes
- **Test coverage target**: >80%

### Current Status
- ✅ 75+ tests passing
- ✅ All major modules covered
- ✅ Mock-based tests (no external dependencies for unit tests)
- ✅ Integration tests available for end-to-end validation

## Contributing

When adding new features:

1. Write tests first (TDD)
2. Ensure >80% code coverage
3. Add integration tests for external services
4. Mark slow tests with `@pytest.mark.slow`
5. Run full test suite before committing

```bash
# Pre-commit checklist
pytest --cov=. --cov-report=term
black .
flake8 .
mypy .
```
