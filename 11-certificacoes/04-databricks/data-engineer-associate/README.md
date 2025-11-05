# Databricks Certified Data Engineer Associate

**A certificação com maior ROI para Data Engineers em 2024**

## 📋 Informações Gerais

- **Código**: Databricks Certified Data Engineer Associate
- **Nível**: Associate
- **Duração**: 90 minutos
- **Número de questões**: 45 questões
- **Formato**: Múltipla escolha
- **Nota mínima**: 70% (32/45 questões corretas)
- **Custo**: $200 USD
- **Validade**: 2 anos
- **Idiomas**: Inglês
- **Modalidade**: Online (proctored)
- **Tentativas**: Permitidas (com intervalo mínimo)

## 🎯 Para Quem é Esta Certificação

### ✅ Ideal para:
- Data Engineers com 6+ meses de experiência em Spark/Databricks
- Profissionais migrando para Lakehouse architecture
- Engineers querendo validar conhecimento em Delta Lake
- Candidatos a posições Senior Data Engineer

### ❌ Não recomendado para:
- Iniciantes em programação (aprenda Python/Scala primeiro)
- Sem experiência com Spark (faça curso básico antes)
- Foco apenas em ML (faça ML Associate/Professional)

## 💰 ROI (Return on Investment)

```
Investimento:
- Certificação: $200
- Tempo de estudo: 60-80 horas
- Cursos: $0-50 (Databricks Academy é grátis!)
Total: ~$250

Retorno:
- Aumento salarial: +$15K-30K/ano
- Payback: 1 mês de salário
- Demanda: 🔥🔥🔥🔥🔥 (Altíssima)

Empresas usando Databricks:
- Uber, Lyft, DoorDash, Spotify
- Shell, Nationwide, Regeneron
- Adobe, Bloomberg, Comcast
```

## 📊 Tópicos do Exame

| Tópico | Peso | Questões (~) |
|--------|------|--------------|
| **1. Databricks Lakehouse Platform** | 24% | 11 |
| **2. ELT with Spark SQL and Python** | 29% | 13 |
| **3. Incremental Data Processing** | 22% | 10 |
| **4. Production Pipelines** | 16% | 7 |
| **5. Data Governance** | 9% | 4 |

---

## 📚 Tópico 1: Databricks Lakehouse Platform (24%)

### Arquitetura Lakehouse

```
Traditional Architecture:
┌──────────────┐
│  Data Lake   │ (S3/HDFS) - Cheap, unstructured
│  (Hadoop)    │ ❌ Slow queries
└──────────────┘ ❌ No ACID
      ↓ ETL
┌──────────────┐
│Data Warehouse│ (Redshift/Snowflake) - Fast queries
│  (Expensive) │ ✅ ACID transactions
└──────────────┘ ❌ Expensive, data duplication

Lakehouse Architecture:
┌──────────────────────────────────┐
│      Delta Lake on Cloud         │
│  ✅ Cheap storage (S3/ADLS/GCS)  │
│  ✅ Fast queries (Spark)         │
│  ✅ ACID transactions             │
│  ✅ Schema enforcement            │
│  ✅ Time travel                   │
│  ✅ Unified (batch + streaming)  │
└──────────────────────────────────┘
```

### Databricks Workspace Components

```python
# Workspace hierarquia:
Workspace
  ├── Repos (Git integration)
  │     ├── Notebook 1
  │     └── Notebook 2
  ├── Data
  │     ├── Databases
  │     └── Tables
  ├── Compute
  │     ├── All-Purpose Clusters
  │     └── Job Clusters
  ├── Workflows
  │     └── Jobs / DLT Pipelines
  └── DBFS (Databricks File System)
        ├── /mnt (mount points)
        └── /tmp
```

### Cluster Types

**All-Purpose Cluster**:
```python
# Use cases:
✅ Interactive development
✅ Notebooks exploration
✅ Prototyping
❌ Production jobs (caro!)

# Características:
- Created manually
- Stays up até terminar manualmente
- Shared entre usuários
- Auto-termination: 120 min idle (default)

# Pricing: ~3x mais caro que Job Cluster
```

**Job Cluster**:
```python
# Use cases:
✅ Production jobs
✅ Scheduled workflows
✅ CI/CD pipelines

# Características:
- Created automatically pelo job
- Termina quando job completa
- Dedicado para o job
- Não pode ser usado interativamente

# Pricing: ~3x mais barato
```

