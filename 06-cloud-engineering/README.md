#  Módulo 6: Cloud Data Engineering

## =Ë Visão Geral

Cloud é essencial para engenharia de dados moderna. Este módulo cobre os três principais providers: AWS, GCP e Azure, com foco em serviços de dados.

**Duração:** 4-5 semanas | **Nível:** Intermediário-Avançado

---

## <¯ Objetivos

-  Dominar serviços de dados em AWS, GCP e Azure
-  Projetar arquiteturas serverless
-  Implementar Infrastructure as Code (Terraform)
-  Otimizar custos em cloud
-  Garantir segurança e compliance

---

## =Ú Conteúdo

### 1. AWS Data Services

#### 1.1 S3 (Simple Storage Service)

**Conceito:** Object storage escalável e durável.

```python
import boto3
from botocore.exceptions import ClientError

s3_client = boto3.client('s3')

# Upload de arquivo
def upload_file_to_s3(file_path, bucket, key):
    """Upload com retry e error handling"""
    try:
        s3_client.upload_file(
            file_path,
            bucket,
            key,
            ExtraArgs={
                'ServerSideEncryption': 'AES256',
                'StorageClass': 'INTELLIGENT_TIERING'  # Auto-otimização de custo
            }
        )
        print(f"Uploaded {file_path} to s3://{bucket}/{key}")
    except ClientError as e:
        print(f"Error uploading: {e}")

# Download com streaming
def download_large_file(bucket, key, local_path):
    """Download eficiente para arquivos grandes"""
    s3_client.download_file(bucket, key, local_path)

# List com paginação
def list_all_objects(bucket, prefix=''):
    """Lista TODOS os objetos (handles pagination)"""
    paginator = s3_client.get_paginator('list_objects_v2')
    pages = paginator.paginate(Bucket=bucket, Prefix=prefix)

    all_objects = []
    for page in pages:
        if 'Contents' in page:
            all_objects.extend(page['Contents'])

    return all_objects

# S3 Select (query CSV/JSON diretamente no S3)
def query_s3_with_select(bucket, key):
    """Query CSV no S3 sem baixar arquivo completo"""
    response = s3_client.select_object_content(
        Bucket=bucket,
        Key=key,
        ExpressionType='SQL',
        Expression="SELECT * FROM s3object s WHERE s.amount > 1000",
        InputSerialization={
            'CSV': {'FileHeaderInfo': 'USE', 'FieldDelimiter': ','}
        },
        OutputSerialization={'CSV': {}}
    )

    # Processar streaming response
    for event in response['Payload']:
        if 'Records' in event:
            records = event['Records']['Payload'].decode('utf-8')
            print(records)
```

**S3 Lifecycle Policies:**
```json
{
  "Rules": [
    {
      "Id": "Archive old data",
      "Status": "Enabled",
      "Filter": {
        "Prefix": "data/raw/"
      },
      "Transitions": [
        {
          "Days": 30,
          "StorageClass": "STANDARD_IA"
        },
        {
          "Days": 90,
          "StorageClass": "GLACIER"
        }
      ],
      "Expiration": {
        "Days": 365
      }
    }
  ]
}
```

#### 1.2 AWS Glue (ETL Serverless)

```python
# AWS Glue ETL Job
import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from awsglue.dynamicframe import DynamicFrame

# Inicializar Glue context
args = getResolvedOptions(sys.argv, ['JOB_NAME', 'INPUT_PATH', 'OUTPUT_PATH'])
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args['JOB_NAME'], args)

# Ler dados do S3
datasource = glueContext.create_dynamic_frame.from_options(
    connection_type="s3",
    connection_options={
        "paths": [args['INPUT_PATH']],
        "recurse": True
    },
    format="parquet"
)

# Aplicar transformações do Glue
# ApplyMapping: Renomear e converter tipos
mapped = ApplyMapping.apply(
    frame=datasource,
    mappings=[
        ("customer_id", "string", "customer_id", "long"),
        ("amount", "string", "amount", "double"),
        ("date", "string", "date", "date")
    ]
)

# Filter: Filtrar registros
filtered = Filter.apply(
    frame=mapped,
    f=lambda x: x["amount"] > 100
)

# DropNullFields: Remover campos nulos
cleaned = DropNullFields.apply(frame=filtered)

# ResolveChoice: Resolver tipos ambíguos
resolved = ResolveChoice.apply(
    frame=cleaned,
    choice="cast:long",
    transformation_ctx="resolved"
)

# Escrever resultado
glueContext.write_dynamic_frame.from_options(
    frame=resolved,
    connection_type="s3",
    connection_options={
        "path": args['OUTPUT_PATH'],
        "partitionKeys": ["date"]
    },
    format="parquet",
    transformation_ctx="datasink"
)

job.commit()
```

