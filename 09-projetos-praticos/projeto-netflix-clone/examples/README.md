# Netflix Clone - Practical Examples

Hands-on examples demonstrating key features of the Netflix Clone project.

## Examples

### 1. Upload and Transcode Video (`01_upload_and_transcode_video.py`)

Complete video ingestion pipeline from source to CDN-ready HLS streams.

**What it demonstrates:**
- Uploading source video to S3
- Transcoding to multiple resolutions (360p - 4K)
- Generating HLS adaptive bitrate streams
- Quality validation with VMAF
- CDN distribution
- Database updates

**Requirements:**
- FFmpeg installed
- S3 bucket (or MinIO locally)
- Source video file

**Usage:**
```bash
python 01_upload_and_transcode_video.py
```

**Expected output:**
- 5 transcoded resolutions (if source is 4K+)
- HLS master playlist
- VMAF quality scores (>85 is excellent)
- CDN URLs for streaming

---

### 2. Generate Personalized Recommendations (`02_generate_recommendations.py`)

End-to-end recommendation pipeline using collaborative filtering.

**What it demonstrates:**
- Training Matrix Factorization model
- Generating top-N recommendations
- Model evaluation (RMSE, MAE)
- Diversification with MMR algorithm
- Recommendation explanations
- Performance benchmarking
- Caching strategy

**Requirements:**
- NumPy, Pandas
- Sample viewing data (auto-generated)

**Usage:**
```bash
python 02_generate_recommendations.py
```

**Expected output:**
- Trained model (RMSE ~0.8)
- Top-20 personalized recommendations
- Diversified results balancing relevance and variety
- Latency <50ms for real-time serving

---

### 3. Real-time Analytics (`03_realtime_analytics.py`)

Real-time video playback analytics with Kafka streaming.

**What it demonstrates:**
- Sending playback events to Kafka
- Real-time event processing
- Concurrent viewer tracking
- QoE (Quality of Experience) scoring
- Metrics publishing to Redis
- Session persistence to PostgreSQL
- Alert generation

**Requirements:**
- Kafka running (docker-compose)
- Redis running
- PostgreSQL running

**Usage:**
```bash
# Start services first
docker-compose up -d kafka redis postgres

# Run analytics demo
python 03_realtime_analytics.py
```

**Expected output:**
- 5 simulated playback sessions
- Real-time concurrent viewer counts
- QoE scores (0-100) per content
- Session statistics in PostgreSQL

---

## Setup

### Prerequisites

Install project dependencies:

```bash
pip install -r ../requirements.txt
```

### Start Local Services

For examples 3, start Docker services:

```bash
cd ..
docker-compose up -d
```

This starts:
- Kafka (localhost:9092)
- Redis (localhost:6379)
- PostgreSQL (localhost:5432)
- MinIO / S3 (localhost:9000)

### Configuration

#### Example 1 (Video Transcoding)

Update these variables in the script:

```python
source_video = Path('/path/to/your/movie.mp4')  # Your video file

storage_config = StorageConfig(
    provider='s3',
    bucket='your-bucket-name',
    region='us-east-1',
    access_key='your-key',     # Or use AWS_ACCESS_KEY_ID env var
    secret_key='your-secret'   # Or use AWS_SECRET_ACCESS_KEY env var
)
```

For local testing with MinIO:

```python
storage_config = StorageConfig(
    provider='s3',
    bucket='netflix-content',
    region='us-east-1',
    endpoint_url='http://localhost:9000',
    access_key='minioadmin',
    secret_key='minioadmin'
)
```

#### Example 2 (Recommendations)

No configuration needed - uses auto-generated sample data.

#### Example 3 (Analytics)

Update connection strings if needed:

```python
KAFKA_BOOTSTRAP_SERVERS = 'localhost:9092'
REDIS_HOST = 'localhost'
POSTGRES_CONN_STR = 'postgresql://netflix:netflix123@localhost:5432/netflix'
```

## Running Examples

### Quick Test (No Services Required)

```bash
# Recommendation example (pure Python)
python 02_generate_recommendations.py
```

### With Local Services

```bash
# Start services
docker-compose up -d

# Wait for services to be ready (~30 seconds)
docker-compose ps

# Run analytics example
python 03_realtime_analytics.py
```

### Video Transcoding

Requires FFmpeg and real video file:

```bash
# Check FFmpeg
ffmpeg -version

# Update source_video path in script
# Then run
python 01_upload_and_transcode_video.py
```

## Expected Results

### Example 1: Video Transcoding

```
PIPELINE COMPLETED SUCCESSFULLY!
Content ID 12345 is now ready for streaming:
  ✓ Source uploaded to S3
  ✓ Transcoded to 5 resolutions
  ✓ Quality validated (VMAF 89.2/100)
  ✓ HLS playlists uploaded
  ✓ Database updated
```

### Example 2: Recommendations

```
RECOMMENDATION PIPELINE COMPLETED!
Summary:
  ✓ Model trained on 4,847 interactions
  ✓ RMSE: 0.8234
  ✓ Generated 20 recommendations for User 1
  ✓ Diversified to balance relevance and variety
  ✓ Latency: 12.34ms (<50ms target)
  ✓ Ready for caching and serving
```

### Example 3: Real-time Analytics

```
REAL-TIME ANALYTICS DEMO COMPLETED!
What we demonstrated:
  ✓ Sent playback events to Kafka
  ✓ Processed events in real-time
  ✓ Calculated QoE scores
  ✓ Tracked concurrent viewers
  ✓ Stored session data in PostgreSQL
  ✓ Published metrics to Redis
```

## Troubleshooting

### FFmpeg Not Found

```bash
# Ubuntu/Debian
sudo apt-get install ffmpeg

# macOS
brew install ffmpeg

# Verify
ffmpeg -version
```

### Kafka Connection Error

```bash
# Check Kafka is running
docker-compose ps kafka

# Check logs
docker-compose logs kafka

# Restart if needed
docker-compose restart kafka
```

### Redis Connection Error

```bash
# Check Redis
docker-compose ps redis

# Test connection
redis-cli ping  # Should return "PONG"
```

### PostgreSQL Connection Error

```bash
# Check PostgreSQL
docker-compose ps postgres

# Test connection
psql postgresql://netflix:netflix123@localhost:5432/netflix
```

### Import Errors

```bash
# Add project to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)/.."

# Or install project in editable mode
cd ..
pip install -e .
```

### S3/MinIO Connection

For local MinIO:

```bash
# Check MinIO
docker-compose ps minio

# Access web UI
open http://localhost:9001

# Credentials: minioadmin / minioadmin
```

## Learning Objectives

After running these examples, you should understand:

1. **Video Pipeline**
   - Multi-resolution transcoding
   - HLS adaptive bitrate streaming
   - Quality metrics (VMAF)
   - CDN distribution

2. **Recommendations**
   - Collaborative filtering algorithms
   - Training and evaluation
   - Real-time serving (<50ms)
   - Diversification strategies

3. **Real-time Analytics**
   - Event streaming with Kafka
   - Stream processing
   - QoE calculation
   - Metrics aggregation

## Next Steps

1. Modify examples to use your own data
2. Integrate with production services (AWS, GCP)
3. Scale up (more content, more users)
4. Add monitoring and alerting
5. Implement A/B testing
6. Build dashboards (Grafana)

## Additional Resources

- [Video Processing README](../03-ingestao-processamento/README.md)
- [Storage Layer README](../04-camada-armazenamento/README.md)
- [Recommendation Engine README](../06-sistema-recomendacao/README.md)
- [Analytics README](../07-analytics-metricas/README.md)
- [Main Setup Guide](../SETUP.md)
