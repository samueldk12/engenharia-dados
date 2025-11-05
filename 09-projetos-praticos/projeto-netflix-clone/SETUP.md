# 🚀 Setup Guide - Netflix Clone

## 📋 Pré-requisitos

### Ferramentas Necessárias

```bash
# 1. Docker & Docker Compose
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo apt-get install docker-compose-plugin

# 2. Python 3.10+
sudo apt-get install python3.10 python3-pip

# 3. FFmpeg (para processamento de vídeo)
sudo apt-get install ffmpeg libvmaf-dev

# 4. AWS CLI (opcional, para S3)
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# 5. Git
sudo apt-get install git
```

### Requisitos de Hardware

**Desenvolvimento (mínimo):**
- CPU: 4 cores
- RAM: 16GB
- Disk: 50GB SSD
- Network: 100 Mbps

**Produção (recomendado):**
- CPU: 32+ cores
- RAM: 128GB+
- Disk: 1TB+ NVMe SSD
- Network: 10 Gbps

---

## 🐳 Quick Start com Docker Compose

### 1. Clone o Repositório

```bash
git clone https://github.com/your-repo/netflix-clone.git
cd netflix-clone
```

### 2. Configurar Variáveis de Ambiente

```bash
# Copiar template
cp .env.example .env

# Editar variáveis
nano .env
```

**.env:**
```bash
# Database
POSTGRES_USER=netflix
POSTGRES_PASSWORD=strong_password_here
POSTGRES_DB=netflix

# Redis
REDIS_PASSWORD=redis_password_here

# Kafka
KAFKA_BOOTSTRAP_SERVERS=localhost:9092

# AWS (opcional)
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_DEFAULT_REGION=us-east-1

# S3 Buckets
S3_RAW_CONTENT_BUCKET=netflix-raw-content
S3_ENCODED_CONTENT_BUCKET=netflix-encoded-content
S3_CDN_BUCKET=netflix-cdn-content

# MinIO (S3 local)
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin

# Airflow
AIRFLOW__CORE__FERNET_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")

# Monitoring
GRAFANA_ADMIN_PASSWORD=admin
```

### 3. Iniciar Infraestrutura

```bash
# Subir todos os serviços
docker-compose up -d

# Verificar status
docker-compose ps

# Ver logs
docker-compose logs -f
```

### 4. Acessar Serviços

| Serviço | URL | Credenciais |
|---------|-----|-------------|
| **Airflow** | http://localhost:8081 | airflow / airflow |
| **Grafana** | http://localhost:3000 | admin / admin |
| **Kafka UI** | http://localhost:8080 | - |
| **MinIO** | http://localhost:9001 | minioadmin / minioadmin |
| **Prometheus** | http://localhost:9090 | - |

### 5. Criar Tópicos Kafka

```bash
# Entrar no container do Kafka
docker exec -it netflix-kafka bash

# Criar tópicos
kafka-topics --create --topic video.playback.events \
  --bootstrap-server localhost:9092 \
  --partitions 100 \
  --replication-factor 1

kafka-topics --create --topic user.interaction.events \
  --bootstrap-server localhost:9092 \
  --partitions 50 \
  --replication-factor 1

kafka-topics --create --topic system.error.events \
  --bootstrap-server localhost:9092 \
  --partitions 10 \
  --replication-factor 1

# Listar tópicos
kafka-topics --list --bootstrap-server localhost:9092
```

### 6. Inicializar Database

```bash
# PostgreSQL já inicializa com schema.sql automaticamente
# Verificar se tabelas foram criadas:

docker exec -it netflix-postgres psql -U netflix -d netflix -c "\dt"
```

### 7. Configurar MinIO (S3 Local)

```bash
# Acessar MinIO Console: http://localhost:9001
# Login: minioadmin / minioadmin

# Criar buckets via CLI
docker exec -it netflix-minio mc alias set myminio http://localhost:9000 minioadmin minioadmin

docker exec -it netflix-minio mc mb myminio/netflix-raw-content
docker exec -it netflix-minio mc mb myminio/netflix-encoded-content
docker exec -it netflix-minio mc mb myminio/netflix-cdn-content

# Configurar políticas públicas para CDN bucket
docker exec -it netflix-minio mc anonymous set download myminio/netflix-cdn-content
```

---

## 📦 Instalação Python Packages

### Criar Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
.\venv\Scripts\activate  # Windows
```

### Instalar Dependências

```bash
# Core dependencies
pip install -r requirements.txt

# requirements.txt:
```

```txt
# Data Processing
pandas==2.1.0
numpy==1.25.0
polars==0.19.0

# Cloud Storage
boto3==1.28.0
google-cloud-storage==2.10.0

# Databases
psycopg2-binary==2.9.7
cassandra-driver==3.28.0
redis==5.0.0

# Messaging
kafka-python==2.0.2
confluent-kafka==2.2.0

# Streaming (opcional - Flink requer Java)
apache-flink==1.18.0

# ML & Analytics
scikit-learn==1.3.0
torch==2.0.1
lightgbm==4.1.0

# Workflow
apache-airflow==2.7.3
apache-airflow-providers-amazon==8.5.0
apache-airflow-providers-postgres==5.6.0

