# AWS Certified Data Analytics - Specialty (DAS-C01)

**A certificação mais importante para Data Engineers em AWS**

## 📋 Informações Gerais

- **Código**: DAS-C01
- **Nível**: Specialty
- **Duração**: 180 minutos (3 horas)
- **Número de questões**: 65 questões
- **Formato**: Múltipla escolha e múltiplas respostas
- **Nota mínima**: 750/1000 (75%)
- **Custo**: $300 USD
- **Validade**: 3 anos
- **Idiomas**: Inglês, Japonês, Coreano, Chinês Simplificado
- **Modalidade**: Presencial (Pearson VUE) ou Online (proctored)

## 🎯 Para Quem é Esta Certificação

### ✅ Ideal para:
- Data Engineers com 1+ ano de experiência em AWS
- Analytics Engineers trabalhando com AWS
- Solutions Architects focados em dados
- Big Data Engineers migrando para cloud

### ❌ Não recomendado para:
- Iniciantes em cloud (faça AWS SAA primeiro)
- Quem nunca usou serviços AWS de dados
- Foco apenas em ML (faça AWS MLS-C01)

## 📊 Domínios do Exame

| Domínio | Peso | Tópicos-Chave |
|---------|------|---------------|
| **1. Collection** | 18% | Kinesis, MSK, DMS, DataSync, IoT |
| **2. Storage & Data Management** | 22% | S3, Lake Formation, Glue Catalog |
| **3. Processing** | 24% | EMR, Glue ETL, Lambda, Batch |
| **4. Analysis & Visualization** | 18% | Athena, Redshift, QuickSight, OpenSearch |
| **5. Security** | 18% | IAM, KMS, VPC, CloudTrail, Macie |

---

## 📚 Domínio 1: Collection (18%)

### Serviços Principais

#### Amazon Kinesis Family

**Kinesis Data Streams** (Real-time ingestion)
```python
# Conceitos-chave:
- Shards: 1 MB/sec write, 2 MB/sec read
- Retention: 24 hours (default), up to 365 days
- Enhanced fan-out: 2 MB/sec per consumer
- Partitioning: Usa partition key para distribuir entre shards

# Quando usar:
✅ Real-time analytics
✅ Log aggregation
✅ IoT telemetry
❌ Se precisa de ordering entre partitions (use SQS FIFO)
❌ Se dados > 1 MB (use S3 + SNS)

# Calculando número de shards necessário:
Incoming: 1000 records/sec × 1 KB = 1 MB/sec → 1 shard
Incoming: 10000 records/sec × 1 KB = 10 MB/sec → 10 shards
```

**Kinesis Data Firehose** (Near real-time, managed)
```python
# Diferenças vs Data Streams:
- Fully managed (sem shards para gerenciar)
- Near real-time (60 sec buffer ou 1 MB)
- Auto-scaling
- Integração direta: S3, Redshift, OpenSearch, Splunk

# Transformações:
- Lambda function para transformar dados
- Format conversion: JSON → Parquet/ORC
- Compression: GZIP, Snappy, ZIP

# Quando usar:
✅ Load para S3/Redshift sem código
✅ Format conversion automático
✅ Não precisa de processamento customizado
❌ Se precisa <1 min latency (use Data Streams)
❌ Se precisa replay de dados (use Data Streams)
```

**Kinesis Data Analytics** (SQL em streams)
```sql
-- Exemplo: Calcular média a cada 5 minutos
CREATE OR REPLACE STREAM "DESTINATION_SQL_STREAM" (
  user_id VARCHAR(16),
  avg_score DOUBLE
);

CREATE OR REPLACE PUMP "STREAM_PUMP" AS
INSERT INTO "DESTINATION_SQL_STREAM"
SELECT STREAM
  user_id,
  AVG(score) AS avg_score
FROM "SOURCE_SQL_STREAM_001"
GROUP BY user_id,
  STEP("SOURCE_SQL_STREAM_001".ROWTIME BY INTERVAL '5' MINUTE);

-- Quando usar:
✅ SQL analytics em tempo real
✅ Windowing simples
❌ Transformações complexas (use Spark on EMR)
```

#### Amazon MSK (Managed Streaming for Kafka)

