# E-commerce Analytics Pipeline

**Pergunta de Entrevista:** "Design um pipeline de analytics para e-commerce (escala Amazon) que processe 10TB de dados por dia"

## 📋 Requisitos

### Funcionais
1. **Data Ingestion**: Ingerir dados de múltiplas fontes (clickstream, transações, inventário)
2. **ETL**: Transformar e limpar dados
3. **Data Warehouse**: Armazenar dados para análise (OLAP)
4. **Real-time Metrics**: Dashboards em tempo real (sales, inventory)
5. **Batch Analytics**: Relatórios diários/semanais/mensais
6. **ML Features**: Feature store para modelos de recomendação/fraud detection
7. **GDPR Compliance**: Right to be forgotten, data anonymization

### Não-Funcionais
1. **Scale**: 10TB data/day, 100K events/sec
2. **Latency**:
   - Real-time: <1 minute end-to-end
   - Batch: <2 hours (for daily reports)
3. **Availability**: 99.9% uptime
4. **Data Quality**: <0.1% error rate
5. **Cost**: <$50K/month para 10TB/day

## 🎯 Back-of-the-Envelope Calculations

### Data Volume

```python
# Dados de entrada
Clickstream events: 1B events/day × 1 KB = 1 TB/day
Transactions: 10M transactions/day × 10 KB = 100 GB/day
Inventory updates: 100M updates/day × 500 bytes = 50 GB/day
User profiles: 100M users × 5 KB = 500 GB (one-time)
Product catalog: 10M products × 10 KB = 100 GB (one-time)

Total daily: 1TB + 100GB + 50GB = 1.15 TB/day raw
Compressed (3x): ~400 GB/day
Monthly: 400GB × 30 = 12 TB/month
Yearly: 12TB × 12 = 144 TB/year
```

### QPS (Queries Per Second)

```python
# Ingestion
Clickstream: 1B/day ÷ 86400 = ~11.5K events/sec
Peak (10x): 115K events/sec

Transactions: 10M/day ÷ 86400 = ~115 events/sec
Peak: 1.1K events/sec

# Queries (analytics)
Dashboard queries: 1K/min = ~17 QPS
Ad-hoc queries: 100/min = ~2 QPS
```

### Storage

```python
# Hot data (Last 7 days)
Clickstream: 1 TB/day × 7 = 7 TB
Transactions: 100 GB/day × 7 = 700 GB
Total hot: ~8 TB

# Warm data (Last 90 days)
Aggregated: 50 GB/day × 90 = 4.5 TB

# Cold data (Historical - 2 years)
Compressed: 400 GB/day × 730 = 292 TB

# Total storage: 8 TB + 4.5 TB + 292 TB = 304.5 TB
```

### Cost (AWS)

```python
# Ingestion
Kafka (MSK): 3 brokers × m5.large ($0.10/hr) × 730 hrs = $220/mo

# Processing
Spark on EMR: 20 r5.4xlarge ($1.00/hr) × 8 hrs/day × 30 = $4,800/mo

# Storage
S3:
  - Hot: 8 TB × $0.023/GB = $184/mo
  - Warm: 4.5 TB × $0.0125/GB = $56/mo  (Infrequent Access)
  - Cold: 292 TB × $0.004/GB = $1,168/mo  (Glacier)

# Data Warehouse (Redshift)
dc2.large: 3 nodes × $0.25/hr × 730 hrs = $550/mo

# TOTAL: ~$7K/mo  ✅ (<$50K target)
```

---

## 🏗️ Arquitetura

### Lambda Architecture (Batch + Stream)

