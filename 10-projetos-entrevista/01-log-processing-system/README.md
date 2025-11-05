# Log Processing System

**Pergunta de Entrevista:** "Como você processaria 10GB de logs por segundo de forma eficiente?"

## 📋 Requisitos

### Funcionais
1. **Parse de Logs**: Suportar múltiplos formatos (Apache, Nginx, JSON, custom)
2. **Agregação**: Métricas em janelas de tempo (1min, 5min, 1hora)
3. **Detecção de Anomalias**: Identificar padrões anormais
4. **Persistência**: Escrita eficiente para storage (batch writes)

### Não-Funcionais
1. **Throughput**: Processar 10GB/s (≈ 100K logs/sec @ 100KB/log)
2. **Latência**: <100ms para agregações em tempo real
3. **Memory**: <2GB para 1 hora de dados na memória
4. **CPU**: <50% de uma CPU por 10K logs/sec

## 🎯 Back-of-the-Envelope Calculations

```
# Assumptions
Tamanho médio de log: 100 bytes
Logs por segundo: 100,000
Tamanho total: 100,000 * 100 bytes = 10 MB/s = 36 GB/hour

# Memory para agregações
Unique IPs: ~10K
Unique URLs: ~100K
Unique User-Agents: ~1K
Agregações por métrica: 8 bytes (long) + 50 bytes (key)
Total por minuto: 111K * 58 bytes ≈ 6.4 MB
Total por hora (60 min): 6.4 MB * 60 = 384 MB ✅

# CPU
Parse com regex: ~1000 logs/sec por core
Parse com split: ~10,000 logs/sec por core
Para 100K logs/sec: precisa 10-100 cores dependendo da estratégia
```

## 🏗️ Arquitetura

```
┌─────────────┐
│  Log Source │  (Apache, Nginx, App logs)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Parser    │  Regex vs Split (10x difference)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Aggregator │  Sliding windows (1min, 5min, 1h)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Detector  │  Anomaly detection (threshold, z-score)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Writer    │  Batch writes (1000 logs/batch)
└─────────────┘
```

## 🔧 Implementação

### 1. Log Parser (log_parser.py)

**Desafio**: Parse eficiente é crítico para performance

**Estratégias**:
- ❌ **Regex**: Lento (1K logs/sec)
- ✅ **Split + Manual**: Rápido (10K logs/sec)
- ✅✅ **Compilar Regex**: Meio-termo (5K logs/sec)

```python
# Apache Log Format
# 127.0.0.1 - - [10/Oct/2000:13:55:36 -0700] "GET /index.html HTTP/1.0" 200 2326

# Naive Regex (LENTO - 1K logs/sec)
pattern = r'(\d+\.\d+\.\d+\.\d+) .* \[(.*?)\] "(.*?)" (\d+) (\d+)'

# Otimizado: Split (RÁPIDO - 10K logs/sec)
parts = line.split(' ')
ip = parts[0]
timestamp = parts[3][1:]  # Remove '['
method_path = parts[5:8]
status = int(parts[8])
size = int(parts[9])
```

### 2. Aggregator (aggregator.py)

**Desafio**: Manter agregações em múltiplas janelas de tempo

**Data Structure**:
```python
# Sliding Window com Deque
from collections import deque, defaultdict

class SlidingWindowAggregator:
    def __init__(self, window_size_sec=60):
        self.windows = defaultdict(deque)  # key -> [(timestamp, value), ...]
        self.aggregations = defaultdict(int)  # key -> sum

    def add(self, key, value, timestamp):
        # O(1) - Adiciona ao final
        self.windows[key].append((timestamp, value))
        self.aggregations[key] += value

        # Remove valores antigos - O(k) onde k é # de valores expirados
        cutoff = timestamp - self.window_size_sec
        while self.windows[key] and self.windows[key][0][0] < cutoff:
            old_ts, old_val = self.windows[key].popleft()
            self.aggregations[key] -= old_val
```

**Complexidade**:
- Add: O(1) amortizado
- Get: O(1)
- Memory: O(n) onde n = eventos na janela

### 3. Anomaly Detector (anomaly_detector.py)