```python
# Conceitos-chave:
- Fully managed Apache Kafka
- Multi-AZ por default
- Integração com Kafka Connect
- Schema Registry (Glue Schema Registry)

# MSK vs Kinesis:
MSK:
  ✅ Kafka ecosystem (Kafka Connect, KSQL)
  ✅ Exatamente Apache Kafka (portabilidade)
  ✅ Retention ilimitada
  ❌ Você gerencia brokers
  ❌ Mais caro

Kinesis:
  ✅ Fully managed (zero ops)
  ✅ Mais barato
  ✅ Integração nativa AWS
  ❌ Vendor lock-in
  ❌ Retention max 365 dias
```

#### AWS Database Migration Service (DMS)

```python
# Casos de uso:
1. Database → S3 (CDC)
2. Database → Database (homogêneo/heterogêneo)
3. Database → Redshift
4. Database → Kinesis

# Tipos de migração:
- Full load: Migração completa uma vez
- CDC (Change Data Capture): Replicação contínua
- Full load + CDC: Migração + sync

# SCT (Schema Conversion Tool):
- Converte schema entre engines diferentes
- Oracle → PostgreSQL
- SQL Server → MySQL
```

**Questões Típicas**:
```
Q: Empresa precisa ingerir 10K eventos/sec com <1 second latency.
   Qual serviço usar?

A: Kinesis Data Streams (não Firehose por causa latência)

Q: Ingerir logs e salvar em S3 em Parquet. Sem código custom.

A: Kinesis Firehose com format conversion

Q: Migrar Oracle on-premises para Aurora. Replicação contínua.

A: DMS com CDC + SCT para converter schema
```

---

## 📚 Domínio 2: Storage & Data Management (22%)

### Amazon S3 (Simple Storage Service)

```python
# Storage Classes:
S3 Standard:           $0.023/GB  (hot data)
S3 Intelligent-Tiering: $0.023/GB  (auto-tiering)
S3 IA:                 $0.0125/GB (warm data)
S3 Glacier Instant:    $0.004/GB  (archive, ms retrieval)
S3 Glacier Flexible:   $0.0036/GB (archive, min-hours retrieval)
S3 Glacier Deep:       $0.00099/GB (archive, 12h retrieval)

# Lifecycle policies:
{
  "Rules": [{
    "Id": "Archive old logs",
    "Status": "Enabled",
    "Transitions": [
      {"Days": 30, "StorageClass": "STANDARD_IA"},
      {"Days": 90, "StorageClass": "GLACIER"},
      {"Days": 365, "StorageClass": "DEEP_ARCHIVE"}
    ],
    "Expiration": {"Days": 2555}  # 7 years
  }]
}

# Data Lake padrão:
s3://datalake/
  raw/          # Bronze layer
    year=2024/
      month=01/
        day=15/
          data.parquet
  processed/    # Silver layer
    table=users/
      year=2024/
        month=01/
          data.parquet
  curated/      # Gold layer
    analytics/
      daily_metrics/
        date=2024-01-15/
          data.parquet
```

### AWS Lake Formation

```python
# O que faz:
- Centralized data lake management
- Fine-grained access control (column-level)
- Data catalog (Glue Catalog)
- Blueprints para ingestion

# Permissions:
- Table-level: Controla acesso a tabelas
- Column-level: Mascara colunas sensíveis (PII)
- Row-level filtering: WHERE clauses automáticos

# Exemplo:
-- Analista vê apenas:
SELECT name, email_masked, age
FROM users
WHERE region = 'us-east-1'  -- Automatic row filter

-- DBA vê tudo:
SELECT name, email, age, ssn
FROM users
```

### AWS Glue Data Catalog

```python
# Centraliza metadados:
- Database definitions
- Table schemas
- Partitions
- Statistics

# Crawlers:
- Auto-detect schema
- Cria/atualiza tabelas
- Detecta partições
- Schedule: Hourly, Daily, Weekly, On-demand

# Integração:
- Athena: Query sem definir schema
- Redshift Spectrum: External tables
- EMR: Hive Metastore
- Glue ETL: Data Catalog como source/target
```

**Questões Típicas**:
```
Q: Data lake com 10 TB. Acesso frequente apenas last 30 days.
   Como otimizar custo?

A: Lifecycle policy:
   - 0-30 days: S3 Standard
   - 30-90 days: S3 IA
   - 90+ days: Glacier Flexible

Q: Analistas devem ver tabela users mas não SSN column.

A: Lake Formation column-level permissions

Q: Novos arquivos chegam diariamente em S3. Como atualizar catalog?

A: Glue Crawler scheduled daily
```