**Cluster Modes**:
```python
# Standard Mode:
- Shared entre usuários
- ❌ Não tem isolação completa
- Use para: Development, testing

# High Concurrency Mode:
- Process isolation
- ✅ Seguro para multi-tenancy
- Fair scheduling
- Use para: Production com múltiplos usuários

# Single Node:
- Sem workers (only driver)
- Use para: Lightweight tasks, testing
```

### DBFS (Databricks File System)

```python
# Abstração sobre cloud storage (S3/ADLS/GCS)

# Paths:
dbfs:/                    # DBFS root
dbfs:/mnt/                # Mount points
dbfs:/FileStore/          # UI uploaded files
dbfs:/tmp/                # Temporary storage

# Python access:
df = spark.read.parquet("dbfs:/data/events.parquet")
df = spark.read.parquet("/dbfs/data/events.parquet")  # Filesystem API

# Mount external storage:
dbutils.fs.mount(
  source = "s3a://my-bucket",
  mount_point = "/mnt/my-data",
  extra_configs = {"fs.s3a.access.key": "...", "fs.s3a.secret.key": "..."}
)

# List:
dbutils.fs.ls("/mnt/my-data")

# Read:
df = spark.read.parquet("/mnt/my-data/events/")
```

**Questões Típicas**:
```
Q: Qual cluster type usar para scheduled ETL job que roda daily?
A: Job Cluster (mais barato, auto-termination)

Q: Diferença entre Data Lake e Lakehouse?
A: Lakehouse = Data Lake + ACID transactions + schema enforcement

Q: Como acessar S3 bucket de dentro do Databricks?
A: Mount com dbutils.fs.mount() ou configurar access keys no cluster

Q: Cluster mode para múltiplos analistas rodando notebooks?
A: High Concurrency Mode (process isolation)
```

---

## 📚 Tópico 2: ELT with Spark SQL and Python (29%)

### Spark DataFrame API

```python
from pyspark.sql import functions as F

# Read data
df = spark.read.format("parquet") \
    .option("header", "true") \
    .load("/mnt/data/events/")

# Transformations (lazy)
df_clean = df \
    .filter(F.col("event_type") == "purchase") \
    .filter(F.col("amount") > 0) \
    .select("user_id", "amount", "timestamp") \
    .withColumn("date", F.to_date("timestamp"))

# Aggregations
df_summary = df_clean \
    .groupBy("user_id", "date") \
    .agg(
        F.sum("amount").alias("total_amount"),
        F.count("*").alias("num_purchases"),
        F.avg("amount").alias("avg_amount")
    )

# Write (action)
df_summary.write \
    .mode("overwrite") \
    .partitionBy("date") \
    .format("delta") \
    .save("/mnt/data/user_purchases/")
```

### Spark SQL

```sql
-- Create database
CREATE DATABASE IF NOT EXISTS ecommerce;

-- Use database
USE ecommerce;

-- Create table (managed)
CREATE TABLE IF NOT EXISTS events (
  event_id STRING,
  user_id STRING,
  event_type STRING,
  timestamp TIMESTAMP,
  amount DECIMAL(10,2)
)
USING DELTA
PARTITIONED BY (date DATE);

-- Create external table
CREATE EXTERNAL TABLE events_external
USING DELTA
LOCATION '/mnt/data/events';

-- Insert data
INSERT INTO events
SELECT * FROM events_external
WHERE date >= '2024-01-01';

-- Query
SELECT
  user_id,
  COUNT(*) as event_count,
  SUM(amount) as total_spent
FROM events
WHERE event_type = 'purchase'
GROUP BY user_id
HAVING total_spent > 1000
ORDER BY total_spent DESC
LIMIT 10;
```

### Managed vs External Tables

```python
# Managed Table:
# - Databricks manages metadata + data
# - DROP TABLE deletes data + metadata
spark.sql("""
    CREATE TABLE managed_table (id INT, name STRING)
    USING DELTA
""")

# External Table:
# - Databricks manages apenas metadata
# - DROP TABLE deleta apenas metadata (data preservada)
spark.sql("""
    CREATE EXTERNAL TABLE external_table (id INT, name STRING)
    USING DELTA
    LOCATION '/mnt/data/table/'
""")

# Quando usar:
Managed: ✅ Data owned by Databricks, temporary data
External: ✅ Shared data, production data, data owned by outro sistema
```