**Glue Data Catalog:**
```python
import boto3

glue_client = boto3.client('glue')

# Criar tabela no Glue Catalog
glue_client.create_table(
    DatabaseName='my_database',
    TableInput={
        'Name': 'sales',
        'StorageDescriptor': {
            'Columns': [
                {'Name': 'sale_id', 'Type': 'bigint'},
                {'Name': 'customer_id', 'Type': 'bigint'},
                {'Name': 'amount', 'Type': 'double'},
                {'Name': 'sale_date', 'Type': 'date'}
            ],
            'Location': 's3://bucket/data/sales/',
            'InputFormat': 'org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat',
            'OutputFormat': 'org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat',
            'SerdeInfo': {
                'SerializationLibrary': 'org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe'
            }
        },
        'PartitionKeys': [
            {'Name': 'year', 'Type': 'int'},
            {'Name': 'month', 'Type': 'int'}
        ]
    }
)

# Crawlers para descobrir schema automaticamente
glue_client.create_crawler(
    Name='sales_crawler',
    Role='AWSGlueServiceRole',
    DatabaseName='my_database',
    Targets={
        'S3Targets': [
            {'Path': 's3://bucket/data/sales/'}
        ]
    },
    Schedule='cron(0 1 * * ? *)'  # Diário à 1AM
)
```

#### 1.3 Amazon Athena (Query Engine)

```python
import boto3
import time

athena_client = boto3.client('athena')

def run_athena_query(query, database, output_location):
    """Executa query no Athena e aguarda resultado"""

    # Iniciar query
    response = athena_client.start_query_execution(
        QueryString=query,
        QueryExecutionContext={'Database': database},
        ResultConfiguration={'OutputLocation': output_location}
    )

    query_execution_id = response['QueryExecutionId']
    print(f"Query ID: {query_execution_id}")

    # Aguardar conclusão
    while True:
        status = athena_client.get_query_execution(
            QueryExecutionId=query_execution_id
        )

        state = status['QueryExecution']['Status']['State']

        if state == 'SUCCEEDED':
            print("Query succeeded!")
            break
        elif state in ['FAILED', 'CANCELLED']:
            reason = status['QueryExecution']['Status'].get('StateChangeReason', '')
            raise Exception(f"Query {state}: {reason}")

        time.sleep(2)

    # Obter resultados
    results = athena_client.get_query_results(
        QueryExecutionId=query_execution_id,
        MaxResults=1000
    )

    return results

# Exemplo de uso
query = """
SELECT
    date,
    SUM(amount) as total_amount,
    COUNT(*) as transaction_count
FROM sales
WHERE year = 2024 AND month = 1
GROUP BY date
ORDER BY date
"""

results = run_athena_query(
    query=query,
    database='my_database',
    output_location='s3://bucket/athena-results/'
)
```

**Otimizações Athena:**
```sql
-- 1. Particionar dados
CREATE EXTERNAL TABLE sales_partitioned (
    sale_id BIGINT,
    customer_id BIGINT,
    amount DOUBLE
)
PARTITIONED BY (year INT, month INT, day INT)
STORED AS PARQUET
LOCATION 's3://bucket/data/sales_partitioned/';

-- Adicionar partições
MSCK REPAIR TABLE sales_partitioned;

-- 2. Usar formato columnar (Parquet/ORC)
CREATE TABLE sales_optimized
WITH (
    format = 'PARQUET',
    parquet_compression = 'SNAPPY',
    partitioned_by = ARRAY['year', 'month']
) AS
SELECT * FROM sales_original;

-- 3. CTAS para pre-agregar
CREATE TABLE daily_summary AS
SELECT
    date,
    SUM(amount) as total_amount,
    COUNT(*) as count
FROM sales
GROUP BY date;
```

#### 1.4 Amazon Redshift (Data Warehouse)