---

## 📚 Domínio 3: Processing (24%)

### Amazon EMR (Elastic MapReduce)

```python
# Quando usar EMR:
✅ Spark, Hadoop, Hive, Presto
✅ Processamento complexo
✅ Controle total do cluster
❌ ETL simples (use Glue)
❌ SQL analytics (use Athena)

# Cluster types:
- Transient (ephemeral): Cria, processa, termina
  * Mais barato
  * Use para batch jobs

- Long-running (persistent): Cluster sempre up
  * Mais caro
  * Use para interactive queries, notebooks

# Instâncias:
Master: m5.xlarge (1 node)
Core: r5.4xlarge (2+ nodes) - HDFS storage
Task: c5.4xlarge (0+ nodes) - Compute only, pode usar Spot

# Storage:
- HDFS: Temporário, vai embora com cluster
- S3: Persistente, recomendado para data lake
- EBS: Persistent volumes

# Otimizações:
- Use Spot instances para task nodes (70% desconto)
- S3DistCp para mover dados S3 → HDFS (faster)
- Dynamic allocation para auto-scaling
- Glue Catalog como Hive Metastore
```

**PySpark no EMR**:
```python
from pyspark.sql import SparkSession

spark = SparkSession.builder \
    .appName("EMR Job") \
    .config("spark.sql.catalogImplementation", "hive") \
    .enableHiveSupport() \
    .getOrCreate()

# Read from S3
df = spark.read.parquet("s3://bucket/raw/data/")

# Transform
df_clean = df \
    .filter(df.amount > 0) \
    .groupBy("user_id").sum("amount")

# Write to S3 (partitioned)
df_clean.write \
    .mode("overwrite") \
    .partitionBy("date") \
    .parquet("s3://bucket/processed/user_totals/")

# Register as Hive table (accessible from Athena)
df_clean.createOrReplaceTempView("user_totals")
spark.sql("CREATE EXTERNAL TABLE user_totals LOCATION 's3://...'")
```

### AWS Glue ETL

```python
# Quando usar Glue:
✅ ETL simples/médio
✅ Serverless (zero ops)
✅ Python or Scala
❌ Processamento muito complexo (use EMR)
❌ Streaming real-time (use Kinesis Analytics ou Spark Streaming)

# Job types:
- Spark: PySpark ou Scala (default)
- Python Shell: Python sem Spark (lightweight, < 1 DPU)
- Streaming: Spark Streaming com Kinesis/Kafka

# DPUs (Data Processing Units):
1 DPU = 4 vCPU + 16 GB memory
Cost: $0.44/DPU-hour

Standard: 2 DPUs (min)
Flexível: 0.25 DPUs (min) - Para Python Shell

# Job Bookmarks:
- Track o que já foi processado
- Evita reprocessamento
- Funciona com: S3, JDBC, DynamoDB
```

**Glue Script Example**:
```python
import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job

args = getResolvedOptions(sys.argv, ['JOB_NAME'])
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args['JOB_NAME'], args)

# Read from Glue Catalog
datasource = glueContext.create_dynamic_frame.from_catalog(
    database = "my_database",
    table_name = "raw_data"
)

# Transform
mapped = ApplyMapping.apply(
    frame = datasource,
    mappings = [
        ("user_id", "long", "user_id", "long"),
        ("amount", "double", "amount", "double"),
        ("timestamp", "string", "event_date", "date")
    ]
)

# Write to S3 + update catalog
glueContext.write_dynamic_frame.from_catalog(
    frame = mapped,
    database = "my_database",
    table_name = "processed_data"
)

job.commit()
```

### AWS Lambda