### Views

```sql
-- Temporary View (session-scoped)
CREATE OR REPLACE TEMP VIEW recent_purchases AS
SELECT * FROM events
WHERE date >= CURRENT_DATE - INTERVAL 7 DAYS;

-- Global Temp View (application-scoped)
CREATE OR REPLACE GLOBAL TEMP VIEW all_purchases AS
SELECT * FROM events;

-- Access:
SELECT * FROM recent_purchases;
SELECT * FROM global_temp.all_purchases;

-- Persistent View (stored in metastore)
CREATE OR REPLACE VIEW vip_users AS
SELECT user_id, SUM(amount) as lifetime_value
FROM events
WHERE event_type = 'purchase'
GROUP BY user_id
HAVING lifetime_value > 10000;
```

### Transformations vs Actions

```python
# Transformations (lazy, retornam DataFrame):
df.select()
df.filter()
df.groupBy()
df.join()
df.withColumn()
df.drop()
df.distinct()

# Actions (eager, triggers computation):
df.show()
df.count()
df.collect()
df.write.save()
df.take(n)
df.first()
```

### Handling Null Values

```python
# Drop rows com nulls
df.dropna()  # Drop se ANY column is null
df.dropna(subset=["user_id", "amount"])  # Drop se specific columns null

# Fill nulls
df.fillna(0)  # Fill all numeric columns com 0
df.fillna({"age": 0, "name": "Unknown"})  # Fill specific columns

# Filter nulls
df.filter(F.col("user_id").isNotNull())
df.filter(~F.col("amount").isNull())
```

### Deduplication

```python
# Remove exact duplicates (all columns)
df.distinct()

# Remove duplicates based on subset of columns
df.dropDuplicates(["user_id", "event_id"])

# Keep last duplicate (by timestamp)
from pyspark.sql.window import Window

window = Window.partitionBy("user_id", "event_id").orderBy(F.desc("timestamp"))

df.withColumn("row_num", F.row_number().over(window)) \
  .filter(F.col("row_num") == 1) \
  .drop("row_num")
```

**Questões Típicas**:
```
Q: Qual operação é lazy?
A: select(), filter(), groupBy() (transformations)

Q: Qual operação triggers execution?
A: count(), show(), write() (actions)

Q: Como remover duplicates baseado em user_id?
A: df.dropDuplicates(["user_id"])

Q: Managed vs External table. Quando usar cada um?
A: Managed para temporary, External para production shared data

Q: Como criar view que persiste entre sessions?
A: CREATE VIEW (não TEMP VIEW)
```

---

## 📚 Tópico 3: Incremental Data Processing (22%)

### Delta Lake Basics

```python
# Delta Lake = Parquet + transaction log
# Benefits:
✅ ACID transactions
✅ Schema enforcement
✅ Schema evolution
✅ Time travel
✅ UPSERT (MERGE)
✅ Audit history

# Write Delta
df.write.format("delta").save("/mnt/data/events")

# Read Delta
df = spark.read.format("delta").load("/mnt/data/events")

# SQL
spark.sql("CREATE TABLE events USING DELTA LOCATION '/mnt/data/events'")
```

### MERGE (UPSERT)

```sql
-- Upsert: Update if exists, Insert if not

MERGE INTO target t
USING source s
ON t.user_id = s.user_id
WHEN MATCHED THEN
  UPDATE SET
    t.name = s.name,
    t.email = s.email,
    t.updated_at = current_timestamp()
WHEN NOT MATCHED THEN
  INSERT (user_id, name, email, created_at)
  VALUES (s.user_id, s.name, s.email, current_timestamp());

-- Python API:
from delta.tables import DeltaTable

delta_table = DeltaTable.forPath(spark, "/mnt/data/users")

delta_table.alias("target").merge(
    source_df.alias("source"),
    "target.user_id = source.user_id"
).whenMatchedUpdate(set = {
    "name": "source.name",
    "email": "source.email",
    "updated_at": "current_timestamp()"
}).whenNotMatchedInsert(values = {
    "user_id": "source.user_id",
    "name": "source.name",
    "email": "source.email",
    "created_at": "current_timestamp()"
}).execute()
```

### Time Travel