```
┌──────────────────────────────────────────────────────────────────┐
│                         DATA SOURCES                              │
├────────────┬──────────────┬──────────────┬─────────────┬─────────┤
│ Clickstream│ Transactions │  Inventory   │ User Profiles│ Products│
│  (1 TB/d)  │  (100 GB/d)  │  (50 GB/d)   │  (500 GB)   │ (100 GB)│
└─────┬──────┴──────┬───────┴──────┬───────┴──────┬──────┴────┬────┘
      │             │              │              │           │
      ▼             ▼              ▼              ▼           ▼
┌─────────────────────────────────────────────────────────────────┐
│                        INGESTION LAYER                           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │  Kafka   │  │ Debezium │  │   API    │  │  Batch   │       │
│  │(Stream)  │  │  (CDC)   │  │Collectors│  │  Jobs    │       │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘       │
└───────┼────────────┼──────────────┼─────────────┼──────────────┘
        │            │              │             │
        └────────────┴──────────────┴─────────────┘
                            │
            ┌───────────────┼───────────────┐
            │               │               │
            ▼               ▼               ▼
    ┌──────────┐    ┌──────────┐    ┌──────────┐
    │  STREAM  │    │  BATCH   │    │  SPEED   │
    │  LAYER   │    │  LAYER   │    │  LAYER   │
    ├──────────┤    ├──────────┤    ├──────────┤
    │  Flink   │    │  Spark   │    │  Flink   │
    │ (Real-   │    │ (Daily   │    │ (Real-   │
    │  time)   │    │  ETL)    │    │  time    │
    │          │    │          │    │  Agg)    │
    │<1 min    │    │<2 hours  │    │<5 sec    │
    └────┬─────┘    └────┬─────┘    └────┬─────┘
         │               │               │
         ▼               ▼               ▼
    ┌──────────┐    ┌──────────┐    ┌──────────┐
    │   RAW    │    │ REFINED  │    │  REAL-   │
    │ (Bronze) │    │ (Silver) │    │   TIME   │
    │          │    │          │    │  (Redis) │
    │S3/Parquet│    │S3/Parquet│    │          │
    └────┬─────┘    └────┬─────┘    └────┬─────┘
         │               │               │
         └───────────────┴───────────────┘
                         │
                         ▼
                 ┌──────────────┐
                 │ CURATED      │
                 │ (Gold)       │
                 │              │
                 │ S3/Parquet   │
                 │ + Redshift   │
                 └──────┬───────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
        ▼               ▼               ▼
┌──────────┐    ┌──────────┐    ┌──────────┐
│DASHBOARDS│    │   ML     │    │   API    │
│(Superset)│    │ Feature  │    │(Serving) │
│          │    │  Store   │    │          │
└──────────┘    └──────────┘    └──────────┘
```

---

## 🔑 Componentes-Chave

### 1. Data Ingestion

#### Kafka (Streaming Data)

```python
# Producer: Clickstream events
from kafka import KafkaProducer
import json

producer = KafkaProducer(
    bootstrap_servers=['localhost:9092'],
    value_serializer=lambda v: json.dumps(v).encode('utf-8'),
    compression_type='snappy',  # 3x compression
    batch_size=16384,  # 16 KB batches
    linger_ms=10  # Wait 10ms to batch
)

# Click event
event = {
    'event_type': 'page_view',
    'user_id': 12345,
    'session_id': 'abc123',
    'timestamp': int(time.time() * 1000),
    'page_url': '/product/laptop-dell-xps',
    'referrer': 'https://google.com',
    'device': 'mobile',
    'location': {'country': 'US', 'state': 'CA'}
}

producer.send('clickstream', event)
```

**Topics**:
- `clickstream` - Page views, clicks
- `transactions` - Orders, payments
- `inventory` - Stock updates
- `users` - User profile changes

**Partitioning**: By `user_id` hash (para manter ordem por usuário)

#### Debezium (CDC - Change Data Capture)

```yaml
# Captura mudanças do PostgreSQL em tempo real
# Sem código custom!

connector.class: io.debezium.connector.postgresql.PostgresConnector
database.hostname: postgres
database.dbname: ecommerce
table.include.list: public.orders, public.users
transforms: unwrap
transforms.unwrap.type: io.debezium.transforms.ExtractNewRecordState
```