# Monitoring
prometheus-client==0.17.1
```

---

## 🎬 Testando o Pipeline de Vídeo

### 1. Upload Vídeo de Teste

```bash
# Download sample video
wget https://sample-videos.com/video123/mp4/720/big_buck_bunny_720p_1mb.mp4 \
  -O test_video.mp4

# Upload para MinIO (simula S3)
python 04-camada-armazenamento/storage_manager.py upload \
  --file test_video.mp4 \
  --bucket netflix-raw-content \
  --key raw-content/test_video.mp4
```

### 2. Trigger Airflow DAG

```bash
# Via Web UI: http://localhost:8081
# Ou via CLI:

docker exec -it netflix-airflow-scheduler \
  airflow dags trigger video_processing_pipeline \
  -c '{"s3_key": "raw-content/test_video.mp4"}'
```

### 3. Monitorar Progresso

```bash
# Ver logs do DAG
docker exec -it netflix-airflow-scheduler \
  airflow tasks logs video_processing_pipeline validate_source_video $(date +%Y-%m-%d)

# Ver logs em tempo real
docker-compose logs -f airflow-scheduler
```

### 4. Verificar Output

```bash
# Listar arquivos transcodificados no MinIO
docker exec -it netflix-minio mc ls myminio/netflix-encoded-content/content/

# Output esperado:
# content/test_video/
#   ├── 4k/
#   │   ├── output.m3u8
#   │   ├── segment_00000.ts
#   │   └── ...
#   ├── 1080p/
#   ├── 720p/
#   ├── 480p/
#   ├── 360p/
#   └── master.m3u8
```

---

## 📊 Testando Analytics em Tempo Real

### 1. Enviar Eventos de Teste

```python
# run_test_events.py
from kafka import KafkaProducer
import json
import time
import random

