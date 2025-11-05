# ☁️ AWS Data Services para Engenharia de Dados

## 📋 Índice

1. [Visão Geral AWS Data Stack](#visão-geral-aws-data-stack)
2. [S3 - Data Lake](#s3---data-lake)
3. [AWS Glue - ETL Serverless](#aws-glue---etl-serverless)
4. [Amazon Athena - Query Engine](#amazon-athena---query-engine)
5. [Amazon Redshift - Data Warehouse](#amazon-redshift---data-warehouse)
6. [Amazon EMR - Big Data Processing](#amazon-emr---big-data-processing)
7. [Kinesis - Real-time Streaming](#kinesis---real-time-streaming)
8. [Arquiteturas Completas](#arquiteturas-completas)

---

## Visão Geral AWS Data Stack

### Componentes Principais

```
┌─────────────────────────────────────────────────────────────┐
│                    DATA SOURCES                             │
│  Databases | APIs | Applications | IoT | Logs | Events     │
└─────────────────┬───────────────────────────────────────────┘
                  │
        ┌─────────┴─────────┐
        │                   │
    ┌───▼──────┐      ┌────▼─────┐
    │ Kinesis  │      │  DMS     │
    │(Streaming│      │(CDC)     │
    └───┬──────┘      └────┬─────┘
        │                  │
        └─────────┬────────┘
                  ▼
          ┌──────────────┐
          │   S3 Bucket  │
          │  (Data Lake) │
          └──────┬───────┘
                 │
      ┌──────────┼──────────┐
      │          │          │
  ┌───▼───┐  ┌──▼────┐  ┌──▼────┐
  │ Glue  │  │  EMR  │  │Athena │
  │ ETL   │  │ Spark │  │ Query │
  └───┬───┘  └───┬───┘  └───┬───┘
      │          │          │
      └──────────┼──────────┘
                 ▼
         ┌──────────────┐
         │   Redshift   │
         │(Data Warehouse)
         └──────┬───────┘
                │
         ┌──────▼───────┐
         │  QuickSight  │
         │     (BI)     │
         └──────────────┘
```

### Comparação de Serviços

| Serviço | Uso | Custo | Quando Usar |
|---------|-----|-------|-------------|
| **S3** | Storage | Muito baixo | Data Lake, arquivos raw |
| **Athena** | Query ad-hoc | Pay-per-query | Análise exploratória |
| **Glue** | ETL | Pay-per-DPU-hour | ETL serverless |
| **EMR** | Big Data | Pay-per-hour | Spark/Hadoop jobs |
| **Redshift** | DW | Médio-Alto | Analytics, BI |
| **Kinesis** | Streaming | Pay-per-shard | Real-time data |

---

## S3 - Data Lake

### Conceitos Fundamentais

**S3 = Simple Storage Service**: Storage ilimitado, durável (99.999999999%), escalável.

### Storage Classes

```python
# Lifecycle policy example
lifecycle_config = {
    'Rules': [{
        'Id': 'archive-old-data',
        'Status': 'Enabled',
        'Prefix': 'data/',
        'Transitions': [
            {
                'Days': 30,
                'StorageClass': 'STANDARD_IA'  # Infrequent Access
            },
            {
                'Days': 90,
                'StorageClass': 'GLACIER'  # Archive
            },
            {
                'Days': 365,
                'StorageClass': 'DEEP_ARCHIVE'  # Cold archive
            }
        ],
        'Expiration': {
            'Days': 2555  # 7 years
        }
    }]
}
```

**Classes:**
- **Standard**: Acesso frequente (mais caro)
- **Standard-IA**: Infrequent Access (50% mais barato)
- **Glacier**: Archive (83% mais barato, retrieval minutos-horas)
- **Glacier Deep Archive**: Cold archive (95% mais barato, retrieval 12h)

### Data Lake Architecture (Bronze/Silver/Gold)

```python
# S3 bucket structure
s3://my-data-lake/
├── bronze/              # Raw data (as-is)
│   ├── orders/
│   │   └── year=2024/month=01/day=15/data.json
│   ├── customers/
│   └── events/
├── silver/              # Cleaned, validated
│   ├── orders/
│   │   └── year=2024/month=01/orders.parquet
│   ├── customers/
│   └── events/
└── gold/                # Business-level aggregates
    ├── sales_summary/
    ├── customer_360/
    └── kpis/

# Python boto3 - Upload to S3
import boto3
import pandas as pd

s3 = boto3.client('s3')

# Upload file
s3.upload_file(
    Filename='local_file.csv',
    Bucket='my-data-lake',
    Key='bronze/orders/2024/01/15/orders.csv'
)

# Upload DataFrame as Parquet
df = pd.DataFrame({'col1': [1, 2], 'col2': [3, 4]})
df.to_parquet('s3://my-data-lake/silver/orders/data.parquet')

# Read from S3
df = pd.read_parquet('s3://my-data-lake/silver/orders/data.parquet')
```

### S3 Best Practices

```python
# 1. Particionamento por data
s3://bucket/table/year=2024/month=01/day=15/data.parquet

# 2. Use Parquet/ORC (formato colunar)
df.to_parquet('s3://bucket/data.parquet', compression='snappy')

# 3. Server-Side Encryption
s3.put_object(
    Bucket='my-bucket',
    Key='sensitive-data.csv',
    Body=data,
    ServerSideEncryption='AES256'  # ou 'aws:kms'
)

# 4. Versioning (backup automático)
s3.put_bucket_versioning(
    Bucket='my-bucket',
    VersioningConfiguration={'Status': 'Enabled'}
)

# 5. Cross-Region Replication
replication_config = {
    'Role': 'arn:aws:iam::123456789:role/s3-replication',
    'Rules': [{
        'Status': 'Enabled',
        'Priority': 1,
        'Destination': {
            'Bucket': 'arn:aws:s3:::backup-bucket',
            'ReplicationTime': {'Status': 'Enabled', 'Time': {'Minutes': 15}}
        }
    }]
}
```

---

## AWS Glue - ETL Serverless

### O que é Glue?

**AWS Glue** = ETL serverless baseado em Apache Spark.

**Componentes:**
- **Glue Crawler**: Descobre schema automaticamente
- **Glue Data Catalog**: Metadata repository
- **Glue ETL Jobs**: Spark jobs (Python/Scala)
- **Glue Workflows**: Orquestração de jobs

### Glue Crawler

```python
import boto3

glue = boto3.client('glue')

# Criar Crawler
glue.create_crawler(
    Name='orders-crawler',
    Role='arn:aws:iam::123456789:role/GlueServiceRole',
    DatabaseName='raw_data',
    Targets={
        'S3Targets': [{
            'Path': 's3://my-data-lake/bronze/orders/'
        }]
    },
    SchemaChangePolicy={
        'UpdateBehavior': 'UPDATE_IN_DATABASE',
        'DeleteBehavior': 'LOG'
    },
    Schedule='cron(0 2 * * ? *)'  # Daily at 2am
)

# Run Crawler
glue.start_crawler(Name='orders-crawler')
```

### Glue ETL Job (PySpark)

```python
import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.sql.functions import *

# Initialize
args = getResolvedOptions(sys.argv, ['JOB_NAME', 'input_path', 'output_path'])
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args['JOB_NAME'], args)

# Read from Glue Catalog
datasource = glueContext.create_dynamic_frame.from_catalog(
    database="raw_data",
    table_name="orders"
)

# Transform to DataFrame
df = datasource.toDF()

# Transformations
df_clean = df \
    .filter(col("order_id").isNotNull()) \
    .withColumn("order_date", to_date(col("order_timestamp"))) \
    .withColumn("year", year(col("order_date"))) \
    .withColumn("month", month(col("order_date"))) \
    .dropDuplicates(["order_id"])

# Write to S3 (partitioned Parquet)
df_clean.write \
    .mode("overwrite") \
    .partitionBy("year", "month") \
    .parquet(args['output_path'])

job.commit()
```

### Glue Data Catalog

```python
# Query Glue Catalog
response = glue.get_table(
    DatabaseName='raw_data',
    Name='orders'
)

print(response['Table']['StorageDescriptor']['Columns'])
# [{'Name': 'order_id', 'Type': 'bigint'}, ...]

# Update table partition
glue.update_partition(
    DatabaseName='raw_data',
    TableName='orders',
    PartitionValueList=['2024', '01', '15'],
    PartitionInput={
        'Values': ['2024', '01', '15'],
        'StorageDescriptor': {
            'Location': 's3://my-bucket/orders/year=2024/month=01/day=15/',
            'InputFormat': 'org.apache.hadoop.mapred.TextInputFormat',
            'OutputFormat': 'org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat',
            'SerdeInfo': {'SerializationLibrary': 'org.apache.hadoop.hive.serde2.lazy.LazySimpleSerDe'}
        }
    }
)
```

---

## Amazon Athena - Query Engine

### O que é Athena?

**Amazon Athena** = Query engine serverless para S3 usando SQL (Presto).

**Características:**
- Pay-per-query ($5 per TB scanned)
- Sem servidor (serverless)
- Integração com Glue Catalog
- Suporta Parquet, ORC, JSON, CSV

### Queries Básicas

```sql
-- Criar database
CREATE DATABASE IF NOT EXISTS analytics;

-- Criar external table
CREATE EXTERNAL TABLE analytics.orders (
    order_id BIGINT,
    customer_id BIGINT,
    order_date DATE,
    total_amount DECIMAL(10,2),
    status STRING
)
PARTITIONED BY (year INT, month INT)
STORED AS PARQUET
LOCATION 's3://my-data-lake/silver/orders/';

-- Adicionar partições
MSCK REPAIR TABLE analytics.orders;

-- ou manualmente
ALTER TABLE analytics.orders ADD IF NOT EXISTS
PARTITION (year=2024, month=1)
LOCATION 's3://my-data-lake/silver/orders/year=2024/month=01/';

-- Query
SELECT 
    year,
    month,
    COUNT(*) as order_count,
    SUM(total_amount) as total_revenue
FROM analytics.orders
WHERE year = 2024
GROUP BY year, month;
```

### Otimizações Athena

```sql
-- 1. Usar Parquet/ORC (90% menos scan)
CREATE TABLE orders_parquet
WITH (format='PARQUET', parquet_compression='SNAPPY')
AS SELECT * FROM orders_csv;

-- 2. Particionar por colunas de filtro comum
CREATE TABLE orders
PARTITIONED BY (year INT, month INT, day INT)
...

-- 3. Usar CTAS (Create Table As Select) para pré-agregar
CREATE TABLE sales_summary
WITH (format='PARQUET')
AS
SELECT 
    DATE_TRUNC('day', order_date) as date,
    SUM(total_amount) as daily_revenue,
    COUNT(*) as order_count
FROM orders
GROUP BY DATE_TRUNC('day', order_date);

-- 4. Columnar projection (apenas colunas necessárias)
SELECT order_id, total_amount  -- Não SELECT *
FROM orders
WHERE year = 2024;
```

### Python com Athena

```python
import boto3
import time
import pandas as pd

athena = boto3.client('athena')

def query_athena(query, database='analytics', s3_output='s3://athena-results/'):
    # Start query execution
    response = athena.start_query_execution(
        QueryString=query,
        QueryExecutionContext={'Database': database},
        ResultConfiguration={'OutputLocation': s3_output}
    )
    
    query_execution_id = response['QueryExecutionId']
    
    # Wait for completion
    while True:
        status = athena.get_query_execution(QueryExecutionId=query_execution_id)
        state = status['QueryExecution']['Status']['State']
        
        if state in ['SUCCEEDED', 'FAILED', 'CANCELLED']:
            break
        
        time.sleep(1)
    
    if state == 'SUCCEEDED':
        # Get results
        results = athena.get_query_results(QueryExecutionId=query_execution_id)
        
        # Convert to DataFrame
        columns = [col['Label'] for col in results['ResultSet']['ResultSetMetadata']['ColumnInfo']]
        data = [[field.get('VarCharValue', '') for field in row['Data']] 
                for row in results['ResultSet']['Rows'][1:]]  # Skip header
        
        return pd.DataFrame(data, columns=columns)
    else:
        raise Exception(f"Query failed: {status['QueryExecution']['Status']['StateChangeReason']}")

# Usage
df = query_athena("SELECT * FROM orders WHERE year = 2024 LIMIT 1000")
```

---

## Amazon Redshift - Data Warehouse

### O que é Redshift?

**Amazon Redshift** = Data Warehouse colunar baseado em PostgreSQL.

**Características:**
- Columnar storage (compressão 3-10x)
- Massively Parallel Processing (MPP)
- Escalável (de 160GB a petabytes)
- Integração com S3 (Redshift Spectrum)

### Criar Cluster

```python
import boto3

redshift = boto3.client('redshift')

# Criar cluster
redshift.create_cluster(
    ClusterIdentifier='my-dw-cluster',
    NodeType='dc2.large',  # ou ra3.xlplus, ra3.4xlarge
    NumberOfNodes=2,
    MasterUsername='admin',
    MasterUserPassword='SecurePass123!',
    DBName='analytics',
    ClusterSubnetGroupName='my-subnet-group',
    VpcSecurityGroupIds=['sg-12345678'],
    PubliclyAccessible=False,
    Encrypted=True,
    KmsKeyId='arn:aws:kms:us-east-1:123456789:key/abc123'
)
```

### DDL e Data Loading

```sql
-- Criar tabela com dist e sort keys
CREATE TABLE sales (
    sale_id BIGINT IDENTITY(1,1),
    order_date DATE NOT NULL,
    customer_id BIGINT NOT NULL,
    product_id BIGINT NOT NULL,
    quantity INT,
    amount DECIMAL(10,2),
    PRIMARY KEY (sale_id)
)
DISTKEY (customer_id)      -- Distribuir por customer_id
SORTKEY (order_date);       -- Ordenar por data

-- COPY from S3 (mais eficiente)
COPY sales
FROM 's3://my-bucket/sales/'
IAM_ROLE 'arn:aws:iam::123456789:role/RedshiftCopyRole'
FORMAT AS PARQUET
TIMEFORMAT 'auto';

-- COPY com manifest (múltiplos arquivos)
COPY sales
FROM 's3://my-bucket/manifest.json'
IAM_ROLE 'arn:aws:iam::123456789:role/RedshiftCopyRole'
MANIFEST
FORMAT AS PARQUET;

-- UNLOAD para S3
UNLOAD ('SELECT * FROM sales WHERE year = 2024')
TO 's3://my-bucket/exports/sales_2024_'
IAM_ROLE 'arn:aws:iam::123456789:role/RedshiftUnloadRole'
FORMAT PARQUET
PARALLEL ON
MAXFILESIZE 1 GB;
```

### Redshift Spectrum (Query S3 direto)

```sql
-- Criar external schema (Glue Catalog)
CREATE EXTERNAL SCHEMA spectrum
FROM DATA CATALOG
DATABASE 'raw_data'
IAM_ROLE 'arn:aws:iam::123456789:role/RedshiftSpectrumRole';

-- Query S3 via Spectrum
SELECT 
    r.customer_id,
    r.total_amount,
    e.event_count
FROM sales r                          -- Redshift table
JOIN spectrum.events e                 -- S3 external table
    ON r.customer_id = e.customer_id
WHERE r.order_date >= '2024-01-01';
```

### Otimizações Redshift

```sql
-- 1. VACUUM (reorganizar dados após DELETEs)
VACUUM FULL sales;

-- 2. ANALYZE (atualizar estatísticas)
ANALYZE sales;

-- 3. Dist Style
-- AUTO, EVEN, KEY, ALL

-- KEY: Particionar por chave
CREATE TABLE orders (...) DISTKEY (customer_id);

-- ALL: Replicar tabela em todos os nodes (pequenas dim tables)
CREATE TABLE dim_country (...) DISTSTYLE ALL;

-- 4. Sort Keys
-- Acelera queries com filtros por essas colunas
CREATE TABLE logs (...) SORTKEY (timestamp);

-- Compound sort key (múltiplas colunas)
CREATE TABLE sales (...) COMPOUND SORTKEY (year, month, day);

-- 5. Compression
-- Redshift aplica automaticamente, mas pode especificar:
CREATE TABLE sales (
    order_id BIGINT ENCODE AZ64,
    customer_id BIGINT ENCODE AZ64,
    amount DECIMAL(10,2) ENCODE AZ64,
    status VARCHAR(20) ENCODE LZO
);
```

---

## Amazon EMR - Big Data Processing

### O que é EMR?

**EMR = Elastic MapReduce**: Managed Hadoop/Spark cluster.

**Componentes:**
- Hadoop, Spark, Hive, Presto, Flink
- Auto-scaling
- Spot instances (70% cheaper)

### Criar Cluster EMR

```python
import boto3

emr = boto3.client('emr')

# Criar cluster
response = emr.run_job_flow(
    Name='spark-data-processing',
    ReleaseLabel='emr-6.10.0',  # Latest version
    Applications=[
        {'Name': 'Spark'},
        {'Name': 'Hadoop'},
        {'Name': 'Hive'}
    ],
    Instances={
        'InstanceGroups': [
            {
                'Name': 'Master',
                'InstanceRole': 'MASTER',
                'InstanceType': 'm5.xlarge',
                'InstanceCount': 1
            },
            {
                'Name': 'Core',
                'InstanceRole': 'CORE',
                'InstanceType': 'm5.xlarge',
                'InstanceCount': 2
            },
            {
                'Name': 'Task',
                'InstanceRole': 'TASK',
                'InstanceType': 'm5.xlarge',
                'InstanceCount': 3,
                'Market': 'SPOT',  # Use spot instances
                'BidPrice': '0.10'
            }
        ],
        'Ec2KeyName': 'my-key-pair',
        'KeepJobFlowAliveWhenNoSteps': True
    },
    JobFlowRole='EMR_EC2_DefaultRole',
    ServiceRole='EMR_DefaultRole',
    VisibleToAllUsers=True,
    LogUri='s3://my-logs/emr/',
    BootstrapActions=[{
        'Name': 'Install Python packages',
        'ScriptBootstrapAction': {
            'Path': 's3://my-bucket/bootstrap.sh'
        }
    }]
)

cluster_id = response['JobFlowId']
```

### Submit Spark Job

```python
# Add Spark step
emr.add_job_flow_steps(
    JobFlowId=cluster_id,
    Steps=[{
        'Name': 'process-data',
        'ActionOnFailure': 'CONTINUE',
        'HadoopJarStep': {
            'Jar': 'command-runner.jar',
            'Args': [
                'spark-submit',
                '--deploy-mode', 'cluster',
                '--master', 'yarn',
                '--conf', 'spark.executor.memory=4g',
                '--conf', 'spark.executor.cores=2',
                's3://my-bucket/scripts/process_data.py',
                '--input', 's3://my-bucket/input/',
                '--output', 's3://my-bucket/output/'
            ]
        }
    }]
)
```

---

## Kinesis - Real-time Streaming

### Kinesis Data Streams

```python
import boto3
import json

kinesis = boto3.client('kinesis')

# Criar stream
kinesis.create_stream(
    StreamName='user-events',
    ShardCount=5
)

# Produzir evento
event = {
    'user_id': 12345,
    'event_type': 'page_view',
    'timestamp': '2024-01-15T10:30:00Z',
    'page': '/products/123'
}

kinesis.put_record(
    StreamName='user-events',
    Data=json.dumps(event),
    PartitionKey=str(event['user_id'])  # Mesmo user vai para mesmo shard
)

# Consumir eventos
shard_iterator = kinesis.get_shard_iterator(
    StreamName='user-events',
    ShardId='shardId-000000000000',
    ShardIteratorType='LATEST'
)['ShardIterator']

while True:
    response = kinesis.get_records(ShardIterator=shard_iterator, Limit=100)
    
    for record in response['Records']:
        data = json.loads(record['Data'])
        print(f"User {data['user_id']} - {data['event_type']}")
    
    shard_iterator = response['NextShardIterator']
    
    if not response['Records']:
        time.sleep(1)
```

### Kinesis Firehose (Delivery)

```python
firehose = boto3.client('firehose')

# Criar delivery stream para S3
firehose.create_delivery_stream(
    DeliveryStreamName='events-to-s3',
    DeliveryStreamType='DirectPut',
    S3DestinationConfiguration={
        'RoleARN': 'arn:aws:iam::123456789:role/FirehoseRole',
        'BucketARN': 'arn:aws:s3:::my-data-lake',
        'Prefix': 'bronze/events/year=!{timestamp:yyyy}/month=!{timestamp:MM}/day=!{timestamp:dd}/',
        'BufferingHints': {
            'SizeInMBs': 128,
            'IntervalInSeconds': 300  # 5 minutos
        },
        'CompressionFormat': 'GZIP',
        'DataFormatConversionConfiguration': {
            'Enabled': True,
            'SchemaConfiguration': {
                'DatabaseName': 'raw_data',
                'TableName': 'events',
                'Region': 'us-east-1',
                'RoleARN': 'arn:aws:iam::123456789:role/FirehoseRole'
            },
            'OutputFormatConfiguration': {
                'Serializer': {'ParquetSerDe': {}}
            }
        }
    }
)

# Put record
firehose.put_record(
    DeliveryStreamName='events-to-s3',
    Record={'Data': json.dumps(event)}
)
```

---

## Arquiteturas Completas

### Batch Architecture (Lambda Architecture)

```
Data Sources → S3 (Bronze) → Glue/EMR → S3 (Silver) → Redshift → QuickSight
     │                                      │
     └──────── Athena (ad-hoc queries) ────┘
```

### Streaming Architecture

```
Applications → Kinesis → Lambda → Kinesis Firehose → S3 → Glue → Redshift
                  │
                  └────→ Kinesis Analytics → CloudWatch Alarms
```

### Full Stack (Batch + Streaming)

```
         Batch Layer                    Speed Layer
              │                              │
    ┌─────────▼─────────┐        ┌─────────▼──────────┐
    │  S3 → Glue → S3   │        │ Kinesis → Lambda   │
    │  (Daily batches)  │        │  (Real-time)       │
    └─────────┬─────────┘        └──────────┬─────────┘
              │                              │
              └──────────┬───────────────────┘
                         ▼
                  ┌─────────────┐
                  │  Redshift   │
                  │ (Serving)   │
                  └──────┬──────┘
                         ▼
                  ┌─────────────┐
                  │ QuickSight  │
                  └─────────────┘
```

---

## 🎯 Best Practices AWS

- ✅ Use S3 para Data Lake (Bronze/Silver/Gold)
- ✅ Particione dados por data (year/month/day)
- ✅ Use Parquet/ORC (não CSV/JSON)
- ✅ Glue para ETL serverless < 100TB
- ✅ EMR para workloads > 100TB ou custom
- ✅ Athena para queries ad-hoc
- ✅ Redshift para DW com queries frequentes
- ✅ Kinesis para streaming < 1MB/record
- ✅ MSK (Kafka) para streaming > 1MB/record
- ✅ IAM roles (não access keys)
- ✅ Encryption at rest (S3, Redshift, etc)
- ✅ VPC para recursos privados
- ✅ CloudWatch para monitoring
- ✅ Cost Explorer para otimização de custos

---

**Próximo:** [02-gcp-data-services.md](./02-gcp-data-services.md)