**Vantagens**:
- ✅ Zero-code data replication
- ✅ Exactly-once delivery
- ✅ Captura DELETEs (para GDPR)

---

### 2. Stream Processing (Flink)

#### Real-time Aggregations

```python
from pyflink.datastream import StreamExecutionEnvironment
from pyflink.table import StreamTableEnvironment

# Setup
env = StreamExecutionEnvironment.get_execution_environment()
t_env = StreamTableEnvironment.create(env)

# Fonte: Kafka
t_env.execute_sql("""
    CREATE TABLE clickstream (
        user_id BIGINT,
        event_type STRING,
        product_id STRING,
        timestamp BIGINT,
        event_time AS TO_TIMESTAMP(FROM_UNIXTIME(timestamp / 1000)),
        WATERMARK FOR event_time AS event_time - INTERVAL '10' SECOND
    ) WITH (
        'connector' = 'kafka',
        'topic' = 'clickstream',
        'properties.bootstrap.servers' = 'localhost:9092',
        'format' = 'json'
    )
""")

# Aggregação: Page views por minuto
t_env.execute_sql("""
    CREATE TABLE page_views_per_minute AS
    SELECT
        TUMBLE_START(event_time, INTERVAL '1' MINUTE) as window_start,
        event_type,
        COUNT(*) as view_count
    FROM clickstream
    WHERE event_type = 'page_view'
    GROUP BY
        TUMBLE(event_time, INTERVAL '1' MINUTE),
        event_type
""")

# Sink: Redis (para dashboards real-time)
t_env.execute_sql("""
    CREATE TABLE redis_sink (
        window_start TIMESTAMP,
        event_type STRING,
        view_count BIGINT
    ) WITH (
        'connector' = 'redis',
        'host' = 'localhost',
        'port' = '6379'
    )
""")

# Insert agregações no Redis
t_env.execute_sql("""
    INSERT INTO redis_sink
    SELECT * FROM page_views_per_minute
""")
```

#### Real-time Metrics

```python
# Top 10 produtos mais visualizados (última hora)
t_env.execute_sql("""
    SELECT
        product_id,
        COUNT(*) as view_count
    FROM clickstream
    WHERE
        event_type = 'product_view' AND
        event_time > CURRENT_TIMESTAMP - INTERVAL '1' HOUR
    GROUP BY product_id
    ORDER BY view_count DESC
    LIMIT 10
""")
```

---

### 3. Batch Processing (Spark)

#### Daily ETL Job

```python
from pyspark.sql import SparkSession
from pyspark.sql.functions import *

spark = SparkSession.builder \
    .appName("DailyETL") \
    .config("spark.sql.shuffle.partitions", "200") \
    .getOrCreate()

# 1. Read raw data (Bronze layer)
df_clicks = spark.read.parquet("s3://datalake/bronze/clickstream/2024/01/15/")
df_transactions = spark.read.parquet("s3://datalake/bronze/transactions/2024/01/15/")

# 2. Clean and transform (Silver layer)

# Deduplication
df_clicks_clean = df_clicks.dropDuplicates(['user_id', 'session_id', 'timestamp'])

# Validation
df_transactions_clean = df_transactions \
    .filter(col('amount') > 0) \
    .filter(col('status') == 'completed')

# Enrichment: Join com dimensões
df_enriched = df_transactions_clean \
    .join(df_users, 'user_id') \
    .join(df_products, 'product_id')

# 3. Aggregations (Gold layer)

# Daily sales summary
df_daily_sales = df_enriched \
    .groupBy('date', 'product_id', 'category') \
    .agg(
        sum('amount').alias('total_revenue'),
        count('*').alias('num_transactions'),
        countDistinct('user_id').alias('unique_customers'),
        avg('amount').alias('avg_order_value')
    )

# Write to S3 (Parquet, partitioned by date)
df_daily_sales.write \
    .mode('overwrite') \
    .partitionBy('date') \
    .parquet('s3://datalake/gold/daily_sales/')

# Write to Redshift (for BI)
df_daily_sales.write \
    .format("jdbc") \
    .option("url", "jdbc:redshift://...") \
    .option("dbtable", "analytics.daily_sales") \
    .option("user", "admin") \
    .option("password", "...") \
    .mode("append") \
    .save()
```