**Estratégias**:

**a) Threshold-based (Simples)**
```python
if current_rate > threshold:
    alert("High rate detected")
```

**b) Z-Score (Estatístico)**
```python
# Detecta quando valor está X desvios-padrão da média
z_score = (current - mean) / std_dev
if abs(z_score) > 3:  # 3-sigma rule
    alert("Anomaly detected")
```

**c) Moving Average (Suavizado)**
```python
# Detecta mudanças bruscas
if abs(current - moving_avg) > threshold * moving_avg:
    alert("Spike detected")
```

### 4. Writer (writer.py)

**Desafio**: Escrita eficiente para minimizar I/O

**Estratégias**:
```python
# ❌ Write-per-log (LENTO - 100 logs/sec)
for log in logs:
    file.write(log)  # 1 I/O operation per log

# ✅ Batch Write (RÁPIDO - 10K logs/sec)
buffer = []
for log in logs:
    buffer.append(log)
    if len(buffer) >= BATCH_SIZE:  # e.g., 1000
        file.write('\n'.join(buffer))  # 1 I/O per 1000 logs
        buffer.clear()

# ✅✅ Async Write (MUITO RÁPIDO - 50K logs/sec)
import asyncio
import aiofiles

async def write_batch(logs):
    async with aiofiles.open('output.log', mode='a') as f:
        await f.write('\n'.join(logs))
```

## 📊 Benchmarks

| Estratégia | Throughput | Latência | Memory |
|------------|------------|----------|--------|
| Regex Parse | 1K logs/sec | 1ms | 50 MB |
| Split Parse | 10K logs/sec | 0.1ms | 50 MB |
| Batch Write (100) | 5K logs/sec | 20ms | 10 MB |
| Batch Write (1000) | 10K logs/sec | 100ms | 100 MB |
| Async Write | 50K logs/sec | 20ms | 100 MB |

## 🎯 Otimizações

### 1. Multi-threading
```python
from concurrent.futures import ThreadPoolExecutor

# Processar logs em paralelo
with ThreadPoolExecutor(max_workers=10) as executor:
    futures = [executor.submit(process_log, log) for log in logs]
    results = [f.result() for f in futures]
```

**Trade-off**: GIL em Python limita paralelismo. Melhor usar multiprocessing.

### 2. Multi-processing
```python
from multiprocessing import Pool

# Processar logs em múltiplos processos
with Pool(processes=10) as pool:
    results = pool.map(process_log_batch, log_batches)
```

**Ganho**: 10x throughput (se 10 cores disponíveis)

### 3. Memory-Mapped Files
```python
import mmap

# Ler arquivo sem carregar tudo na memória
with open('huge.log', 'r+b') as f:
    with mmap.mmap(f.fileno(), 0) as mmap_obj:
        for line in iter(mmap_obj.readline, b""):
            process_line(line)
```

**Ganho**: Processa arquivos de 100GB com <1GB RAM

### 4. Columnar Storage (Parquet)
```python
import pyarrow.parquet as pq

# Escrever em formato columnar para queries rápidas
df.to_parquet('logs.parquet', compression='snappy')

# Ler apenas colunas necessárias
df = pq.read_table('logs.parquet', columns=['ip', 'status']).to_pandas()
```

**Ganho**: 10x compressão, 10x velocidade de leitura para queries analíticas

## 🚀 Scaling para 100GB/s

### Horizontal Scaling

```
┌─────────────┐
│   Kafka     │  (Sharded por IP hash)
│  (100 parts)│
└──────┬──────┘
       │
       ├───────────────────────────┐
       ▼                           ▼
┌─────────────┐            ┌─────────────┐
│  Consumer 1 │            │  Consumer N │  (100 consumers)
│  (Spark)    │            │  (Spark)    │
└──────┬──────┘            └──────┬──────┘
       │                           │
       └───────────────────────────┘
                   ▼
           ┌─────────────┐
           │  S3/HDFS    │  (Parquet format)
           └─────────────┘
```

**Capacidade**:
- Kafka: 100 partitions × 1GB/s = 100 GB/s
- Spark: 100 executors × 1GB/s = 100 GB/s
- S3: Unlimited throughput com prefixes diferentes