```python
import psycopg2

# Conectar ao Redshift
conn = psycopg2.connect(
    host='cluster.region.redshift.amazonaws.com',
    port=5439,
    dbname='warehouse',
    user='admin',
    password='password'
)

cur = conn.cursor()

# COPY: Carregar dados do S3 (método mais eficiente)
cur.execute("""
    COPY sales
    FROM 's3://bucket/data/sales/'
    IAM_ROLE 'arn:aws:iam::account:role/RedshiftCopyRole'
    FORMAT AS PARQUET
    COMPUPDATE ON
    STATUPDATE ON;
""")

# UNLOAD: Exportar dados para S3
cur.execute("""
    UNLOAD ('SELECT * FROM sales WHERE date >= CURRENT_DATE - 7')
    TO 's3://bucket/exports/sales_'
    IAM_ROLE 'arn:aws:iam::account:role/RedshiftUnloadRole'
    FORMAT AS PARQUET
    PARALLEL ON;
""")

# Vacuum e Analyze (manutenção)
cur.execute("VACUUM DELETE ONLY sales;")
cur.execute("ANALYZE sales;")

conn.commit()
cur.close()
conn.close()
```

**Distribution Keys e Sort Keys:**
```sql
-- Distribution KEY: Como dados são distribuídos entre nodes
CREATE TABLE fact_sales (
    sale_id BIGINT,
    customer_id BIGINT,
    product_id BIGINT,
    amount DECIMAL(10,2)
)
DISTKEY(customer_id)  -- Distribui por customer_id
SORTKEY(sale_date);   -- Ordena por sale_date

-- Distribution styles:
-- KEY: Hash distribution (co-location)
-- ALL: Replica tabela em todos os nodes (para dimensões pequenas)
-- EVEN: Round-robin (quando não há boa chave)

CREATE TABLE dim_customer (
    customer_id BIGINT,
    customer_name VARCHAR(200)
)
DISTSTYLE ALL;  -- Pequena, replicar
```

#### 1.5 AWS EMR (Elastic MapReduce)

```python
import boto3

emr_client = boto3.client('emr')

# Criar cluster EMR
response = emr_client.run_job_flow(
    Name='DataProcessingCluster',
    ReleaseLabel='emr-6.15.0',
    Applications=[
        {'Name': 'Spark'},
        {'Name': 'Hive'},
        {'Name': 'Presto'}
    ],
    Instances={
        'InstanceGroups': [
            {
                'Name': 'Master',
                'Market': 'ON_DEMAND',
                'InstanceRole': 'MASTER',
                'InstanceType': 'r5.xlarge',
                'InstanceCount': 1
            },
            {
                'Name': 'Core',
                'Market': 'SPOT',  # Usar SPOT para economizar
                'InstanceRole': 'CORE',
                'InstanceType': 'r5.2xlarge',
                'InstanceCount': 2,
                'BidPrice': '0.50'
            }
        ],
        'Ec2KeyName': 'my-key',
        'KeepJobFlowAliveWhenNoSteps': False,  # Auto-termina
        'TerminationProtected': False
    },
    Steps=[
        {
            'Name': 'Process Sales Data',
            'ActionOnFailure': 'TERMINATE_CLUSTER',
            'HadoopJarStep': {
                'Jar': 'command-runner.jar',
                'Args': [
                    'spark-submit',
                    '--deploy-mode', 'cluster',
                    '--master', 'yarn',
                    's3://bucket/scripts/process_sales.py',
                    '--date', '2024-01-01'
                ]
            }
        }
    ],
    LogUri='s3://bucket/emr-logs/',
    ServiceRole='EMR_DefaultRole',
    JobFlowRole='EMR_EC2_DefaultRole',
    VisibleToAllUsers=True,
    Tags=[
        {'Key': 'Environment', 'Value': 'Production'},
        {'Key': 'CostCenter', 'Value': 'DataEngineering'}
    ]
)

cluster_id = response['JobFlowId']
print(f"Cluster created: {cluster_id}")
```

---

### 2. Google Cloud Platform (GCP) Data Services

#### 2.1 BigQuery

