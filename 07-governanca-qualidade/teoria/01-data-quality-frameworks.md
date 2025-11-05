# ✅ Data Quality e Governança

## 📋 Índice

1. [O que é Data Quality](#o-que-é-data-quality)
2. [Great Expectations](#great-expectations)
3. [Data Lineage](#data-lineage)
4. [Data Catalogs](#data-catalogs)
5. [Data Security](#data-security)
6. [GDPR e Compliance](#gdpr-e-compliance)

---

## O que é Data Quality

### Dimensões de Qualidade

```
┌─────────────────────────────────────────────────┐
│          DIMENSÕES DE DATA QUALITY              │
├─────────────────────────────────────────────────┤
│                                                 │
│  ✅ Accuracy      - Dados corretos?            │
│  ✅ Completeness  - Sem valores missing?       │
│  ✅ Consistency   - Mesmos valores em sources? │
│  ✅ Timeliness    - Dados atualizados?         │
│  ✅ Validity      - Formato correto?           │
│  ✅ Uniqueness    - Sem duplicatas?            │
│                                                 │
└─────────────────────────────────────────────────┘
```

### Data Quality Pipeline

```python
from pyspark.sql import DataFrame
from pyspark.sql.functions import *

def validate_data_quality(df: DataFrame) -> dict:
    """
    Valida qualidade dos dados.
    Retorna métricas de qualidade.
    """
    total_rows = df.count()
    
    # 1. Completeness
    null_counts = {
        col: df.filter(col(col).isNull()).count()
        for col in df.columns
    }
    
    completeness = {
        col: 100 * (1 - count / total_rows)
        for col, count in null_counts.items()
    }
    
    # 2. Validity (email format)
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    invalid_emails = df.filter(
        ~col("email").rlike(email_regex)
    ).count()
    
    email_validity = 100 * (1 - invalid_emails / total_rows)
    
    # 3. Uniqueness (duplicates)
    unique_ids = df.select("customer_id").distinct().count()
    uniqueness = 100 * (unique_ids / total_rows)
    
    # 4. Timeliness (data freshness)
    max_date = df.agg(max("updated_at")).collect()[0][0]
    freshness_hours = (datetime.now() - max_date).total_seconds() / 3600
    
    return {
        'total_rows': total_rows,
        'completeness': completeness,
        'email_validity': email_validity,
        'uniqueness': uniqueness,
        'freshness_hours': freshness_hours
    }

# Usage
metrics = validate_data_quality(df)

# Alert if thresholds violated
if metrics['completeness']['email'] < 95:
    send_alert("Email completeness below 95%")

if metrics['freshness_hours'] > 24:
    send_alert("Data is more than 24 hours old")
```

---

## Great Expectations

**Great Expectations** = Framework Python para validação de dados.

### Instalação e Setup

```bash
pip install great_expectations

# Initialize
great_expectations init
```

### Expectations Básicas

```python
import great_expectations as gx
from great_expectations.dataset import PandasDataset
import pandas as pd

# Carregar dados
df = pd.read_csv("customers.csv")
ge_df = PandasDataset(df)

# Expectations
ge_df.expect_table_row_count_to_be_between(min_value=1000, max_value=1000000)
ge_df.expect_column_values_to_not_be_null("customer_id")
ge_df.expect_column_values_to_be_unique("customer_id")
ge_df.expect_column_values_to_be_in_set("country", ["BR", "US", "UK"])
ge_df.expect_column_values_to_match_regex("email", r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
ge_df.expect_column_values_to_be_between("age", min_value=18, max_value=120)
ge_df.expect_column_mean_to_be_between("order_total", min_value=10, max_value=1000)

# Validate
results = ge_df.validate()

if not results['success']:
    print(f"Validation failed: {results['statistics']['unsuccessful_expectations']} expectations failed")
    
    for result in results['results']:
        if not result['success']:
            print(f"  - {result['expectation_config']['expectation_type']}: {result.get('exception_info', {}).get('raised_exception', False)}")
```

### Expectation Suite

```python
# Criar Expectation Suite
context = gx.get_context()

# Data Source
datasource = context.sources.add_pandas("my_datasource")
data_asset = datasource.add_dataframe_asset(name="customers")

# Batch Request
batch_request = data_asset.build_batch_request(dataframe=df)

# Create Suite
suite = context.add_expectation_suite("customers_suite")

# Add Expectations
validator = context.get_validator(
    batch_request=batch_request,
    expectation_suite_name="customers_suite"
)

validator.expect_column_values_to_not_be_null("customer_id")
validator.expect_column_values_to_be_unique("customer_id")
validator.expect_column_values_to_be_between("age", min_value=0, max_value=150)

# Save Suite
validator.save_expectation_suite()

# Run Checkpoint
checkpoint = context.add_checkpoint(
    name="customers_checkpoint",
    validations=[{
        "batch_request": batch_request,
        "expectation_suite_name": "customers_suite"
    }]
)

results = checkpoint.run()
```

### Great Expectations com Spark

```python
from great_expectations.dataset import SparkDFDataset

# Spark DataFrame
spark_df = spark.read.parquet("s3://bucket/data.parquet")

# Convert to GE Dataset
ge_spark_df = SparkDFDataset(spark_df)

# Expectations
ge_spark_df.expect_column_values_to_not_be_null("order_id")
ge_spark_df.expect_column_distinct_values_to_be_in_set("status", ["pending", "completed", "cancelled"])
ge_spark_df.expect_column_pair_values_A_to_be_greater_than_B("total_amount", "discount_amount")

# Validate
results = ge_spark_df.validate()
```

### Data Docs (Reports)

```python
# Build Data Docs (HTML reports)
context.build_data_docs()

# Opens in browser
context.open_data_docs()
```

---

## Data Lineage

**Data Lineage** = Rastreamento da origem, transformações e destino dos dados.

### Por que Data Lineage?

- 🔍 **Debug**: Encontrar erros em pipelines
- 📊 **Impact Analysis**: Saber o que é afetado por mudanças
- 🔒 **Compliance**: GDPR, auditorias
- 📈 **Trust**: Saber de onde vêm os dados

### Tools de Lineage

**1. Apache Atlas**
```python
# Registrar entidade
atlas_client = AtlasClient(base_url='http://atlas:21000', username='admin', password='admin')

# Criar database
database_entity = {
    'typeName': 'hive_db',
    'attributes': {
        'name': 'raw_data',
        'qualifiedName': 'raw_data@cluster',
        'clusterName': 'prod_cluster'
    }
}

atlas_client.entity.create(database_entity)
```

**2. OpenLineage (padrão aberto)**
```python
from openlineage.client import OpenLineageClient
from openlineage.run import RunEvent, RunState, Run, Job

client = OpenLineageClient(url="http://marquez:5000")

# Emit lineage event
event = RunEvent(
    eventType=RunState.START,
    eventTime="2024-01-15T10:30:00Z",
    run=Run(runId="run-123", facets={}),
    job=Job(namespace="prod", name="etl_pipeline", facets={}),
    inputs=[{
        "namespace": "s3",
        "name": "raw-data",
        "facets": {}
    }],
    outputs=[{
        "namespace": "s3",
        "name": "processed-data",
        "facets": {}
    }]
)

client.emit(event)
```

**3. Spark com Lineage**
```python
# Spark Listener para capturar lineage
from pyspark.sql import SparkSession

spark = SparkSession.builder \
    .appName("LineageTracking") \
    .config("spark.extraListeners", "io.openlineage.spark.agent.OpenLineageSparkListener") \
    .config("spark.openlineage.transport.url", "http://marquez:5000") \
    .getOrCreate()

# Transformações são rastreadas automaticamente
df = spark.read.parquet("s3://input/")
df_transformed = df.filter(col("status") == "active")
df_transformed.write.parquet("s3://output/")

# Lineage capturado:
# s3://input/ → filter → s3://output/
```

### Lineage Manual

```python
class DataLineageTracker:
    def __init__(self):
        self.lineage = []
    
    def track(self, job_name, inputs, outputs, transformation):
        entry = {
            'timestamp': datetime.now().isoformat(),
            'job': job_name,
            'inputs': inputs,
            'outputs': outputs,
            'transformation': transformation
        }
        self.lineage.append(entry)
        self.save_to_catalog(entry)
    
    def save_to_catalog(self, entry):
        # Save to data catalog (Glue, Atlas, etc)
        pass

# Usage
tracker = DataLineageTracker()

# Track transformation
tracker.track(
    job_name='daily_etl',
    inputs=['s3://raw/orders/', 's3://raw/customers/'],
    outputs=['s3://processed/sales_summary/'],
    transformation='join + group by + aggregate'
)
```

---

## Data Catalogs

**Data Catalog** = Metadata repository (esquemas, owners, lineage, qualidade).

### AWS Glue Data Catalog

```python
import boto3

glue = boto3.client('glue')

# Get table metadata
table = glue.get_table(
    DatabaseName='analytics',
    Name='customers'
)

print(f"Table: {table['Table']['Name']}")
print(f"Location: {table['Table']['StorageDescriptor']['Location']}")
print(f"Columns: {table['Table']['StorageDescriptor']['Columns']}")

# Update table description
glue.update_table(
    DatabaseName='analytics',
    TableInput={
        'Name': 'customers',
        'Description': 'Customer master data with PII',
        'Owner': 'data-team',
        'Parameters': {
            'classification': 'pii',
            'data_owner': 'john@company.com',
            'update_frequency': 'daily'
        },
        'StorageDescriptor': table['Table']['StorageDescriptor']
    }
)

# Tag table
glue.tag_resource(
    ResourceArn=table['Table']['Arn'],
    TagsToAdd={
        'Environment': 'production',
        'Team': 'data-engineering',
        'Contains-PII': 'true'
    }
)
```

### Apache Atlas

```python
from pyatlasclient.client import AtlasClient

atlas = AtlasClient(host='atlas.company.com', port=21000)

# Search entities
search_results = atlas.search_basic.create(
    query="customers",
    typeName="hive_table"
)

for entity in search_results:
    print(f"Table: {entity['attributes']['name']}")
    print(f"Owner: {entity['attributes'].get('owner', 'unknown')}")
```

### Amundsen (Lyft's Data Discovery)

```python
# Metadata model
{
    "table": {
        "database": "analytics",
        "cluster": "prod",
        "schema": "public",
        "name": "customers",
        "description": "Customer master data",
        "columns": [
            {
                "name": "customer_id",
                "description": "Unique identifier",
                "type": "bigint",
                "badges": ["primary-key"]
            },
            {
                "name": "email",
                "description": "Customer email",
                "type": "varchar",
                "badges": ["pii"]
            }
        ],
        "tags": ["pii", "customer-data"],
        "owners": ["data-team@company.com"],
        "frequent_users": ["analyst1", "analyst2"]
    }
}
```

---

## Data Security

### Encryption

```python
# 1. At Rest (S3)
import boto3

s3 = boto3.client('s3')

# Default encryption
s3.put_bucket_encryption(
    Bucket='my-bucket',
    ServerSideEncryptionConfiguration={
        'Rules': [{
            'ApplyServerSideEncryptionByDefault': {
                'SSEAlgorithm': 'aws:kms',
                'KMSMasterKeyID': 'arn:aws:kms:us-east-1:123:key/abc'
            }
        }]
    }
)

# 2. At Rest (Spark)
spark = SparkSession.builder \
    .config("spark.io.encryption.enabled", "true") \
    .config("spark.io.encryption.keySizeBits", "256") \
    .getOrCreate()

# 3. In Transit (TLS)
spark = SparkSession.builder \
    .config("spark.ssl.enabled", "true") \
    .config("spark.ssl.keyStore", "/path/to/keystore") \
    .config("spark.ssl.keyStorePassword", "password") \
    .getOrCreate()
```

### Data Masking (PII)

```python
from pyspark.sql.functions import sha2, regexp_replace

# Hash PII
df_masked = df.withColumn(
    "email_hash",
    sha2(col("email"), 256)
)

# Mask credit card
df_masked = df.withColumn(
    "credit_card_masked",
    regexp_replace(col("credit_card"), r"(\d{12})(\d{4})", "************$2")
)

# Mask phone
df_masked = df.withColumn(
    "phone_masked",
    regexp_replace(col("phone"), r"(\d{6})(\d{4})", "******$2")
)

# Tokenization
import hashlib

def tokenize_pii(value, salt="secret"):
    return hashlib.sha256((value + salt).encode()).hexdigest()

tokenize_udf = udf(tokenize_pii, StringType())
df_tokenized = df.withColumn("ssn_token", tokenize_udf(col("ssn")))
```

### Access Control

```python
# Row-Level Security (RLS) example
def apply_rls(df, user_role, user_id):
    """Apply row-level security based on user role."""
    if user_role == 'admin':
        return df  # Full access
    elif user_role == 'manager':
        # Only see their team's data
        return df.filter(col("team_id") == user_id)
    elif user_role == 'analyst':
        # Only aggregated data, no PII
        return df.select("date", "revenue", "order_count") \
            .groupBy("date").sum()
    else:
        return spark.createDataFrame([], df.schema)  # No access

# Column-Level Security
def mask_columns_by_role(df, user_role):
    """Mask sensitive columns based on role."""
    if user_role in ['admin', 'compliance']:
        return df  # See everything
    else:
        # Mask PII for other roles
        return df.drop("ssn", "credit_card", "email")
```

---

## GDPR e Compliance

### GDPR Requirements

**1. Right to Access**
```python
def get_user_data(user_id):
    """Retornar TODOS os dados do usuário."""
    tables = [
        'customers', 'orders', 'payments',
        'browsing_history', 'preferences'
    ]
    
    user_data = {}
    for table in tables:
        df = spark.table(f"analytics.{table}")
        user_data[table] = df.filter(col("user_id") == user_id).toPandas()
    
    return user_data

# Export to JSON
user_data = get_user_data(12345)
with open('user_data_12345.json', 'w') as f:
    json.dump(user_data, f, default=str)
```

**2. Right to Erasure (Right to be Forgotten)**
```python
def delete_user_data(user_id):
    """Deletar TODOS os dados do usuário (GDPR)."""
    tables = [
        'customers', 'orders', 'payments',
        'browsing_history', 'preferences', 'logs'
    ]
    
    for table in tables:
        # Soft delete (recomendado para auditoria)
        spark.sql(f"""
            UPDATE {table}
            SET deleted_at = current_timestamp(),
                gdpr_deleted = true,
                email = 'deleted@gdpr.com',
                name = 'DELETED',
                phone = NULL,
                address = NULL
            WHERE user_id = {user_id}
        """)
        
        # ou Hard delete
        # spark.sql(f"DELETE FROM {table} WHERE user_id = {user_id}")
    
    # Log deletion for audit
    audit_log = spark.createDataFrame([{
        'user_id': user_id,
        'action': 'gdpr_deletion',
        'timestamp': datetime.now(),
        'initiated_by': 'user_request'
    }])
    audit_log.write.mode("append").saveAsTable("audit.gdpr_deletions")
```

**3. Data Retention Policies**
```python
# Airflow DAG for automatic deletion
from airflow import DAG
from airflow.operators.python import PythonOperator

def delete_old_data():
    """Delete data older than retention period."""
    retention_policies = {
        'browsing_history': 90,    # days
        'logs': 365,
        'transactions': 2555       # 7 years (legal requirement)
    }
    
    for table, days in retention_policies.items():
        cutoff_date = datetime.now() - timedelta(days=days)
        
        spark.sql(f"""
            DELETE FROM {table}
            WHERE created_at < '{cutoff_date}'
        """)

dag = DAG(
    'data_retention',
    schedule_interval='@daily',
    start_date=datetime(2024, 1, 1)
)

delete_task = PythonOperator(
    task_id='delete_old_data',
    python_callable=delete_old_data,
    dag=dag
)
```

**4. Consent Management**
```python
# Schema
CREATE TABLE user_consents (
    user_id BIGINT,
    consent_type VARCHAR(50),  -- marketing, analytics, personalization
    consented BOOLEAN,
    consent_date TIMESTAMP,
    withdrawn_date TIMESTAMP,
    ip_address VARCHAR(45),
    user_agent TEXT
);

# Filter data based on consent
def apply_consent_filter(df, processing_type):
    """Only process data for users who consented."""
    consents = spark.table("user_consents") \
        .filter(
            (col("consent_type") == processing_type) &
            (col("consented") == True) &
            (col("withdrawn_date").isNull())
        ) \
        .select("user_id")
    
    return df.join(consents, "user_id", "inner")

# Usage
analytics_df = spark.table("events")
analytics_df = apply_consent_filter(analytics_df, "analytics")
```

---

## 🎯 Checklist de Governança

- ✅ **Data Quality:**
  - Validações automatizadas (Great Expectations)
  - Alertas para violações de qualidade
  - Métricas de qualidade publicadas

- ✅ **Data Lineage:**
  - Rastreamento de origem → transformações → destino
  - Impact analysis para mudanças
  - Documentação de transformações

- ✅ **Data Catalog:**
  - Metadata centralizado
  - Schema documentation
  - Data owners identificados
  - Tags e classificações (PII, confidencial, etc)

- ✅ **Security:**
  - Encryption at rest e in transit
  - Data masking para PII
  - Access control (RBAC)
  - Audit logs

- ✅ **Compliance:**
  - GDPR compliance (access, erasure, portability)
  - Data retention policies
  - Consent management
  - Regular audits

---

**Próximo:** [02-data-governance-tools.md](./02-data-governance-tools.md)