### Estimativa de Recursos

```python
# Para 100GB/s (1M logs/sec @ 100KB/log)

# Kafka
Partitions: 100
Brokers: 10 (cada broker 10GB/s)
Retenção: 7 dias × 100GB/s × 86400 sec = 60 PB

# Spark
Executors: 100
Cores por executor: 4
Memory por executor: 16 GB
Total: 400 cores, 1.6 TB memory

# Storage (S3)
Daily: 100GB/s × 86400 sec = 8.6 PB/dia
Compressão Snappy: 3x → 2.9 PB/dia
Mensal: 87 PB
Anual: 1 EB (ExaByte!)

# Custo
S3: $0.023/GB × 87 PB = $2M/mês
Spark (100 r5.4xlarge): $1.00/hr × 100 × 730 hrs = $73K/mês
Total: ~$2.1M/mês
```

## 🧪 Testes

```bash
# Executar testes
pytest tests/ -v

# Benchmarks
python benchmarks/benchmark_parser.py
python benchmarks/benchmark_aggregator.py

# Teste de carga
python benchmarks/load_test.py --rate 10000  # 10K logs/sec
```

## 📝 Perguntas de Follow-up

### Q1: Como garantir exactly-once processing?

**Resposta**:
```python
# Usar idempotent writes + offset tracking

# 1. Cada log tem ID único
log_id = f"{timestamp}_{ip}_{sequence}"

# 2. Track offset no Kafka
consumer.commit()  # Commit apenas após sucesso

# 3. Deduplicação no sink
# Usar UPSERT baseado em log_id
INSERT INTO logs (...) ON CONFLICT (log_id) DO NOTHING
```

### Q2: Como lidar com logs out-of-order?

**Resposta**:
```python
# Usar watermark + grace period

# 1. Watermark: último timestamp processado
watermark = max_timestamp - grace_period  # e.g., -5min

# 2. Buffer de logs tardios
late_buffer = []  # Logs com timestamp < watermark

# 3. Processar tardios em batch separado
if timestamp < watermark:
    late_buffer.append(log)
else:
    process(log)
```

### Q3: Como otimizar para queries analíticas?

**Resposta**:
```python
# 1. Particionamento por data
s3://bucket/year=2024/month=01/day=15/part-00001.parquet

# 2. Compressão columnar
# Parquet com Snappy: 3x compressão

# 3. Pré-agregações
# Materializar agregações comuns (por hora, por URL, por status)

# 4. Indexação
# Bloom filters para IP lookups
# Z-ordering para multi-dimensional queries
```

## 🎓 Conceitos-Chave

1. **String Parsing**: Regex vs Split (10x difference)
2. **Sliding Windows**: Deque para O(1) add/remove
3. **Batch Processing**: Reduzir I/O operations
4. **Async I/O**: aiofiles para escrita não-bloqueante
5. **Columnar Storage**: Parquet para analytics
6. **Partitioning**: Por data para queries eficientes
7. **Compression**: Snappy (rápido) vs Gzip (compacto)
8. **Multiprocessing**: Contornar GIL do Python

## ⚠️ Red Flags na Entrevista

❌ **Usar regex sem compilar**
❌ **Não mencionar batch processing**
❌ **Ignorar memory footprint**
❌ **Não considerar paralelização**
❌ **Esquecer de tratar logs mal-formados**
❌ **Não falar sobre monitoramento**

✅ **Bom candidato fala sobre**:
- Parse otimizado (split vs regex)
- Batch writes
- Memory-efficient aggregations
- Horizontal scaling (Kafka + Spark)
- Monitoring e alerting

## 🏆 Solução Completa

Ver arquivos:
- `log_parser.py` - Parser otimizado
- `aggregator.py` - Sliding window aggregations
- `anomaly_detector.py` - Detecção de anomalias
- `writer.py` - Batch writer
- `main.py` - Orquestração completa
- `benchmarks/` - Performance tests

**Tempo de implementação**: 45-60 minutos
**Dificuldade**: ⭐⭐ (Medium)