producer = KafkaProducer(
    bootstrap_servers='localhost:9092',
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

# Simular 100 sessões de playback
for i in range(100):
    session_id = f"test_session_{i}"
    content_id = random.randint(1, 10)
    user_id = random.randint(1, 1000)

    # Start event
    producer.send('video.playback.events', {
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
        'device_type': 'web',
        'country': 'US',
        'cdn_pop': 'us-east-1'
    })

    # Heartbeat events
    for j in range(5):
        time.sleep(0.1)  # Simulated 30s
        producer.send('video.playback.events', {
            'event_type': 'heartbeat',
            'user_id': user_id,
            'profile_id': user_id * 10,
            'content_id': content_id,
            'session_id': session_id,
            'timestamp': int(time.time() * 1000),
            'position_sec': (j + 1) * 30.0,
            'bitrate_kbps': random.randint(4000, 6000),
            'resolution': '1080p',
            'buffer_health_sec': random.uniform(10, 20),
            'buffering_events': 0,
            'dropped_frames': random.randint(0, 3),
            'device_type': 'web',
            'country': 'US',
            'cdn_pop': 'us-east-1'
        })

    # Stop event
    producer.send('video.playback.events', {
        'event_type': 'stop',
        'user_id': user_id,
        'profile_id': user_id * 10,
        'content_id': content_id,
        'session_id': session_id,
        'timestamp': int(time.time() * 1000),
        'position_sec': 150.0,
        'bitrate_kbps': 5000,
        'resolution': '1080p',
        'buffer_health_sec': 15.0,
        'buffering_events': 0,
        'dropped_frames': 2,
        'device_type': 'web',
        'country': 'US',
        'cdn_pop': 'us-east-1'
    })

producer.flush()
print("✓ Sent 100 test sessions")
```

```bash
python run_test_events.py
```

### 2. Verificar Métricas no Redis

```bash
# Conectar ao Redis
docker exec -it netflix-redis redis-cli

# Ver concurrent viewers
GET concurrent_viewers:1
GET concurrent_viewers:2

# Ver QoE metrics
HGETALL qoe_metrics:1

# Ver todas as keys
KEYS *
```

### 3. Ver Dashboard no Grafana

```
1. Acessar: http://localhost:3000
2. Login: admin / admin
3. Add Data Source → Redis
   - Host: redis:6379
4. Import dashboard de ./monitoring/grafana/dashboards/
```

---

## 🎯 Testando Sistema de Recomendação

### 1. Gerar Dados de Viewing History

```python
# generate_viewing_data.py
import psycopg2
import random
from datetime import datetime, timedelta

conn = psycopg2.connect(
    host='localhost',
    port=5432,
    user='netflix',
    password='strong_password_here',
    database='netflix'
)

cursor = conn.cursor()

# Gerar 10K interações
for i in range(10000):
    user_id = random.randint(1, 1000)
    content_id = random.randint(1, 500)
    started_at = datetime.now() - timedelta(days=random.randint(0, 30))

    cursor.execute("""
        INSERT INTO viewing_history_hot (
            user_id, profile_id, content_id, session_id,
            started_at, watch_duration_sec, watch_percentage,
            avg_bitrate_kbps, qoe_score
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
    """, (
        user_id,
        user_id * 10,
        content_id,
        f'session_{i}',
        started_at,
        random.randint(300, 7200),
        random.uniform(0.3, 1.0),
        random.randint(2000, 6000),
        random.uniform(70, 100)
    ))

conn.commit()
print("✓ Generated 10K viewing records")
```

### 2. Treinar Modelo de Recomendação

```python
# train_recommendation_model.py
from recommendation_engine import RecommendationEngine
import pandas as pd
import psycopg2

# Load viewing data
conn = psycopg2.connect('postgresql://netflix:password@localhost:5432/netflix')

interactions = pd.read_sql("""
    SELECT
        user_id,
        content_id,
        watch_percentage * 5 as rating
    FROM viewing_history_hot
    WHERE started_at >= NOW() - INTERVAL '30 days'
""", conn)

# Train model
engine = RecommendationEngine()
engine.train_collaborative_filtering(interactions)

# Save model
engine.matrix_factorization.save('models/cf_model.pkl')

print("✓ Model trained and saved")
```

### 3. Obter Recomendações

```python
# get_recommendations.py
from recommendation_engine import RecommendationEngine, UserContext

# Load model
engine = RecommendationEngine()
engine.matrix_factorization = MatrixFactorization.load('models/cf_model.pkl')

# Get recommendations
context = UserContext(
    user_id=123,
    profile_id=1230,
    country='US',
    device_type='smart_tv',
    time_of_day='evening',
    subscription_tier='premium'
)

recs = engine.recommend(user_id=123, context=context, n=20)

print("Top 10 Recommendations:")
for rec in recs[:10]:
    print(f"{rec.rank}. {rec.title} (score: {rec.score:.2f}) - {rec.reason}")
```

---

## 📈 Monitoramento e Alertas

### Prometheus Targets

Editar `monitoring/prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres:5432']

  - job_name: 'redis'
    static_configs:
      - targets: ['redis:6379']

  - job_name: 'kafka'
    static_configs:
      - targets: ['kafka:9092']

  - job_name: 'analytics-consumer'
    static_configs:
      - targets: ['analytics-consumer:8000']
```

### Alerting Rules

Criar `monitoring/alerts.yml`:

```yaml
groups:
  - name: video_quality
    rules:
      - alert: HighVideoStartTime
        expr: vst_p95_ms > 3000
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High video start time"
          description: "VST p95 is {{ $value }}ms"

      - alert: HighRebuffering
        expr: rebuffering_ratio > 0.02
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "High rebuffering rate"
          description: "Rebuffering ratio is {{ $value }}"
```

---

## 🧪 Testes

### Unit Tests

```bash
# Rodar todos os testes
pytest

# Com coverage
pytest --cov=. --cov-report=html

# Testes específicos
pytest tests/test_recommendation_engine.py
pytest tests/test_storage_manager.py
```

### Integration Tests

```bash
# Testar pipeline completo
python tests/integration/test_video_pipeline.py

# Testar analytics
python tests/integration/test_analytics_pipeline.py
```

### Load Tests

```bash
# Simular 100K eventos/segundo
python tests/load_test_events.py --rate 100000 --duration 60

# Simular 1000 uploads simultâneos
python tests/load_test_uploads.py --files 1000 --parallel 50
```

---

## 🚀 Deploy em Produção

### AWS

```bash
# 1. Criar infraestrutura com Terraform
cd terraform/aws
terraform init
terraform plan
terraform apply

# 2. Deploy Airflow no EKS
kubectl apply -f k8s/airflow/

# 3. Deploy Analytics no ECS
aws ecs create-service --cli-input-json file://ecs/analytics-service.json
```

### GCP

```bash
# 1. Criar projeto
gcloud projects create netflix-clone

# 2. Deploy no GKE
gcloud container clusters create netflix-cluster
kubectl apply -f k8s/
```

---

## 📚 Troubleshooting

### Problema: Kafka não conecta

```bash
# Verificar se Kafka está rodando
docker ps | grep kafka

# Ver logs
docker logs netflix-kafka

# Testar conectividade
docker exec -it netflix-kafka kafka-broker-api-versions --bootstrap-server localhost:9092
```

### Problema: Airflow DAG não aparece

```bash
# Verificar syntax do DAG
python 03-ingestao-processamento/dags/video_processing_pipeline.py

# Refresh DAGs
docker exec -it netflix-airflow-scheduler airflow dags list-import-errors
```

### Problema: Out of Memory

```bash
# Aumentar memory limits no docker-compose.yml
services:
  postgres:
    mem_limit: 4g

  cassandra:
    mem_limit: 8g

# Ou aumentar Docker daemon memory
```

---

## 📖 Documentação Completa

- [Arquitetura](01-arquitetura/README.md)
- [Modelagem de Dados](02-modelagem-dados/README.md)
- [Pipeline de Vídeo](03-ingestao-processamento/README.md)
- [Storage Layer](04-camada-armazenamento/README.md)
- [Sistema de Recomendação](06-sistema-recomendacao/README.md)
- [Analytics](07-analytics-metricas/README.md)

---

**Setup completo! Sistema pronto para processar vídeos em escala Netflix! 🚀**