#### Incremental Processing

```python
# Processar apenas novos dados (incremental)

# 1. Get last processed timestamp
last_processed = spark.read \
    .table("metadata.last_processed") \
    .select(max('timestamp')) \
    .collect()[0][0]

# 2. Read only new data
df_new = spark.read.parquet("s3://datalake/bronze/clickstream/") \
    .filter(col('timestamp') > last_processed)

# 3. Process
# ...

# 4. Update metadata
spark.sql(f"""
    INSERT INTO metadata.last_processed
    VALUES ('{datetime.now()}', {df_new.agg(max('timestamp')).collect()[0][0]})
""")
```

---

### 4. Data Warehouse (Star Schema)

```sql
-- Fact table: Sales
CREATE TABLE fact_sales (
    sale_id BIGINT PRIMARY KEY,
    date_key INT REFERENCES dim_date(date_key),
    user_key INT REFERENCES dim_user(user_key),
    product_key INT REFERENCES dim_product(product_key),
    store_key INT REFERENCES dim_store(store_key),
    quantity INT,
    unit_price DECIMAL(10,2),
    total_amount DECIMAL(10,2),
    discount_amount DECIMAL(10,2),
    tax_amount DECIMAL(10,2),
    shipping_amount DECIMAL(10,2)
)
DISTSTYLE KEY
DISTKEY (date_key)
SORTKEY (date_key);

-- Dimension: Date
CREATE TABLE dim_date (
    date_key INT PRIMARY KEY,
    date DATE,
    day_of_week VARCHAR(10),
    day_of_month INT,
    day_of_year INT,
    week_of_year INT,
    month INT,
    quarter INT,
    year INT,
    is_weekend BOOLEAN,
    is_holiday BOOLEAN
)
DISTSTYLE ALL;

-- Dimension: User (SCD Type 2 - Track changes)
CREATE TABLE dim_user (
    user_key INT PRIMARY KEY,  -- Surrogate key
    user_id BIGINT,  -- Business key
    email VARCHAR(255),
    name VARCHAR(100),
    tier VARCHAR(20),  -- 'free', 'premium', 'vip'
    country VARCHAR(2),
    state VARCHAR(50),
    effective_date DATE,
    expiration_date DATE,
    is_current BOOLEAN
)
DISTSTYLE ALL;

-- Dimension: Product
CREATE TABLE dim_product (
    product_key INT PRIMARY KEY,
    product_id VARCHAR(50),
    product_name VARCHAR(255),
    category VARCHAR(100),
    subcategory VARCHAR(100),
    brand VARCHAR(100),
    price DECIMAL(10,2)
)
DISTSTYLE ALL;
```

**Queries Analíticas**:
```sql
-- Top 10 produtos por receita (último mês)
SELECT
    p.product_name,
    p.category,
    SUM(s.total_amount) as revenue,
    COUNT(*) as num_sales
FROM fact_sales s
JOIN dim_product p ON s.product_key = p.product_key
JOIN dim_date d ON s.date_key = d.date_key
WHERE d.date >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY p.product_name, p.category
ORDER BY revenue DESC
LIMIT 10;

-- Cohort analysis: Retenção de usuários
SELECT
    EXTRACT(MONTH FROM first_purchase.date) as cohort_month,
    DATEDIFF(month, first_purchase.date, s.date) as months_since_first,
    COUNT(DISTINCT s.user_key) as active_users
FROM fact_sales s
JOIN (
    SELECT user_key, MIN(date) as date
    FROM fact_sales
    GROUP BY user_key
) first_purchase ON s.user_key = first_purchase.user_key
GROUP BY cohort_month, months_since_first
ORDER BY cohort_month, months_since_first;
```

