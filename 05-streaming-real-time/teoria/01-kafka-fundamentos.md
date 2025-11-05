# 📡 Apache Kafka: Streaming em Tempo Real

## 📋 Índice

1. [O que é Apache Kafka](#o-que-é-apache-kafka)
2. [Arquitetura do Kafka](#arquitetura-do-kafka)
3. [Producers e Consumers](#producers-e-consumers)
4. [Topics, Partitions e Offsets](#topics-partitions-e-offsets)
5. [Consumer Groups](#consumer-groups)
6. [Kafka Streams](#kafka-streams)
7. [Kafka Connect](#kafka-connect)
8. [Best Practices](#best-practices)

---

## O que é Apache Kafka

**Apache Kafka** é uma plataforma distribuída de streaming de eventos, usada para:
- **Messaging**: Comunicação assíncrona entre serviços
- **Event Streaming**: Processar streams de dados em tempo real
- **Log Aggregation**: Coletar logs de múltiplos serviços
- **Metrics**: Pipeline de métricas e monitoramento

### Por que Kafka?

**Características:**
- ⚡ **Alta throughput**: Milhões de mensagens/segundo
- 📈 **Escalável**: Horizontal scaling (adicionar brokers)
- 💾 **Durável**: Dados persistidos em disco
- 🔄 **Replicação**: Tolerância a falhas
- 🎯 **Low latency**: < 10ms (end-to-end)

**Comparação com outras soluções:**

| Feature | Kafka | RabbitMQ | AWS Kinesis |
|---------|-------|----------|-------------|
| **Throughput** | Muito Alto | Médio | Alto |
| **Latency** | < 10ms | < 5ms | ~200ms |
| **Durability** | Disk persist | Memory/Disk | S3 backing |
| **Order Guarantee** | Por partição | Por queue | Por shard |
| **Replay** | ✅ Sim | ❌ Não | ✅ Sim (7 dias) |
| **Use Case** | Event streaming | Task queues | AWS ecosystem |

---

## Arquitetura do Kafka

```
┌─────────────────────────────────────────────────────────┐
│                     Kafka Cluster                       │
│                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │   Broker 1   │  │   Broker 2   │  │   Broker 3   │ │
│  │              │  │              │  │              │ │
│  │  Topic: orders                                    │ │
│  │  ┌─────────┐ │  │ ┌─────────┐ │  │ ┌─────────┐  │ │
│  │  │Part 0   │ │  │ │Part 1   │ │  │ │Part 2   │  │ │
│  │  │(leader) │ │  │ │(replica)│ │  │ │(leader) │  │ │
│  │  └─────────┘ │  │ └─────────┘ │  │ └─────────┘  │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────┘
         ▲                                        │
         │                                        │
    ┌────┴────┐                              ┌───▼────┐
    │Producer │                              │Consumer│
    │(write)  │                              │(read)  │
    └─────────┘                              └────────┘
```

### Componentes

**1. Broker:**
- Servidor Kafka que armazena dados
- Cluster = múltiplos brokers
- Cada broker tem ID único

**2. Topic:**
- Categoria ou feed de mensagens
- Múltiplas partições
- Ex: `orders`, `payments`, `user-events`

**3. Partition:**
- Topic dividido em partições
- Cada partição = log ordenado imutável
- Partições permitem paralelismo

**4. ZooKeeper (legado) / KRaft (novo):**
- Coordenação do cluster
- Election de líderes
- Metadata do cluster

---

## Producers e Consumers

### Producer (Enviar Mensagens)

```python
from kafka import KafkaProducer
import json

# Criar producer
producer = KafkaProducer(
    bootstrap_servers=['localhost:9092'],
    value_serializer=lambda v: json.dumps(v).encode('utf-8'),
    key_serializer=lambda k: k.encode('utf-8') if k else None,
    acks='all',            # 0, 1, ou 'all'
    retries=3,
    max_in_flight_requests_per_connection=1,  # Garante ordem
    compression_type='gzip'  # None, 'gzip', 'snappy', 'lz4'
)

# Enviar mensagem
message = {
    'order_id': 12345,
    'customer_id': 67890,
    'total_amount': 299.99,
    'timestamp': '2024-01-15T10:30:00Z'
}

# Send async
future = producer.send(
    topic='orders',
    key='order-12345',      # Mesmo key vai para mesma partição
    value=message,
    partition=None,         # Auto-select ou especificar
    timestamp_ms=None       # Timestamp customizado
)

# Callback para sucesso/erro
def on_success(metadata):
    print(f"Message sent to {metadata.topic} partition {metadata.partition} offset {metadata.offset}")

def on_error(e):
    print(f"Error sending message: {e}")

future.add_callback(on_success)
future.add_errback(on_error)

# Flush (garantir envio antes de fechar)
producer.flush()
producer.close()

# Send síncrono (espera confirmação)
metadata = producer.send('orders', value=message).get(timeout=10)
```

### Producer Configs Importantes

```python
producer = KafkaProducer(
    # Acknowledgments
    acks='all',  # 0=no ack, 1=leader ack, all=all replicas ack
    
    # Batching (melhor throughput)
    batch_size=16384,      # Bytes por batch
    linger_ms=10,          # Espera 10ms para batching
    
    # Compression
    compression_type='gzip',  # Reduz network + storage
    
    # Retries
    retries=3,
    retry_backoff_ms=100,
    
    # Idempotence (exactly-once)
    enable_idempotence=True,  # Evita duplicatas
    max_in_flight_requests_per_connection=5,
    
    # Buffering
    buffer_memory=33554432,  # 32MB buffer
    max_block_ms=60000       # Timeout se buffer cheio
)
```

### Consumer (Ler Mensagens)

```python
from kafka import KafkaConsumer

# Criar consumer
consumer = KafkaConsumer(
    'orders',  # Topic(s)
    bootstrap_servers=['localhost:9092'],
    group_id='order-processor-group',
    auto_offset_reset='earliest',  # 'earliest', 'latest', 'none'
    enable_auto_commit=True,
    auto_commit_interval_ms=5000,
    value_deserializer=lambda m: json.loads(m.decode('utf-8')),
    key_deserializer=lambda k: k.decode('utf-8') if k else None,
    max_poll_records=500,          # Mensagens por poll
    session_timeout_ms=10000,      # Heartbeat timeout
    heartbeat_interval_ms=3000
)

# Consumir mensagens (blocking)
for message in consumer:
    print(f"Topic: {message.topic}")
    print(f"Partition: {message.partition}")
    print(f"Offset: {message.offset}")
    print(f"Key: {message.key}")
    print(f"Value: {message.value}")
    print(f"Timestamp: {message.timestamp}")
    
    # Processar mensagem
    process_order(message.value)

# Poll com timeout (non-blocking)
messages = consumer.poll(timeout_ms=1000, max_records=100)
for topic_partition, records in messages.items():
    for record in records:
        process(record)

# Commit manual
consumer.commit()  # Commit all
consumer.commit_async()  # Non-blocking commit

# Commit offset específico
from kafka import TopicPartition, OffsetAndMetadata
tp = TopicPartition('orders', 0)
consumer.commit({tp: OffsetAndMetadata(100, None)})

# Fechar
consumer.close()
```

---

## Topics, Partitions e Offsets

### Partitioning

```
Topic: orders (3 partições)

Partition 0:  [msg0] [msg3] [msg6] [msg9]  ...
Partition 1:  [msg1] [msg4] [msg7] [msg10] ...
Partition 2:  [msg2] [msg5] [msg8] [msg11] ...

Offset:        0      1      2      3       ...
```

**Por que particionar?**
- ✅ **Paralelismo**: Cada consumer processa partições diferentes
- ✅ **Escalabilidade**: Adicionar partições aumenta throughput
- ✅ **Ordem**: Garantida DENTRO de cada partição

### Partitioning Strategy

```python
# 1. Key-based partitioning (padrão)
# Mesmo key sempre vai para mesma partição
producer.send('orders', key='customer-123', value=msg)  # Hash(key) % num_partitions

# 2. Round-robin (se key=None)
producer.send('orders', value=msg)  # Distribui uniformemente

# 3. Custom partitioner
from kafka.partitioner import Partitioner

class CustomPartitioner(Partitioner):
    def partition(self, key, partitions_available, partitions_unavailable):
        # Lógica customizada
        if key.startswith('vip-'):
            return 0  # VIP customers vão para partição 0
        return hash(key) % len(partitions_available)

producer = KafkaProducer(partitioner=CustomPartitioner())
```

### Offsets

```python
# Offset = posição da mensagem na partição

# Ler do início
consumer = KafkaConsumer(auto_offset_reset='earliest')

# Ler apenas novas mensagens
consumer = KafkaConsumer(auto_offset_reset='latest')

# Seek para offset específico
from kafka import TopicPartition
tp = TopicPartition('orders', 0)
consumer.assign([tp])
consumer.seek(tp, 100)  # Começa do offset 100

# Seek para timestamp
import time
timestamp_ms = int(time.time() * 1000) - (86400 * 1000)  # 24h atrás
offsets = consumer.offsets_for_times({tp: timestamp_ms})
consumer.seek(tp, offsets[tp].offset)

# Seek para início/fim
consumer.seek_to_beginning(tp)
consumer.seek_to_end(tp)
```

---

## Consumer Groups

**Consumer Group** permite escalabilidade horizontal:

```
Topic: orders (4 partições)

┌────────────────────────────────────────┐
│      Consumer Group: processors        │
│                                        │
│  Consumer 1 → Part 0, Part 1          │
│  Consumer 2 → Part 2, Part 3          │
└────────────────────────────────────────┘

# Cada partição é consumida por APENAS 1 consumer do grupo
# Se adicionar Consumer 3, rebalanceamento:
#   Consumer 1 → Part 0
#   Consumer 2 → Part 1  
#   Consumer 3 → Part 2, Part 3
```

### Rebalancing

Quando consumer entra/sai do grupo, Kafka rebalanceia partições:

```python
from kafka import KafkaConsumer

consumer = KafkaConsumer(
    'orders',
    group_id='my-group',
    
    # Rebalance config
    session_timeout_ms=10000,     # Timeout para considerar consumer morto
    heartbeat_interval_ms=3000,   # Frequência de heartbeat
    max_poll_interval_ms=300000,  # Tempo máximo entre polls
    
    # Rebalance listener
    enable_auto_commit=False
)

# Consumer Rebalance Listener
from kafka import TopicPartition, ConsumerRebalanceListener

class MyRebalanceListener(ConsumerRebalanceListener):
    def on_partitions_revoked(self, revoked):
        print(f"Partitions revoked: {revoked}")
        # Commit offsets antes de perder partições
        consumer.commit()
    
    def on_partitions_assigned(self, assigned):
        print(f"Partitions assigned: {assigned}")
        # Inicializar estado para novas partições

consumer.subscribe(['orders'], listener=MyRebalanceListener())
```

### Múltiplos Consumer Groups

```python
# Diferentes grupos processam independentemente
group1 = KafkaConsumer('orders', group_id='analytics')    # Para analytics
group2 = KafkaConsumer('orders', group_id='notifications') # Para emails

# Cada grupo mantém próprio offset
# Mesma mensagem processada por ambos os grupos
```

---

## Kafka Streams

**Kafka Streams** = biblioteca para processar streams de dados.

```python
# Nota: Exemplo em Java (não há Python nativo)
# Para Python, use: faust, kafka-python + manual processing

# Java example
StreamsBuilder builder = new StreamsBuilder();

KStream<String, String> orders = builder.stream("orders");

// Filter
KStream<String, String> highValue = orders.filter(
    (key, value) -> parseAmount(value) > 1000
);

// Map
KStream<String, String> transformed = orders.mapValues(
    value -> value.toUpperCase()
);

// GroupBy + Aggregate
KTable<String, Long> orderCounts = orders
    .groupBy((key, value) -> extractCustomerId(value))
    .count();

// Join streams
KStream<String, String> enriched = orders.join(
    customers,
    (order, customer) -> order + customer,
    JoinWindows.of(Duration.ofMinutes(5))
);

// Output
enriched.to("enriched-orders");
```

### Stream Processing com Python (Faust)

```python
import faust

# Faust = Kafka Streams para Python
app = faust.App('myapp', broker='kafka://localhost:9092')

class Order(faust.Record):
    order_id: int
    customer_id: int
    amount: float

# Topic
orders_topic = app.topic('orders', value_type=Order)
high_value_topic = app.topic('high-value-orders', value_type=Order)

# Agent (stream processor)
@app.agent(orders_topic)
async def process_orders(orders):
    async for order in orders:
        if order.amount > 1000:
            await high_value_topic.send(value=order)

# Table (aggregation)
order_counts = app.Table('order-counts', default=int)

@app.agent(orders_topic)
async def count_orders(orders):
    async for order in orders.group_by(Order.customer_id):
        order_counts[order.customer_id] += 1

# Run
if __name__ == '__main__':
    app.main()
```

---

## Kafka Connect

**Kafka Connect** = framework para integrar Kafka com sistemas externos.

### Source Connectors (Dados → Kafka)

```json
{
  "name": "postgres-source",
  "config": {
    "connector.class": "io.debezium.connector.postgresql.PostgresConnector",
    "database.hostname": "localhost",
    "database.port": "5432",
    "database.user": "postgres",
    "database.password": "secret",
    "database.dbname": "mydb",
    "database.server.name": "dbserver1",
    "table.include.list": "public.orders,public.customers",
    "plugin.name": "pgoutput"
  }
}
```

### Sink Connectors (Kafka → Dados)

```json
{
  "name": "s3-sink",
  "config": {
    "connector.class": "io.confluent.connect.s3.S3SinkConnector",
    "tasks.max": "1",
    "topics": "orders",
    "s3.region": "us-east-1",
    "s3.bucket.name": "my-orders-bucket",
    "s3.part.size": "5242880",
    "flush.size": "1000",
    "storage.class": "io.confluent.connect.s3.storage.S3Storage",
    "format.class": "io.confluent.connect.s3.format.parquet.ParquetFormat",
    "partitioner.class": "io.confluent.connect.storage.partitioner.TimeBasedPartitioner",
    "path.format": "'year'=YYYY/'month'=MM/'day'=dd",
    "partition.duration.ms": "3600000",
    "timestamp.extractor": "Record"
  }
}
```

### Deploy Connector

```bash
# REST API
curl -X POST http://localhost:8083/connectors \
  -H "Content-Type: application/json" \
  -d @connector-config.json

# Listar connectors
curl http://localhost:8083/connectors

# Status
curl http://localhost:8083/connectors/postgres-source/status

# Delete
curl -X DELETE http://localhost:8083/connectors/postgres-source
```

---

## Best Practices

### 1. Número de Partições

```bash
# Calcular partições ideais
# Throughput desejado / Throughput por partição

# Exemplo:
# - Producer throughput: 100 MB/s
# - Consumer throughput: 50 MB/s por partição
# - Partições = 100 / 50 = 2 partições (mínimo)

# Criar topic com partições
kafka-topics --create \
  --bootstrap-server localhost:9092 \
  --topic orders \
  --partitions 10 \
  --replication-factor 3
```

**Regra de ouro:**
- Mais partições = mais paralelismo
- Mas: muitas partições = overhead (file handles, rebalancing)
- Recomendado: < 4000 partições por broker

### 2. Replication Factor

```bash
# Replication factor = número de cópias
# RF=3 (recomendado para produção)

# Topic com RF=3
kafka-topics --create \
  --bootstrap-server localhost:9092 \
  --topic critical-data \
  --partitions 6 \
  --replication-factor 3 \
  --config min.insync.replicas=2
```

**min.insync.replicas:**
- Quantos replicas devem ACK antes de sucesso
- RF=3, min.insync=2 → tolera 1 broker down

### 3. Retention

```bash
# Retention por tempo
kafka-configs --alter \
  --bootstrap-server localhost:9092 \
  --topic orders \
  --add-config retention.ms=604800000  # 7 dias

# Retention por tamanho
kafka-configs --alter \
  --bootstrap-server localhost:9092 \
  --topic logs \
  --add-config retention.bytes=1073741824  # 1GB

# Compact (mantém último valor por key)
kafka-topics --create \
  --bootstrap-server localhost:9092 \
  --topic user-profiles \
  --config cleanup.policy=compact
```

### 4. Monitoramento

```python
# Lag do consumer (quantas mensagens atrás)
from kafka import KafkaAdminClient, TopicPartition

admin = KafkaAdminClient(bootstrap_servers=['localhost:9092'])

# Consumer group offsets
group_offsets = admin.list_consumer_group_offsets('my-group')

# End offsets (última mensagem)
end_offsets = consumer.end_offsets([TopicPartition('orders', 0)])

# Lag = end_offset - group_offset
lag = end_offsets[tp] - group_offsets[tp].offset
print(f"Consumer lag: {lag} messages")
```

**Métricas importantes:**
- **Lag**: Atraso do consumer
- **Throughput**: Mensagens/segundo
- **Latency**: Tempo producer → consumer
- **Under-replicated partitions**: Partições sem réplicas suficientes

### 5. Security

```python
# SSL/TLS
producer = KafkaProducer(
    bootstrap_servers=['localhost:9093'],
    security_protocol='SSL',
    ssl_cafile='/path/to/ca-cert',
    ssl_certfile='/path/to/client-cert',
    ssl_keyfile='/path/to/client-key'
)

# SASL (authentication)
producer = KafkaProducer(
    bootstrap_servers=['localhost:9093'],
    security_protocol='SASL_SSL',
    sasl_mechanism='PLAIN',
    sasl_plain_username='user',
    sasl_plain_password='password'
)

# ACLs (authorization)
# kafka-acls --add \
#   --allow-principal User:alice \
#   --operation Read \
#   --topic orders
```

---

## 🎯 Checklist de Produção

- ✅ Replication factor ≥ 3
- ✅ min.insync.replicas ≥ 2
- ✅ acks='all' para dados críticos
- ✅ enable_idempotence=True
- ✅ Monitorar consumer lag
- ✅ Configurar retention apropriada
- ✅ Usar compression (gzip/snappy)
- ✅ Particionar por chave de negócio
- ✅ Implementar error handling e retry
- ✅ Logs e métricas (Prometheus + Grafana)
- ✅ Security (SSL + SASL + ACLs)
- ✅ Disaster recovery plan

---

## 📚 Referências

- [Kafka Documentation](https://kafka.apache.org/documentation/)
- [Confluent Developer](https://developer.confluent.io/)
- [Kafka: The Definitive Guide](https://www.confluent.io/resources/kafka-the-definitive-guide/)

---

**Próximo:** [02-kafka-advanced-patterns.md](./02-kafka-advanced-patterns.md)