```python
# Read specific version
df = spark.read.format("delta").option("versionAsOf", 5).load("/path/")

# Read at specific timestamp
df = spark.read.format("delta") \
    .option("timestampAsOf", "2024-01-15T10:00:00Z") \
    .load("/path/")

# SQL
SELECT * FROM events VERSION AS OF 5;
SELECT * FROM events TIMESTAMP AS OF '2024-01-15 10:00:00';

# Describe history
DESCRIBE HISTORY events;

# Restore to previous version
RESTORE TABLE events TO VERSION AS OF 5;
```

### OPTIMIZE & Z-ORDER

```sql
-- OPTIMIZE: Compact small files
OPTIMIZE events;

-- Z-ORDER: Co-locate related data (multi-dimensional clustering)
OPTIMIZE events ZORDER BY (user_id, date);

-- Benefícios:
- Menos small files = faster reads
- Z-ORDER = faster WHERE queries

-- Exemplo:
SELECT * FROM events
WHERE user_id = '12345' AND date = '2024-01-15';
-- Com Z-ORDER: Skip 90% dos files!
```

### VACUUM

```python
# Delete old versions (free up storage)

VACUUM events RETAIN 168 HOURS;  # 7 days (default)

# WARNING: Cannot time travel before VACUUM
# Best practice: RETAIN 168 HOURS (1 week)

# Disable check (risky!)
spark.conf.set("spark.databricks.delta.retentionDurationCheck.enabled", false)
VACUUM events RETAIN 0 HOURS;
```

### Auto Loader (Structured Streaming)

```python
# Efficiently process novo files em S3/ADLS

df = spark.readStream.format("cloudFiles") \
    .option("cloudFiles.format", "json") \
    .option("cloudFiles.schemaLocation", "/mnt/schema/") \
    .load("/mnt/raw/events/")

# Transformations
df_clean = df.filter(F.col("amount") > 0)

# Write to Delta (streaming)
query = df_clean.writeStream \
    .format("delta") \
    .outputMode("append") \
    .option("checkpointLocation", "/mnt/checkpoints/events") \
    .trigger(availableNow=True) \  # or processingTime="1 minute"
    .start("/mnt/data/events")

query.awaitTermination()

# Auto Loader benefits:
✅ Automatic schema inference
✅ Exactly-once processing
✅ Scalable (millions of files)
✅ Low cost (vs listing S3 files)
```

### Streaming vs Batch

```python
# Batch (read once)
df = spark.read.format("delta").load("/path/")

# Streaming (continuous processing)
df = spark.readStream.format("delta").load("/path/")

# Trigger modes:
.trigger(processingTime="1 minute")  # Micro-batch every 1 min
.trigger(once=True)                  # Process available data once, then stop
.trigger(availableNow=True)          # Same as once (newer API)
.trigger(continuous="1 second")      # Low-latency streaming (experimental)

# Output modes:
.outputMode("append")     # Only new rows (default)
.outputMode("complete")   # Full result (use com aggregations)
.outputMode("update")     # Only updated rows
```

**Questões Típicas**:
```
Q: Como fazer UPSERT em Delta Lake?
A: MERGE INTO ... USING ... ON ... WHEN MATCHED ... WHEN NOT MATCHED

Q: Como ler versão anterior de uma Delta table?
A: VERSION AS OF 5 ou TIMESTAMP AS OF '...'

Q: Qual comando compacta small files?
A: OPTIMIZE

Q: Qual comando melhora performance de queries com WHERE?
A: OPTIMIZE ... ZORDER BY (columns)

Q: Como processar novos files automaticamente de S3?
A: Auto Loader com cloudFiles format

Q: Diferença entre trigger once=True e processingTime="1 minute"?
A: once=True processa e para, processingTime roda continuamente
```

---

## 📚 Tópico 4: Production Pipelines (16%)

### Delta Live Tables (DLT)