---

### 5. Data Quality

```python
# Great Expectations - Data validation

import great_expectations as ge

# Load data
df = ge.read_csv('s3://datalake/bronze/transactions.csv')

# Expectations (rules)
df.expect_column_values_to_not_be_null('user_id')
df.expect_column_values_to_be_between('amount', min_value=0, max_value=1000000)
df.expect_column_values_to_be_in_set('status', ['pending', 'completed', 'failed', 'refunded'])
df.expect_column_values_to_match_regex('email', r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')

# Validate
validation_result = df.validate()

if not validation_result['success']:
    # Send alert
    send_slack_alert(f"Data quality issues: {validation_result}")

    # Log failures
    for result in validation_result['results']:
        if not result['success']:
            print(f"FAILED: {result['expectation_config']}")
            print(f"Details: {result['result']}")
```

---

### 6. GDPR Compliance

#### Right to be Forgotten

```python
# Quando usuário solicita deleção

def delete_user_data(user_id: int):
    """
    1. Delete from operational databases
    2. Anonymize historical data (cannot delete for auditing)
    3. Update data lake with tombstone markers
    """

    # 1. Delete from PostgreSQL
    db.execute("DELETE FROM users WHERE user_id = %s", (user_id,))
    db.execute("UPDATE orders SET user_id = NULL WHERE user_id = %s", (user_id,))

    # 2. Mark for deletion in data lake
    spark.sql(f"""
        INSERT INTO deleted_users
        VALUES ({user_id}, CURRENT_TIMESTAMP)
    """)

    # 3. Re-run ETL to filter deleted users
    # Spark filter: .filter(~col('user_id').isin(deleted_users))

    # 4. Anonymize Redshift
    redshift.execute(f"""
        UPDATE dim_user
        SET
            email = 'deleted@deleted.com',
            name = 'DELETED',
            is_deleted = TRUE
        WHERE user_id = {user_id}
    """)
```

---

## 📊 Monitoring & Alerting

```python
# Key Metrics

# Data Quality
- Data freshness: <5 min for real-time, <2 hours for batch
- Data completeness: >99.9%
- Data accuracy: >99.9%
- Schema validation failures: <0.1%

# Pipeline Health
- Kafka lag: <1 minute
- Flink checkpoint duration: <10 sec
- Spark job success rate: >99%
- ETL job duration: <2 hours

# Business Metrics
- Orders per minute
- Revenue per minute
- Top products (real-time)
- Inventory alerts (low stock)

# Alerting (PagerDuty)
- Pipeline failure: P1 (immediate)
- Data quality issues: P2 (within 1 hour)
- High Kafka lag: P3 (within 4 hours)
```

---

## 🎓 Conceitos-Chave

1. **Lambda Architecture**: Batch + Stream processing
2. **Data Lake**: Bronze (raw) → Silver (cleaned) → Gold (curated)
3. **Change Data Capture**: Debezium para replicação em tempo real
4. **Star Schema**: Fact + Dimensions para analytics
5. **SCD Type 2**: Track historical changes
6. **Incremental Processing**: Process only new data
7. **Data Quality**: Great Expectations para validation
8. **GDPR**: Right to be forgotten, anonymization

---

## 🏆 Tempo de Implementação

- **Requirements**: 5 min
- **Back-of-envelope**: 5 min
- **High-level Design**: 20 min
- **Detailed Design**: 45 min
- **Trade-offs**: 15 min

**Total**: 90 minutos
**Dificuldade**: ⭐⭐⭐⭐ (Hard)
**Empresas**: Amazon, Walmart, Shopify, MercadoLibre, Alibaba