```python
# Quando usar para Data Engineering:
✅ Lightweight transformations
✅ Trigger-based (S3 event → process)
✅ Orchestration (Step Functions)
❌ Processamento pesado (max 15 min, 10 GB memory)
❌ Transformações complexas

# Exemplo: S3 trigger → Lambda → process
import json
import boto3

s3 = boto3.client('s3')

def lambda_handler(event, context):
    # S3 event
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = event['Records'][0]['s3']['object']['key']

    # Read file
    obj = s3.get_object(Bucket=bucket, Key=key)
    data = obj['Body'].read().decode('utf-8')

    # Process (example: count lines)
    line_count = len(data.split('\n'))

    # Write result
    s3.put_object(
        Bucket=bucket,
        Key=f'processed/{key}.metadata',
        Body=json.dumps({'line_count': line_count})
    )

    return {'statusCode': 200}
```

**Questões Típicas**:
```
Q: ETL de 1 TB/dia com transformações complexas (joins, aggregations).
   Qual serviço?

A: EMR com Spark (Glue tem limite de scale)

Q: Converter JSON files para Parquet diariamente. 100 GB/dia.

A: Glue ETL job (serverless, suficiente para este volume)

Q: Notificar quando arquivo chega em S3 e processar metadata.

A: S3 Event → Lambda

Q: Processar stream em real-time com windowing complexo.

A: Kinesis Data Streams + Spark Streaming on EMR
   (Glue Streaming também funciona mas EMR tem mais controle)
```

---

## 📚 Domínio 4: Analysis & Visualization (18%)

### Amazon Athena

```python
# Serverless SQL queries em S3
# Pay per query: $5 / TB scanned

# Best practices para reduzir custo:
1. Particionar dados:
   s3://bucket/data/year=2024/month=01/day=15/

   SELECT * FROM table WHERE year=2024 AND month=1
   # Scans apenas partition, não toda tabela!

2. Usar formato columnar (Parquet/ORC):
   JSON: 100% scan
   Parquet: ~10% scan (se SELECT apenas algumas colunas)
   Savings: 90%!

3. Compression:
   Uncompressed: 1 GB
   Snappy: 300 MB (3x menos scan)

4. CTAS (Create Table As Select):
   -- Converte para Parquet + particiona
   CREATE TABLE optimized
   WITH (
     format = 'PARQUET',
     parquet_compression = 'SNAPPY',
     partitioned_by = ARRAY['year', 'month']
   ) AS
   SELECT * FROM raw_json_table;
```

**Athena Workgroups**:
```python
# Separar queries por:
- Team (analytics, data-science, finance)
- Environment (dev, prod)
- Cost control (query limits)

# Features:
- Query result location (different S3 paths)
- Data usage controls (bytes scanned limit)
- Query history
- IAM permissions
```

### Amazon Redshift

```python
# Data warehouse MPP (Massively Parallel Processing)
# Use cases:
✅ OLAP queries
✅ Complex joins
✅ Large aggregations
❌ OLTP (use RDS)
❌ Real-time ingestion (use Kinesis first)

# Arquitetura:
Leader node: Coordena queries
Compute nodes: Processam dados
  - Slices: Cada compute node tem 2-16 slices

# Node types:
RA3: Managed storage (S3), escala compute e storage independentemente
DC2: Local SSD storage, mais rápido mas storage fixo

# Distribution styles:
KEY: Distribui por column (use para joins)
  CREATE TABLE orders (
    order_id INT,
    user_id INT,
    amount DECIMAL
  ) DISTKEY(user_id);  -- Co-locate orders with users

ALL: Replica em todos nodes (small dimension tables)
  CREATE TABLE countries (...)
  DISTSTYLE ALL;

EVEN: Round-robin (default, use quando não sabe)

AUTO: Redshift decide (recomendado)

# Sort keys:
- Single column: ORDER BY frequente
- Compound: WHERE em múltiplas colunas em ordem
- Interleaved: WHERE em qualquer combinação de colunas

CREATE TABLE events (
  user_id INT,
  event_date DATE,
  event_type VARCHAR(50)
) SORTKEY(event_date, user_id);  -- Compound
```

**Redshift Spectrum**:
```sql
-- Query S3 directly from Redshift (sem carregar)

CREATE EXTERNAL SCHEMA spectrum_schema
FROM DATA CATALOG
DATABASE 'glue_db'
IAM_ROLE 'arn:aws:iam::123456789:role/RedshiftSpectrum';

-- Query S3 data
SELECT
  r.user_id,
  r.name,
  s.total_purchases
FROM redshift_table r
JOIN spectrum_schema.s3_purchases s ON r.user_id = s.user_id;

-- Hybrid: Hot data em Redshift, cold data em S3
```