```python
# Declarative ETL framework
# Abstrai complexidade de streaming, dependencies, error handling

import dlt
from pyspark.sql import functions as F

# Bronze: Raw ingestion
@dlt.table(
  comment="Raw events from JSON files",
  table_properties={"quality": "bronze"}
)
def events_raw():
  return spark.readStream.format("cloudFiles") \
    .option("cloudFiles.format", "json") \
    .load("/mnt/raw/events/")

# Silver: Cleaned data
@dlt.table(
  comment="Cleaned events with constraints",
  table_properties={"quality": "silver"}
)
@dlt.expect_or_drop("valid_amount", "amount > 0")
@dlt.expect_or_fail("valid_user", "user_id IS NOT NULL")
def events_clean():
  return dlt.read_stream("events_raw") \
    .select("user_id", "event_type", "amount", "timestamp")

# Gold: Aggregated analytics
@dlt.table(
  comment="Daily user metrics",
  table_properties={"quality": "gold"}
)
def user_daily_metrics():
  return dlt.read("events_clean") \
    .groupBy("user_id", F.to_date("timestamp").alias("date")) \
    .agg(
      F.sum("amount").alias("total_amount"),
      F.count("*").alias("event_count")
    )
```

**DLT Benefits**:
```python
✅ Declarative (foco no WHAT, não HOW)
✅ Auto dependency resolution
✅ Data quality expectations
✅ Auto error handling & retry
✅ Observability dashboard
✅ Simplified operations
❌ Vendor lock-in (Databricks only)
```

### Expectations (Data Quality)

```python
# expect: Log warnings
@dlt.expect("valid_email", "email LIKE '%@%.%'")

# expect_or_drop: Drop invalid rows
@dlt.expect_or_drop("positive_amount", "amount > 0")

# expect_or_fail: Fail pipeline if constraint violated
@dlt.expect_or_fail("non_null_user", "user_id IS NOT NULL")

# Multiple expectations:
@dlt.expect_all({
  "valid_amount": "amount > 0",
  "valid_user": "user_id IS NOT NULL",
  "recent": "timestamp > '2020-01-01'"
})
```

### Jobs & Orchestration

```python
# Jobs = scheduled workflows

# Job types:
1. Notebook job: Run notebook
2. JAR job: Run Scala/Java JAR
3. Python job: Run .py file
4. DLT pipeline: Run Delta Live Tables

# Schedule:
- Cron: "0 0 * * *" (daily at midnight)
- Manual
- API trigger

# Compute:
- New job cluster (recommended for production)
- Existing all-purpose cluster (dev only)

# Dependencies:
- Libraries (PyPI, Maven)
- Wheels
- Eggs
- JARs

# Notifications:
- Email on success/failure
- Webhook
- PagerDuty integration
```

### Monitoring & Logging

```python
# Spark UI:
- Stages: See DAG execution
- Storage: Cached RDDs
- Environment: Spark configs
- Executors: Resource usage

# Databricks Job Runs:
- Cluster logs (driver, executor)
- Notebook output
- Spark UI link
- Metrics (duration, rows processed)

# DLT Observability:
- Data quality metrics
- Lineage graph
- Event log (all operations)
- Pipeline health
```

**Questões Típicas**:
```
Q: Qual framework usar para declarative ETL?
A: Delta Live Tables (DLT)

Q: Como droppar rows que não atendem constraint?
A: @dlt.expect_or_drop("constraint_name", "condition")

Q: Qual cluster type usar para scheduled production job?
A: New job cluster (cost-effective)

Q: Como agendar job para rodar diariamente às 2am?
A: Cron schedule: "0 2 * * *"

Q: Onde ver logs de job failure?
A: Job Runs → Failed run → Cluster Logs
```

---

## 📚 Tópico 5: Data Governance (9%)

### Unity Catalog

```python
# Three-level namespace:
catalog.schema.table

# Example:
prod.ecommerce.events
dev.finance.transactions
analytics.marketing.campaigns

# Benefits:
✅ Centralized governance
✅ Fine-grained access control
✅ Audit logging
✅ Data discovery
✅ Cross-workspace sharing
```

### Access Control

```sql
-- Grant table access
GRANT SELECT ON TABLE prod.ecommerce.events TO `analyst@company.com`;

-- Grant schema access
GRANT USAGE ON SCHEMA prod.ecommerce TO `data-team`;
GRANT CREATE TABLE ON SCHEMA prod.ecommerce TO `engineers`;

-- Grant catalog access
GRANT USAGE ON CATALOG prod TO `all-users`;

-- Revoke
REVOKE SELECT ON TABLE prod.ecommerce.events FROM `analyst@company.com`;

-- View grants
SHOW GRANTS ON TABLE prod.ecommerce.events;
```

### Table ACLs (Legacy, before Unity Catalog)

