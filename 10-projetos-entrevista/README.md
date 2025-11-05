# Projetos de Entrevista - Data Engineering

Coleção completa de projetos que caem em entrevistas de emprego para **Senior Data Engineer**, organizados por nível de arquitetura.

## 📋 Índice

### 🔧 Low Level Architecture (Implementação & Algoritmos)
1. [**Log Processing System**](#1-log-processing-system) - Parse e análise de logs em tempo real
2. [**URL Shortener**](#2-url-shortener) - Sistema de encurtamento de URLs com analytics
3. [**Rate Limiter**](#3-rate-limiter) - Implementação de estratégias de rate limiting
4. [**Cache System**](#4-cache-system) - Sistema de cache distribuído (LRU/LFU)

### 🏗️ High Level Architecture (Design de Sistemas)
5. [**Ride-Sharing System**](#5-ride-sharing-system) - Sistema como Uber (matching em tempo real)
6. [**E-commerce Analytics Pipeline**](#6-e-commerce-analytics-pipeline) - Pipeline completo de analytics
7. [**Distributed Job Scheduler**](#7-distributed-job-scheduler) - Scheduler distribuído escalável
8. [**Real-time Fraud Detection**](#8-real-time-fraud-detection) - Detecção de fraude em tempo real

---

## 🔧 LOW LEVEL ARCHITECTURE

Projetos focados em **implementação**, **algoritmos**, **estruturas de dados** e **otimização de código**.

### 1. Log Processing System

**Pergunta comum:** "Como você processaria 10GB de logs por segundo?"

**Desafios:**
- Parse eficiente de logs (múltiplos formatos)
- Agregação em tempo real
- Detecção de anomalias
- Escrita eficiente para storage

**Estrutura:**
```
01-log-processing-system/
├── README.md                  # Requisitos e decisões de design
├── log_parser.py             # Parser otimizado (regex vs split)
├── aggregator.py             # Agregação em janelas de tempo
├── anomaly_detector.py       # Detecção de anomalias
├── writer.py                 # Batch writing otimizado
├── benchmarks/               # Benchmarks de performance
└── tests/                    # Testes unitários
```

**Conceitos Cobertos:**
- String parsing eficiente
- Sliding window aggregation
- Memory-efficient processing
- Batch vs streaming trade-offs
- Time complexity analysis (O(n) vs O(n²))

**Perguntas de Follow-up:**
- Como você otimizaria para 100GB/s?
- Como lidaria com logs out-of-order?
- Como garantiria exactly-once processing?

---

### 2. URL Shortener

**Pergunta comum:** "Design um sistema de encurtamento de URLs como bit.ly"

**Desafios:**
- Geração de IDs únicos e curtos
- Conversão Base62
- Collision handling
- Estatísticas de acesso
- Expiração de URLs

**Estrutura:**
```
02-url-shortener/
├── README.md
├── id_generator.py           # Snowflake ID / Base62 encoding
├── url_shortener.py          # Core logic
├── storage.py                # Storage abstraction (Redis/PostgreSQL)
├── analytics.py              # Click analytics
├── api.py                    # FastAPI endpoints
└── tests/
```

**Conceitos Cobertos:**
- ID generation strategies (UUID vs Snowflake vs Counter)
- Base conversion (Base10 → Base62)
- Hash collision resolution
- Database indexing
- Caching strategies

**Perguntas de Follow-up:**
- Como garantir IDs únicos em sistema distribuído?
- Como escalar para 1 bilhão de URLs?
- Como evitar ataques de brute-force?

---

### 3. Rate Limiter

**Pergunta comum:** "Implemente um rate limiter que suporte 1000 req/min por usuário"

**Desafios:**
- Múltiplas estratégias (Token Bucket, Sliding Window, Fixed Window)
- Implementação distribuída
- Performance (<1ms overhead)
- Precisão vs throughput trade-off

**Estrutura:**
```
03-rate-limiter/
├── README.md
├── strategies/
│   ├── token_bucket.py       # Token bucket algorithm
│   ├── sliding_window.py     # Sliding window log
│   ├── fixed_window.py       # Fixed window counter
│   └── leaky_bucket.py       # Leaky bucket
├── distributed_limiter.py    # Redis-based distribuído
├── decorator.py              # Python decorator para APIs
├── benchmarks/               # Comparação de performance
└── tests/
```

**Conceitos Cobertos:**
- Rate limiting algorithms
- Atomic operations (Redis INCR)
- Distributed coordination
- Time window handling
- Memory efficiency

**Perguntas de Follow-up:**
- Qual estratégia é melhor para bursts?
- Como sincronizar entre múltiplos servidores?
- Como lidar com clock skew?

---

### 4. Cache System

**Pergunta comum:** "Implemente um cache LRU thread-safe com TTL"

**Desafios:**
- Eviction policies (LRU, LFU, FIFO)
- Thread safety
- TTL management
- Memory limits
- Serialização eficiente

**Estrutura:**
```
04-cache-system/
├── README.md
├── policies/
│   ├── lru_cache.py          # LRU com OrderedDict
│   ├── lfu_cache.py          # LFU com heap
│   └── arc_cache.py          # Adaptive Replacement Cache
├── distributed_cache.py      # Redis-based
├── ttl_manager.py            # TTL com lazy deletion
├── serialization.py          # Pickle vs msgpack vs JSON
├── benchmarks/
└── tests/
```

**Conceitos Cobertos:**
- Cache eviction algorithms
- Data structures (OrderedDict, heap, doubly-linked list)
- Thread synchronization (locks, RLock)
- Memory management
- Serialization trade-offs

**Perguntas de Follow-up:**
- LRU vs LFU: quando usar cada um?
- Como implementar write-through vs write-back?
- Como escalar cache entre múltiplas máquinas?

---

## 🏗️ HIGH LEVEL ARCHITECTURE

Projetos focados em **design de sistemas**, **escalabilidade**, **distribuição** e **trade-offs**.

### 5. Ride-Sharing System (Uber-like)

**Pergunta comum:** "Design um sistema de ride-sharing como Uber"

**Desafios:**
- Geolocation matching em tempo real
- Routing otimizado
- Surge pricing
- Disponibilidade de motoristas
- Escalabilidade global

**Estrutura:**
```
05-ride-sharing-system/
├── README.md                 # Arquitetura completa
├── architecture/
│   ├── system_design.md      # Diagrama de componentes
│   ├── data_models.md        # Schema de dados
│   └── scaling.md            # Estratégia de escala
├── location_service/
│   ├── geohash.py            # Geohashing para proximidade
│   ├── quadtree.py           # QuadTree para busca espacial
│   └── matching_engine.py    # Algoritmo de matching
├── pricing_service/
│   ├── surge_calculator.py   # Cálculo de surge pricing
│   └── eta_estimator.py      # Estimativa de ETA
├── trip_service/
│   └── state_machine.py      # State machine de trip
└── infrastructure/
    ├── kafka_topics.md       # Event streaming
    ├── redis_schema.md       # Real-time data
    └── cassandra_schema.md   # Trip history
```

**Conceitos Cobertos:**
- Geospatial indexing (Geohash, S2, QuadTree)
- Real-time matching algorithms
- Event-driven architecture
- CAP theorem trade-offs
- Database sharding por região

**Capacidade:**
- 1M motoristas online
- 10M passageiros ativos
- 100K trips/min
- <1 segundo para matching

**Perguntas de Follow-up:**
- Como garantir consistency em matching?
- Como lidar com network partitions?
- Como calcular surge pricing em tempo real?

---

### 6. E-commerce Analytics Pipeline

**Pergunta comum:** "Design um pipeline de analytics para e-commerce (Amazon-scale)"

**Desafios:**
- Ingestão de múltiplas fontes (clickstream, transações, inventory)
- ETL de 10TB+ por dia
- Real-time + batch analytics
- Data quality e deduplicação
- GDPR compliance

**Estrutura:**
```
06-ecommerce-analytics-pipeline/
├── README.md
├── architecture/
│   ├── data_flow.md          # Diagrama de fluxo de dados
│   ├── lambda_architecture.md # Lambda vs Kappa
│   └── data_warehouse.md     # Star schema design
├── ingestion/
│   ├── kafka_producers/      # Event producers
│   ├── change_data_capture/  # CDC para databases
│   └── api_collectors/       # Coleta de APIs externas
├── processing/
│   ├── spark_jobs/           # Batch ETL (PySpark)
│   ├── flink_jobs/           # Stream processing
│   └── dbt_models/           # Data transformation (dbt)
├── serving/
│   ├── olap_cubes/           # OLAP cubes (Druid/Clickhouse)
│   ├── ml_features/          # Feature store
│   └── dashboards/           # Superset/Tableau
└── orchestration/
    └── airflow_dags/         # DAGs de orquestração
```

**Conceitos Cobertos:**
- Lambda vs Kappa architecture
- Data lake vs data warehouse
- Star schema vs snowflake schema
- Slowly changing dimensions (SCD Type 2)
- Data partitioning strategies

**Métricas:**
- 10TB data/day
- 100K events/sec (real-time)
- <5 min latency (streaming)
- <2 hours latency (batch)

**Perguntas de Follow-up:**
- Como garantir data quality?
- Como lidar com late-arriving data?
- Como implementar GDPR (right to be forgotten)?

---

### 7. Distributed Job Scheduler

**Pergunta comum:** "Design um sistema de job scheduling distribuído (Airflow-like)"

**Desafios:**
- DAG execution
- Distributed coordination
- Failure recovery
- Resource management
- Priority scheduling

**Estrutura:**
```
07-distributed-job-scheduler/
├── README.md
├── architecture/
│   ├── system_design.md
│   ├── consensus.md          # Raft/Paxos para leader election
│   └── fault_tolerance.md
├── scheduler/
│   ├── dag_parser.py         # Parse de DAGs
│   ├── topological_sort.py   # Ordenação topológica
│   ├── executor.py           # Task execution
│   └── retry_policy.py       # Exponential backoff
├── coordination/
│   ├── leader_election.py    # Leader election (ZooKeeper/etcd)
│   ├── distributed_lock.py   # Distributed locking
│   └── health_check.py       # Health monitoring
├── storage/
│   ├── metadata_store.py     # PostgreSQL para metadata
│   └── state_machine.py      # State machine de tasks
└── workers/
    ├── worker_pool.py        # Pool de workers
    └── resource_manager.py   # CPU/memory management
```

**Conceitos Cobertos:**
- Directed Acyclic Graphs (DAG)
- Distributed consensus (Raft/Paxos)
- Leader election
- At-least-once vs exactly-once execution
- Graceful degradation

**Capacidade:**
- 10K DAGs
- 1M tasks/day
- 1K concurrent workers
- <10 sec scheduling latency

**Perguntas de Follow-up:**
- Como garantir exactly-once execution?
- Como priorizar jobs críticos?
- Como escalar horizontalmente?

---

### 8. Real-time Fraud Detection

**Pergunta comum:** "Design um sistema de detecção de fraude em tempo real"

**Desafios:**
- Latência ultra-baixa (<100ms)
- Feature engineering em tempo real
- ML model serving
- False positive vs false negative trade-off
- Concept drift handling

**Estrutura:**
```
08-realtime-fraud-detection/
├── README.md
├── architecture/
│   ├── system_design.md
│   ├── ml_pipeline.md        # Pipeline de ML
│   └── feature_engineering.md
├── feature_engineering/
│   ├── real_time_features.py # Features de evento atual
│   ├── windowed_features.py  # Agregações de janela
│   ├── graph_features.py     # Features de grafo (conexões)
│   └── feature_store.py      # Redis feature store
├── models/
│   ├── rule_engine.py        # Regras hard-coded
│   ├── random_forest.py      # Random Forest
│   ├── xgboost_model.py      # XGBoost
│   └── neural_network.py     # Deep learning (PyTorch)
├── serving/
│   ├── model_server.py       # FastAPI + model serving
│   ├── ensemble.py           # Ensemble de modelos
│   └── explainability.py     # SHAP values
├── feedback_loop/
│   ├── label_collection.py   # Coleta de labels
│   └── model_retraining.py   # Retreino automático
└── monitoring/
    ├── metrics.py            # Precision, recall, F1
    └── drift_detection.py    # Concept drift detection
```

**Conceitos Cobertos:**
- Feature engineering para ML
- Model serving at scale
- Online learning vs batch learning
- A/B testing de modelos
- Explainable AI (SHAP, LIME)

**Performance:**
- <100ms latency (p99)
- 100K transactions/sec
- 95%+ precision
- 90%+ recall
- <0.1% false positive rate

**Perguntas de Follow-up:**
- Como lidar com imbalanced data?
- Como detectar concept drift?
- Como explicar decisões de fraude para usuários?

---

## 📊 Comparação de Projetos

| Projeto | Dificuldade | Tempo Típico | Conceitos-Chave | Empresas que Perguntam |
|---------|-------------|--------------|-----------------|------------------------|
| **Log Processing** | ⭐⭐ | 45 min | String parsing, aggregation | Google, Amazon, Netflix |
| **URL Shortener** | ⭐⭐ | 45 min | ID generation, encoding | Meta, Twitter, LinkedIn |
| **Rate Limiter** | ⭐⭐⭐ | 60 min | Algorithms, distributed systems | Stripe, Shopify, Cloudflare |
| **Cache System** | ⭐⭐⭐ | 60 min | Data structures, concurrency | Meta, Google, Amazon |
| **Ride-Sharing** | ⭐⭐⭐⭐ | 90 min | Geospatial, matching, events | Uber, Lyft, DoorDash |
| **E-commerce Analytics** | ⭐⭐⭐⭐ | 90 min | Data pipeline, ETL, warehousing | Amazon, Walmart, Shopify |
| **Job Scheduler** | ⭐⭐⭐⭐⭐ | 120 min | Distributed systems, consensus | Airbnb, Netflix, Databricks |
| **Fraud Detection** | ⭐⭐⭐⭐⭐ | 120 min | ML, real-time, feature engineering | PayPal, Stripe, Square |

---

## 🎯 Como Usar Este Repositório

### Para Candidatos

1. **Iniciantes**: Comece com projetos Low Level (1-4)
2. **Intermediários**: Tente projetos High Level mais simples (5-6)
3. **Avançados**: Desafie-se com projetos complexos (7-8)

### Estratégia de Estudo

**Semana 1-2**: Low Level Architecture
- Dia 1-3: Log Processing System
- Dia 4-6: URL Shortener
- Dia 7-9: Rate Limiter
- Dia 10-14: Cache System

**Semana 3-4**: High Level Architecture
- Dia 15-19: Ride-Sharing System
- Dia 20-24: E-commerce Analytics
- Dia 25-28: Distributed Job Scheduler

**Semana 5**: Projetos Avançados
- Dia 29-35: Real-time Fraud Detection

### Para Entrevistadores

Cada projeto inclui:
- ✅ Requisitos claros
- ✅ Rubricas de avaliação
- ✅ Perguntas de follow-up
- ✅ Red flags comuns
- ✅ Soluções de referência

---

## 🛠️ Setup

### Requisitos

```bash
# Python
Python 3.10+

# Dependências principais
pip install redis kafka-python fastapi sqlalchemy pyspark

# Para projetos específicos
# Ver requirements.txt em cada pasta
```

### Executar Projeto

```bash
# Exemplo: Log Processing System
cd 01-log-processing-system
pip install -r requirements.txt
python log_parser.py --input logs/sample.log --output results/
```

### Executar Testes

```bash
cd 01-log-processing-system
pytest tests/ -v
```

---

## 📚 Recursos Adicionais

### Livros Recomendados
- **Designing Data-Intensive Applications** - Martin Kleppmann
- **System Design Interview Vol 1 & 2** - Alex Xu
- **Database Internals** - Alex Petrov

### Cursos
- **Grokking the System Design Interview** (educative.io)
- **System Design Primer** (GitHub)
- **Data Engineering Zoomcamp** (DataTalks.Club)

### Sites para Praticar
- [LeetCode System Design](https://leetcode.com/discuss/interview-question/system-design)
- [Pramp](https://www.pramp.com/)
- [interviewing.io](https://interviewing.io/)

---

## 🎓 Conceitos por Projeto

### Estruturas de Dados
- **OrderedDict**: Cache LRU
- **Heap**: Cache LFU, Priority Queue
- **Trie**: Autocomplete, IP routing
- **QuadTree**: Geospatial indexing
- **Graph**: Fraud detection, social networks

### Algoritmos
- **Sliding Window**: Rate limiter, metrics
- **Topological Sort**: DAG scheduler
- **Dijkstra**: Routing, shortest path
- **Consistent Hashing**: Distributed cache
- **Bloom Filter**: Deduplication

### Design Patterns
- **Circuit Breaker**: Fault tolerance
- **Bulkhead**: Resource isolation
- **Saga**: Distributed transactions
- **CQRS**: Command-Query separation
- **Event Sourcing**: Audit log

### Sistemas Distribuídos
- **CAP Theorem**: Consistency vs Availability
- **Consensus**: Raft, Paxos
- **Replication**: Leader-follower, multi-master
- **Sharding**: Horizontal partitioning
- **Load Balancing**: Round-robin, least-connections

---

## 🏆 Níveis de Senioridade

### Junior (0-2 anos)
Foco: Projetos 1-2
- Implementação básica
- Testes unitários
- Documentação

### Mid-Level (2-4 anos)
Foco: Projetos 1-4
- Otimização de performance
- Trade-offs de design
- Testes de integração

### Senior (4-7 anos)
Foco: Projetos 1-6
- Arquitetura escalável
- Sistemas distribuídos
- Monitoramento e observabilidade

### Staff/Principal (7+ anos)
Foco: Projetos 1-8
- Design de sistemas complexos
- Cross-functional trade-offs
- Organizational impact

---

## 📝 Template de Resolução

Para cada projeto, use este template:

### 1. Requirements Clarification (5 min)
- Functional requirements
- Non-functional requirements
- Constraints e assumptions

### 2. Back-of-the-Envelope Estimation (5 min)
- QPS (Queries per Second)
- Storage requirements
- Bandwidth

### 3. System Interface Definition (5 min)
- APIs
- Data models

### 4. High-Level Design (10-15 min)
- Componentes principais
- Fluxo de dados
- Diagrama

### 5. Detailed Design (20-30 min)
- Componentes específicos
- Algoritmos
- Data structures

### 6. Identifying Bottlenecks (10 min)
- Single points of failure
- Performance bottlenecks
- Scaling strategies

### 7. Trade-offs Discussion (5-10 min)
- Consistency vs Availability
- Latency vs Throughput
- Cost vs Performance

---

## 🤝 Contribuindo

Contribuições são bem-vindas! Para adicionar novos projetos:

1. Fork o repositório
2. Crie uma branch: `git checkout -b projeto-novo`
3. Siga a estrutura de pastas existente
4. Inclua README, código e testes
5. Abra um Pull Request

---

## 📄 Licença

MIT License - Sinta-se livre para usar em estudos e entrevistas.

---

## ⭐ Agradecimentos

Projetos inspirados em entrevistas reais de:
- Google, Amazon, Meta, Netflix
- Uber, Lyft, DoorDash
- Stripe, PayPal, Square
- Airbnb, Booking.com
- Databricks, Snowflake

**Boa sorte nas suas entrevistas! 🚀**