```python
from google.cloud import bigquery
from google.cloud.exceptions import GoogleCloudError

client = bigquery.Client()

# Query básica
def run_bigquery_query(query):
    """Executa query no BigQuery"""
    try:
        query_job = client.query(query)
        results = query_job.result()

        for row in results:
            print(f"{row['date']}: {row['total_amount']}")

        return results
    except GoogleCloudError as e:
        print(f"Error: {e}")

# Query com parâmetros (previne SQL injection)
def query_with_parameters(customer_id):
    """Query segura com parâmetros"""
    query = """
        SELECT
            sale_date,
            SUM(amount) as total
        FROM `project.dataset.sales`
        WHERE customer_id = @customer_id
        GROUP BY sale_date
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("customer_id", "INT64", customer_id)
        ]
    )

    query_job = client.query(query, job_config=job_config)
    return query_job.result()

# Carregar dados do GCS
def load_from_gcs(uri, table_id):
    """Carrega dados do GCS para BigQuery"""
    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.PARQUET,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        autodetect=True
    )

    load_job = client.load_table_from_uri(
        uri,
        table_id,
        job_config=job_config
    )

    load_job.result()  # Aguardar conclusão
    print(f"Loaded {load_job.output_rows} rows into {table_id}")

# Export para GCS
def export_to_gcs(table_id, destination_uri):
    """Exporta tabela para GCS"""
    job_config = bigquery.ExtractJobConfig(
        destination_format=bigquery.DestinationFormat.PARQUET,
        compression=bigquery.Compression.SNAPPY
    )

    extract_job = client.extract_table(
        table_id,
        destination_uri,
        job_config=job_config
    )

    extract_job.result()
    print(f"Exported {table_id} to {destination_uri}")
```

**BigQuery Advanced Features:**
```sql
-- 1. Particionamento por data
CREATE TABLE dataset.sales_partitioned
PARTITION BY DATE(sale_date)
CLUSTER BY customer_id, product_id
AS SELECT * FROM dataset.sales_original;

-- 2. Particionamento por range
CREATE TABLE dataset.events_partitioned
PARTITION BY RANGE_BUCKET(user_id, GENERATE_ARRAY(0, 1000000, 10000))
AS SELECT * FROM dataset.events;

-- 3. Table snapshot (Time Travel)
CREATE SNAPSHOT TABLE dataset.sales_snapshot
CLONE dataset.sales
FOR SYSTEM_TIME AS OF TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 DAY);

-- 4. Materialized Views
CREATE MATERIALIZED VIEW dataset.daily_sales_mv AS
SELECT
    DATE(sale_date) as date,
    SUM(amount) as total_amount,
    COUNT(*) as count
FROM dataset.sales
GROUP BY DATE(sale_date);

-- 5. BI Engine (in-memory acceleration)
ALTER TABLE dataset.sales
SET OPTIONS (
    max_staleness = INTERVAL 1 HOUR
);

-- 6. Wildcard tables
SELECT *
FROM `project.dataset.sales_*`
WHERE _TABLE_SUFFIX BETWEEN '20240101' AND '20240131';
```

#### 2.2 Google Cloud Dataflow (Apache Beam)

```python
import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions
from apache_beam.io.gcp.bigquery import WriteToBigQuery

# Pipeline Options
options = PipelineOptions(
    project='my-project',
    runner='DataflowRunner',
    temp_location='gs://bucket/temp',
    region='us-central1',
    num_workers=10,
    max_num_workers=20,
    autoscaling_algorithm='THROUGHPUT_BASED'
)

# Pipeline
with beam.Pipeline(options=options) as pipeline:
    (
        pipeline
        | 'Read from GCS' >> beam.io.ReadFromText('gs://bucket/input/*.csv')
        | 'Parse CSV' >> beam.Map(lambda line: line.split(','))
        | 'Filter Valid' >> beam.Filter(lambda row: len(row) == 3 and float(row[2]) > 0)
        | 'Transform' >> beam.Map(lambda row: {
            'customer_id': int(row[0]),
            'product_id': int(row[1]),
            'amount': float(row[2])
        })
        | 'Aggregate' >> beam.CombinePerKey(sum)
        | 'Write to BigQuery' >> WriteToBigQuery(
            'project:dataset.aggregated_sales',
            schema='customer_id:INTEGER,total_amount:FLOAT',
            write_disposition=beam.io.BigQueryDisposition.WRITE_TRUNCATE
        )
    )
```

---

### 3. Azure Data Services

#### 3.1 Azure Data Factory (ADF)