```sql
-- Enable Table ACLs no cluster config:
spark.databricks.acl.dfAclsEnabled true

-- Grant
GRANT SELECT ON TABLE events TO `user@company.com`;
GRANT MODIFY ON TABLE events TO `data-engineers`;

-- Deny
DENY SELECT ON TABLE sensitive_data TO `contractors`;
```

### PII & Data Masking

```python
# Column-level encryption
CREATE TABLE users (
  user_id STRING,
  name STRING,
  email STRING MASK 'email',  # Mask PII
  ssn STRING MASK 'custom-ssn'
);

# Row-level filtering (Unity Catalog)
CREATE FUNCTION filter_region(region STRING)
RETURN IF(current_user() IN ('admin@company.com'), TRUE, region = 'US');

CREATE TABLE sales
WITH ROW FILTER filter_region(region);

# Dynamic views (legacy approach)
CREATE VIEW sales_filtered AS
SELECT * FROM sales
WHERE region = CASE
  WHEN current_user() = 'admin@company.com' THEN region
  ELSE 'US'
END;
```

**Questões Típicas**:
```
Q: Formato do fully-qualified table name em Unity Catalog?
A: catalog.schema.table

Q: Como dar SELECT permission para user em table?
A: GRANT SELECT ON TABLE catalog.schema.table TO `user@email.com`

Q: Como mascarar PII column (email) para non-admins?
A: Column-level masking ou dynamic views

Q: Onde ver audit logs de data access?
A: Unity Catalog audit logs (system tables)
```

---

## 🎯 Estratégia de Estudo (6 Semanas)

### Semana 1: Platform & Basics (20h)
- **Dias 1-2**: Lakehouse architecture, benefits
- **Dias 3-4**: Clusters (types, modes), DBFS
- **Dia 5**: Repos, Git integration
- **Dias 6-7**: Practice labs
- **Projeto**: Setup workspace, explore UI

### Semana 2: Spark SQL & DataFrames (20h)
- **Dias 8-10**: DataFrame API (transformations, actions)
- **Dias 11-12**: Spark SQL (DDL, DML, queries)
- **Dia 13**: Managed vs External tables, Views
- **Dia 14**: Practice problems
- **Projeto**: Build ETL with DataFrames

### Semana 3: Delta Lake (20h)
- **Dias 15-16**: Delta Lake basics, ACID
- **Dia 17**: MERGE (upserts)
- **Dia 18**: Time travel, RESTORE
- **Dia 19**: OPTIMIZE, ZORDER, VACUUM
- **Dias 20-21**: Practice labs
- **Projeto**: Incremental pipeline with MERGE

### Semana 4: Streaming & Auto Loader (20h)
- **Dias 22-23**: Structured Streaming basics
- **Dia 24**: Auto Loader (cloudFiles)
- **Dia 25**: Triggers, output modes
- **Dia 26**: Checkpoints
- **Dias 27-28**: Practice labs
- **Projeto**: Streaming pipeline S3 → Delta

### Semana 5: Production & DLT (20h)
- **Dias 29-30**: Delta Live Tables
- **Dia 31**: Expectations (data quality)
- **Dia 32**: Jobs, scheduling
- **Dia 33**: Monitoring
- **Dias 34-35**: Practice labs
- **Projeto**: Production DLT pipeline

### Semana 6: Governance & Review (20h)
- **Dia 36**: Unity Catalog
- **Dia 37**: Access control, grants
- **Dia 38**: PII masking
- **Dias 39-40**: Review todos os tópicos
- **Dia 41**: Practice exam #1
- **Dia 42**: Study gaps
- **Dia 43**: Practice exam #2
- **Dia 44**: Final review
- **Dia 45**: PROVA! 🎉

**Total**: 120 horas, ~20h/semana

---

## 🛠️ Labs Práticos

### Lab 1: Workspace Setup (2h)
1. Create Databricks workspace (Community Edition ou trial)
2. Create all-purpose cluster
3. Upload sample data
4. Create notebook
5. Run basic Spark commands

### Lab 2: Data Exploration (3h)
1. Read CSV/JSON/Parquet
2. DataFrame transformations
3. Aggregations
4. Joins
5. Write results

### Lab 3: Delta Lake (4h)
1. Create Delta table
2. Insert, update, delete
3. MERGE (upsert)
4. Time travel
5. OPTIMIZE + ZORDER

### Lab 4: Streaming (4h)
1. Setup Auto Loader
2. Process JSON files from S3
3. Write to Delta
4. Handle schema evolution
5. Checkpoint management