### Amazon QuickSight

```python
# BI tool serverless
# Pricing: $9/user/month (Reader), $18/user/month (Author)

# Data sources:
- Redshift, Athena, RDS, S3
- SPICE (in-memory): 10 GB/user included
  * Muito mais rápido que query direto
  * Auto-refresh (hourly, daily)

# Q (ML-powered):
- Natural language queries
- "Show me sales by region last quarter"
- Auto-generates visualizations

# Features:
- Dashboards: Interactive, drill-down
- Paginated reports: PDF, email schedule
- Embedded analytics: iframe em apps
- Row-level security: users veem apenas seu data
```

**Questões Típicas**:
```
Q: Queries SQL ad-hoc em 10 TB Parquet data em S3. Custo-efetivo.

A: Athena (serverless, pay per query)

Q: 500 GB analytical database. Complex joins diários. Sub-second queries.

A: Redshift (data warehouse)

Q: Query 50 TB historical data + 500 GB recent data com low latency.

A: Redshift (recent) + Redshift Spectrum (historical em S3)

Q: Dashboards interativos para 100 business users.

A: QuickSight com SPICE (in-memory para performance)
```

---

## 📚 Domínio 5: Security (18%)

### IAM (Identity and Access Management)

```python
# Princípios:
1. Least privilege: Apenas permissões necessárias
2. Separation of duties: Diferentes roles para diferentes tasks
3. Use roles, not users: EC2, Lambda usam roles, não access keys

# Policies:
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": [
      "s3:GetObject",
      "s3:PutObject"
    ],
    "Resource": "arn:aws:s3:::my-bucket/data/*",
    "Condition": {
      "IpAddress": {
        "aws:SourceIp": "203.0.113.0/24"
      }
    }
  }]
}

# Resource-based policies (S3 bucket policy):
{
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"AWS": "arn:aws:iam::123456789:role/GlueRole"},
    "Action": "s3:GetObject",
    "Resource": "arn:aws:s3:::my-bucket/*"
  }]
}
```

### KMS (Key Management Service)

```python
# Encryption:
- At rest: S3, EBS, RDS, Redshift
- In transit: TLS/SSL

# KMS keys:
- AWS managed: Grátis, rotação automática
- Customer managed: $1/month, você controla
- Custom key store: CloudHSM (compliance)

# Envelope encryption:
1. Data key encrypts data
2. Master key (KMS) encrypts data key
3. Store encrypted data + encrypted data key

# S3 encryption:
SSE-S3: AWS manages keys (AES-256)
SSE-KMS: Você controla key via KMS (audit trail)
SSE-C: Você provê key a cada request
Client-side: Encrypt antes de upload
```

### VPC & Networking

```python
# VPC Endpoints:
- Gateway endpoints: S3, DynamoDB (grátis)
- Interface endpoints: Outros serviços ($0.01/hr)

# Benefit: Tráfego não sai da AWS network (security + performance)

# NAT Gateway:
- Private subnet acessa internet
- $0.045/hr + $0.045/GB data processed
- Tip: Usar VPC endpoints para S3 reduz custo NAT

# Security Groups vs NACLs:
Security Groups:
  - Stateful (return traffic automático)
  - Instance-level
  - Only ALLOW rules

NACLs:
  - Stateless (precisa rule para return)
  - Subnet-level
  - ALLOW e DENY rules
```

### CloudTrail & Monitoring

```python
# CloudTrail:
- Audit log de todas API calls
- Quem fez o quê, quando
- Compliance, security analysis

# CloudWatch:
- Metrics: CPU, memory, custom metrics
- Logs: Centralize logs de todos serviços
- Alarms: Trigger SNS quando metric > threshold

# Athena queries em CloudTrail logs:
SELECT
  useridentity.principalid,
  eventname,
  COUNT(*) as count
FROM cloudtrail_logs
WHERE eventtime > '2024-01-01'
GROUP BY useridentity.principalid, eventname
ORDER BY count DESC;
```

