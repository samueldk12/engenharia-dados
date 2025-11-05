# 📡 Módulo 5: Streaming e Real-time

**Duração:** 4-5 semanas | **Nível:** Avançado

## 📋 Visão Geral

Domine processamento de dados em tempo real com Kafka, Flink e arquiteturas event-driven.

## 🎯 Objetivos

- ✅ Apache Kafka (Producer, Consumer, Streams)
- ✅ Stream processing patterns
- ✅ Event-driven architectures
- ✅ CDC (Change Data Capture)
- ✅ Real-time analytics

## 📚 Conteúdo

### 1. Apache Kafka

**Arquitetura:**
- Brokers (clusters)
- Topics (partitioned logs)
- Producers (write)
- Consumers (read)
- ZooKeeper/KRaft (coordination)

**Producer:**
```python
from kafka import KafkaProducer
import json

producer = KafkaProducer(
    bootstrap_servers=['localhost:9092'],
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

# Send message
producer.send('events', {'user_id': 123, 'action': 'click'})
producer.flush()
```

**Consumer:**
```python
from kafka import KafkaConsumer

consumer = KafkaConsumer(
    'events',
    bootstrap_servers=['localhost:9092'],
    group_id='analytics-group',
    auto_offset_reset='earliest',
    value_deserializer=lambda m: json.loads(m.decode('utf-8'))
)

for message in consumer:
    process_event(message.value)
```

### 2. Kafka Streams

```python
from kafka import KafkaProducer, KafkaConsumer
from collections import defaultdict

# Stateful stream processing
def process_stream():
    consumer = KafkaConsumer('input')
    producer = KafkaProducer()
    
    # State store (in-memory)
    user_counts = defaultdict(int)
    
    for msg in consumer:
        event = json.loads(msg.value)
        user_id = event['user_id']
        
        # Update state
        user_counts[user_id] += 1
        
        # Emit result
        producer.send('output', {
            'user_id': user_id,
            'count': user_counts[user_id]
        })
```

### 3. CDC (Change Data Capture)

**Debezium Example:**
```json
{
  "name": "postgres-connector",
  "config": {
    "connector.class": "io.debezium.connector.postgresql.PostgresConnector",
    "database.hostname": "localhost",
    "database.port": "5432",
    "database.user": "postgres",
    "database.password": "password",
    "database.dbname": "mydb",
    "database.server.name": "dbserver1",
    "table.include.list": "public.orders,public.customers"
  }
}
```

### 4. Stream Processing Patterns

**Windowing:**
- Tumbling: Non-overlapping, fixed size
- Sliding: Overlapping, fixed size
- Session: Dynamic, based on inactivity

**Aggregations:**
```python
# Tumbling window (1 minute)
SELECT
  TUMBLE_START(event_time, INTERVAL '1' MINUTE) as window_start,
  COUNT(*) as event_count
FROM events
GROUP BY TUMBLE(event_time, INTERVAL '1' MINUTE);
```

## ✅ Checklist

- [ ] Uso Kafka para messaging
- [ ] Implemento stream processing
- [ ] Entendo CDC patterns
- [ ] Crio real-time analytics

## 🚀 Próximos Passos

➡️ **[Módulo 6: Cloud e Infraestrutura](../06-cloud-infraestrutura/)**