### Lab 5: Production Pipeline (5h)
1. Create DLT pipeline
2. Bronze → Silver → Gold layers
3. Add expectations
4. Schedule as job
5. Monitor & debug

**Total labs**: 18 horas

---

## 📝 Practice Questions (200+)

### Sample Questions:

**Q1**: What is benefit of Lakehouse over Data Lake?
```
A) Cheaper storage
B) ACID transactions ✅
C) Faster ingestion
D) Better compression

Resposta: B
Lakehouse = Data Lake + ACID + schema enforcement
```

**Q2**: Which trigger mode processes ALL available data once and stops?
```
A) processingTime="1 minute"
B) continuous="1 second"
C) availableNow=True ✅
D) Default (no trigger)

Resposta: C
availableNow=True ou once=True processa tudo uma vez
```

**Q3**: How to drop rows that don't satisfy constraint in DLT?
```
A) @dlt.expect()
B) @dlt.expect_or_drop() ✅
C) @dlt.expect_or_fail()
D) .filter()

Resposta: B
expect_or_drop: log + drop invalid rows
```

**Q4**: What does OPTIMIZE command do?
```
A) Compacts small files ✅
B) Deletes old versions
C) Updates statistics
D) Adds indexes

Resposta: A
OPTIMIZE compacts small files into larger ones
```

---

## 🎓 Recursos Recomendados

### Cursos (GRATUITOS!)
1. **Databricks Academy** (⭐⭐⭐⭐⭐):
   - Data Engineering with Databricks
   - Advanced Data Engineering with Databricks
   - Gratuito, hands-on notebooks

2. **Databricks Learning Pathways**:
   - Interactive tutorials
   - Grátis

### Practice Exams
1. **Databricks Official Practice Exam**: $20 (⭐⭐⭐⭐⭐)
2. **Udemy Practice Tests**: ~$15 (variável)
3. **GitHub free questions**: Buscar "Databricks practice questions"

### Community
1. **Databricks Community Edition**: Gratuito para praticar
2. **Stack Overflow**: Tag [databricks]
3. **Databricks Community Forums**

---

## 💡 Dicas para o Exame

### Gerais
- **90 minutos para 45 questões** = 2 min/questão
- **Maioria scenario-based**: Entenda o problema antes de ler opções
- **Eliminate obviously wrong** answers first
- **Flag difficult questions**, volte depois
- **Don't overthink**: Primeira intuição geralmente correta

### Palavras-Chave
- "cost-effective" → Job cluster, serverless
- "real-time" → Streaming, Auto Loader
- "production" → DLT, Job cluster
- "data quality" → DLT expectations
- "incremental" → MERGE, streaming
- "governance" → Unity Catalog

### Pegadinhas Comuns
- **All-purpose vs Job cluster**: Production sempre Job cluster
- **OPTIMIZE vs VACUUM**: OPTIMIZE compacts, VACUUM deletes old versions
- **Managed vs External**: External preserva data no DROP
- **trigger once vs processingTime**: once processa e para

---

## ✅ Checklist Final

Antes da prova:

- [ ] Entendo arquitetura Lakehouse
- [ ] Sei diferença entre cluster types
- [ ] Domino DataFrame API (select, filter, groupBy, etc)
- [ ] Sei escrever Spark SQL (DDL, DML, queries)
- [ ] Entendo Delta Lake (ACID, time travel, MERGE)
- [ ] Sei quando usar OPTIMIZE, ZORDER, VACUUM
- [ ] Domino Structured Streaming & Auto Loader
- [ ] Entendo Delta Live Tables (decorators, expectations)
- [ ] Conheço Unity Catalog (GRANT, REVOKE)
- [ ] Fiz practice exam: >80%
- [ ] Revisei erros dos practice exams

**Se tudo ✅, GO FOR IT! 🚀**

---

## 🎉 Após a Certificação

### ROI Esperado
- **Aumento salarial**: +$15K-30K
- **Novas oportunidades**: Senior DE, Lakehouse Engineer
- **Empresas**: Uber, Lyft, Shell, Bloomberg

### Próxima Certificação
- **Databricks Certified Data Engineer Professional** (next level)
- **Spark Developer Certification** (complementar)
- **AWS/GCP Data Engineering** (multi-cloud)

**Parabéns! Você é agora um Databricks Certified Data Engineer! 🏆**