**Questões Típicas**:
```
Q: Data lake em S3. Analistas precisam acesso mas não podem deletar.

A: IAM policy com s3:GetObject, s3:PutObject (sem s3:DeleteObject)

Q: Redshift cluster em private subnet precisa carregar de S3.

A: VPC endpoint para S3 (gateway endpoint, grátis)

Q: Compliance requer audit de quem acessou quais objetos em S3.

A: CloudTrail + S3 access logs + Athena para queries

Q: Encrypt data em Redshift com keys que empresa controla.

A: Redshift encryption com customer-managed KMS key
```

---

## 🎯 Estratégia de Estudo (8 Semanas)

### Semana 1-2: Collection & Storage
- **Dias 1-3**: Kinesis (Data Streams, Firehose, Analytics)
- **Dias 4-5**: MSK vs Kinesis
- **Dias 6-7**: DMS + DataSync
- **Dias 8-10**: S3 deep dive (storage classes, lifecycle)
- **Dias 11-12**: Lake Formation
- **Dias 13-14**: Glue Catalog + Crawlers
- **Projeto**: Build data lake com ingestion real-time

### Semana 3-4: Processing
- **Dias 15-17**: EMR (Spark, Hive, Presto)
- **Dias 18-20**: Glue ETL
- **Dias 21-22**: Lambda para data processing
- **Dias 23-24**: AWS Batch
- **Dias 25-26**: Step Functions (orchestration)
- **Dias 27-28**: Review + labs
- **Projeto**: ETL pipeline completo (raw → processed → curated)

### Semana 5-6: Analysis & Viz
- **Dias 29-31**: Athena (optimization, CTAS)
- **Dias 32-35**: Redshift (architecture, optimization)
- **Dias 36-37**: Redshift Spectrum
- **Dias 38-39**: QuickSight
- **Dias 40-42**: OpenSearch (ElasticSearch)
- **Projeto**: Analytics platform com Redshift + Athena + QuickSight

### Semana 7: Security & Operations
- **Dias 43-44**: IAM (policies, roles)
- **Dias 45-46**: KMS, encryption
- **Dias 47-48**: VPC, networking
- **Dias 49**: CloudTrail, CloudWatch
- **Projeto**: Secure data lake (least privilege, encryption)

### Semana 8: Review & Mock Exams
- **Dias 50-52**: Review notas, flashcards
- **Dia 53**: Mock exam #1
- **Dias 54-55**: Study gaps
- **Dia 56**: Mock exam #2
- **Dia 57**: Final review
- **Dia 58-59**: Relaxar, dormir bem
- **Dia 60**: PROVA! 🎉

**Total**: 60 dias, ~3 horas/dia = 180 horas

---

## 🛠️ Labs Práticos (Hands-On)

Ver pasta `labs/` para step-by-step tutorials:

1. **Lab 01**: Kinesis Data Streams + Lambda consumer
2. **Lab 02**: Kinesis Firehose → S3 com format conversion
3. **Lab 03**: Glue Crawler + Athena queries
4. **Lab 04**: Glue ETL job (JSON → Parquet)
5. **Lab 05**: EMR cluster com Spark
6. **Lab 06**: S3 Data Lake com Lake Formation permissions
7. **Lab 07**: Redshift data warehouse
8. **Lab 08**: Redshift Spectrum (query S3 from Redshift)
9. **Lab 09**: QuickSight dashboard
10. **Lab 10**: End-to-end pipeline (Kinesis → S3 → Glue → Redshift → QuickSight)

**Tempo total labs**: ~40 horas

---

## 📝 Questões de Exemplo

Ver pasta `questoes-exemplo/` para 200+ practice questions.

**Exemplo 1**:
```
Uma empresa precisa processar logs de aplicação em tempo real.
Os logs chegam a 5 MB/sec. Analistas querem queries SQL em near real-time.

Qual arquitetura recomendada?

A) Kinesis Data Streams → Lambda → DynamoDB → QuickSight
B) Kinesis Firehose → S3 → Athena → QuickSight
C) MSK → Spark Streaming → Redshift → QuickSight
D) S3 → Glue → Redshift → QuickSight

Resposta: B
- Firehose: Near real-time, managed, <60 sec
- S3: Persistent storage
- Athena: Serverless SQL queries
- QuickSight: Visualization

Por que não outras:
A) DynamoDB não é ideal para analytics
C) Over-engineering para 5 MB/sec
D) Não é real-time (S3 primeiro não faz sentido)
```