```json
{
  "name": "CopyPipeline",
  "properties": {
    "activities": [
      {
        "name": "CopyFromBlobToSQL",
        "type": "Copy",
        "inputs": [
          {
            "referenceName": "BlobDataset",
            "type": "DatasetReference"
          }
        ],
        "outputs": [
          {
            "referenceName": "SQLDataset",
            "type": "DatasetReference"
          }
        ],
        "typeProperties": {
          "source": {
            "type": "BlobSource"
          },
          "sink": {
            "type": "SqlSink",
            "writeBatchSize": 10000,
            "writeBatchTimeout": "00:05:00",
            "preCopyScript": "TRUNCATE TABLE dbo.sales"
          }
        }
      }
    ]
  }
}
```

#### 3.2 Azure Synapse Analytics

```sql
-- Create external table (PolyBase)
CREATE EXTERNAL DATA SOURCE AzureStorage
WITH (
    TYPE = HADOOP,
    LOCATION = 'wasbs://container@account.blob.core.windows.net/',
    CREDENTIAL = AzureStorageCredential
);

CREATE EXTERNAL FILE FORMAT ParquetFormat
WITH (
    FORMAT_TYPE = PARQUET,
    DATA_COMPRESSION = 'org.apache.hadoop.io.compress.SnappyCodec'
);

CREATE EXTERNAL TABLE ext_sales (
    sale_id BIGINT,
    customer_id BIGINT,
    amount DECIMAL(10,2)
)
WITH (
    LOCATION = '/sales/',
    DATA_SOURCE = AzureStorage,
    FILE_FORMAT = ParquetFormat
);

-- CTAS para otimizar
CREATE TABLE sales
WITH (
    DISTRIBUTION = HASH(customer_id),
    CLUSTERED COLUMNSTORE INDEX
)
AS SELECT * FROM ext_sales;
```

---

### 4. Infrastructure as Code (Terraform)

```hcl
# terraform/main.tf

# AWS S3 Bucket
resource "aws_s3_bucket" "data_lake" {
  bucket = "my-data-lake-${var.environment}"

  tags = {
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

resource "aws_s3_bucket_versioning" "data_lake" {
  bucket = aws_s3_bucket.data_lake.id

  versioning_configuration {
    status = "Enabled"
  }
}

# AWS Glue Database
resource "aws_glue_catalog_database" "main" {
  name = "analytics_db"
}

# AWS Glue Crawler
resource "aws_glue_crawler" "sales" {
  name          = "sales_crawler"
  role          = aws_iam_role.glue_role.arn
  database_name = aws_glue_catalog_database.main.name

  s3_target {
    path = "s3://${aws_s3_bucket.data_lake.bucket}/raw/sales/"
  }

  schedule = "cron(0 1 * * ? *)"
}

# Redshift Cluster
resource "aws_redshift_cluster" "warehouse" {
  cluster_identifier = "data-warehouse-${var.environment}"
  database_name      = "warehouse"
  master_username    = "admin"
  master_password    = var.redshift_password
  node_type          = "ra3.xlplus"
  number_of_nodes    = 2

  encrypted            = true
  publicly_accessible  = false
  skip_final_snapshot  = var.environment == "dev"

  tags = {
    Environment = var.environment
  }
}
```

---

## =» Exercícios Práticos

### Exercício 1: Arquitetura Multi-Cloud
Implemente pipeline que:
1. Ingere de AWS S3
2. Processa com GCP Dataflow
3. Carrega em Azure Synapse

=Á [exercicios/ex01-multi-cloud.py](./exercicios/ex01-multi-cloud.py)

### Exercício 2: Cost Optimization
Analise e otimize custos de:
1. S3 storage (lifecycle policies)
2. BigQuery queries (partitioning)
3. Redshift (compression, distribution)

=Á [exercicios/ex02-cost-optimization.md](./exercicios/ex02-cost-optimization.md)

### Exercício 3: Serverless Pipeline
Crie pipeline 100% serverless:
1. AWS Lambda triggers
2. Glue ETL
3. Athena queries
4. Step Functions orchestration

=Á [exercicios/ex03-serverless.py](./exercicios/ex03-serverless.py)

---

##  Checklist

- [ ] Configurar contas AWS, GCP, Azure
- [ ] Implementar pipeline em cada cloud
- [ ] Criar IaC com Terraform
- [ ] Otimizar custos
- [ ] Implementar segurança (IAM, encryption)
- [ ] Configurar monitoring

---

## = Próximos Passos

**Módulo 7:** Data Quality e Governança

[Ver Módulo 7](../07-data-quality-governanca/README.md)