**Exemplo 2**:
```
Data lake tem 10 PB em S3. Queries Athena custam $50K/mês.
90% das queries são nos últimos 6 meses.

Como reduzir custo mantendo performance?

A) Mover old data para Glacier
B) Particionar por data + usar WHERE clauses
C) Converter para Parquet com Snappy compression
D) Usar Redshift em vez de Athena

Resposta: C (melhor opção), B também ajuda
- Parquet: 10x menos data scanned (columnar)
- Snappy: 3x compression
- Savings: 30x = $1.7K/mês (saving $48.3K)

B também correto mas C tem maior impacto.
D) Seria mais caro (Redshift cluster 24/7)
```

---

## 🎓 Recursos Recomendados

### Cursos
1. **A Cloud Guru**: AWS Certified Data Analytics Specialty (⭐⭐⭐⭐⭐)
2. **Udemy - Stephane Maarek**: Ultimate AWS Data Analytics (⭐⭐⭐⭐⭐)
3. **AWS Training**: Data Analytics Fundamentals (gratuito)

### Livros
1. **AWS Certified Data Analytics Study Guide** - Ben Piper
2. **AWS Big Data Specialty Certification Guide** - Naresh Kumar

### Practice Exams
1. **Tutorials Dojo**: AWS DAS Practice Exams ($15) ⭐⭐⭐⭐⭐
2. **Whizlabs**: AWS Data Analytics Practice Tests ($20)
3. **AWS Official Practice Exam**: ($40)

### Hands-On
1. **AWS Free Tier**: S3, Lambda, Glue (limited)
2. **Qwiklabs**: AWS Data Analytics Quest
3. **CloudAcademy**: AWS Data Analytics Learning Path

---

## 💡 Dicas para o Exame

### Durante o Exame
1. **Leia com atenção**: Muitas perguntas têm palavras-chave importantes
   - "cost-effective" → serverless, pay-per-use
   - "real-time" → Kinesis Data Streams
   - "near real-time" → Kinesis Firehose
   - "minimum operational overhead" → managed services

2. **Eliminação**: Descarte opções obviamente erradas primeiro

3. **Gestão de tempo**: 180 min ÷ 65 questions = 2.8 min/question
   - Marque difíceis, volte depois
   - Não gaste >3 min em uma questão

4. **Scenario-based**: Maioria das questões são cenários reais
   - Entenda o problema
   - Identifique requirements (performance, cost, complexity)
   - Escolha melhor fit

### Pegadinhas Comuns
- **Kinesis vs MSK**: Kinesis para AWS-native, MSK para Kafka ecosystem
- **Glue vs EMR**: Glue para ETL simples, EMR para processamento complexo
- **Athena vs Redshift**: Athena para ad-hoc, Redshift para frequent complex queries
- **Lake Formation**: Sempre considerar para data lake security
- **Redshift Spectrum**: Para query S3 de dentro do Redshift

---

## ✅ Checklist Final

Antes de agendar a prova, tenha certeza:

- [ ] Completei todos os tópicos (5 domínios)
- [ ] Fiz pelo menos 10 labs hands-on
- [ ] Mock exam #1: >80%
- [ ] Mock exam #2: >85%
- [ ] Revisei todos os erros dos mocks
- [ ] Conheço bem os serviços principais (15+)
- [ ] Entendo trade-offs (cost, performance, complexity)
- [ ] Sei calcular: shards, DPUs, storage costs
- [ ] Consigo desenhar arquiteturas completas
- [ ] Li whitepapers principais (opcional mas ajuda)

**Se tudo ✅, você está pronto! Boa sorte! 🚀**

---

## 📊 Após a Certificação

### Próximos Passos
1. **Atualizar LinkedIn** com certificação
2. **Pedir reembolso** da empresa (se aplicável)
3. **Adicionar ao currículo**
4. **Considerar próxima cert**: GCP Data Engineer ou Databricks

### Manutenção
- **Validade**: 3 anos
- **Recertificação**: Fazer exame novamente ou acumular 80 CE (Continuing Education) credits
- **CE credits**: Cursos AWS, webinars, re:Invent attendance

### ROI Esperado
- **Salário**: +$10K-20K/ano
- **Jobs**: Senior Data Engineer, Cloud Data Engineer
- **Empresas**: Qualquer empresa usando AWS para dados

**Parabéns pela certificação! 🎉**
