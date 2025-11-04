# =Ä Módulo 2: Modelagem e Armazenamento de Dados

## =Ë Visão Geral

Este módulo cobre técnicas avançadas de modelagem de dados, desde modelagem dimensional clássica até arquiteturas modernas de Data Lakes e Lakehouses.

**Duração:** 4-5 semanas | **Nível:** Intermediário

---

## <¯ Objetivos de Aprendizado

-  Dominar modelagem dimensional (Star Schema, Snowflake)
-  Implementar Data Vault 2.0
-  Projetar Data Warehouses escaláveis
-  Arquitetar Data Lakes e Lakehouses
-  Escolher formatos de arquivo otimizados
-  Implementar estratégias de particionamento

---

## =Ú Conteúdo

### 1. Modelagem Dimensional

#### 1.1 Star Schema

**Conceito:** Modelo desnormalizado com tabela fato central e dimensões.

```sql
-- TABELA FATO: Eventos/Transações (muitas linhas, narrow)
CREATE TABLE fact_sales (
    sale_id BIGINT PRIMARY KEY,
    date_key INT NOT NULL,
    product_key INT NOT NULL,
    customer_key INT NOT NULL,
    store_key INT NOT NULL,
    quantity INT,
    unit_price DECIMAL(10,2),
    total_amount DECIMAL(12,2),
    discount_amount DECIMAL(10,2),
    tax_amount DECIMAL(10,2),
    FOREIGN KEY (date_key) REFERENCES dim_date(date_key),
    FOREIGN KEY (product_key) REFERENCES dim_product(product_key),
    FOREIGN KEY (customer_key) REFERENCES dim_customer(customer_key),
    FOREIGN KEY (store_key) REFERENCES dim_store(store_key)
);

-- DIMENSÕES: Contexto (poucas linhas, wide)
CREATE TABLE dim_product (
    product_key INT PRIMARY KEY,
    product_id VARCHAR(50),  -- Business key
    product_name VARCHAR(200),
    category VARCHAR(100),
    subcategory VARCHAR(100),
    brand VARCHAR(100),
    unit_cost DECIMAL(10,2),
    supplier_name VARCHAR(200)
);

CREATE TABLE dim_customer (
    customer_key INT PRIMARY KEY,
    customer_id VARCHAR(50),
    customer_name VARCHAR(200),
    email VARCHAR(200),
    customer_tier VARCHAR(20),
    country VARCHAR(50),
    city VARCHAR(100),
    signup_date DATE
);

CREATE TABLE dim_date (
    date_key INT PRIMARY KEY,
    full_date DATE,
    day_of_week VARCHAR(10),
    day_of_month INT,
    day_of_year INT,
    week_of_year INT,
    month_number INT,
    month_name VARCHAR(10),
    quarter INT,
    year INT,
    is_weekend BOOLEAN,
    is_holiday BOOLEAN
);

CREATE TABLE dim_store (
    store_key INT PRIMARY KEY,
    store_id VARCHAR(50),
    store_name VARCHAR(200),
    store_type VARCHAR(50),
    country VARCHAR(50),
    state VARCHAR(50),
    city VARCHAR(100),
    manager_name VARCHAR(200)
);
```

**Vantagens:**
- Queries simples e rápidas
- Fácil de entender para analistas
- Ótima performance para BI tools

**Desvantagens:**
- Redundância de dados nas dimensões
- Dificuldade com mudanças de hierarquias

#### 1.2 Snowflake Schema

**Conceito:** Normaliza as dimensões em sub-dimensões.

```sql
-- Dimensão normalizada
CREATE TABLE dim_product (
    product_key INT PRIMARY KEY,
    product_id VARCHAR(50),
    product_name VARCHAR(200),
    category_key INT,  -- FK para dim_category
    brand_key INT,     -- FK para dim_brand
    supplier_key INT   -- FK para dim_supplier
);

CREATE TABLE dim_category (
    category_key INT PRIMARY KEY,
    category_name VARCHAR(100),
    subcategory VARCHAR(100),
    department VARCHAR(100)
);

CREATE TABLE dim_brand (
    brand_key INT PRIMARY KEY,
    brand_name VARCHAR(100),
    brand_country VARCHAR(50)
);
```

**Quando usar:**
- Dimensões muito grandes
- Necessidade de reduzir duplicação
- Hierarquias complexas

#### 1.3 Slowly Changing Dimensions (SCD)

**Tipo 1: Sobrescrever**
```sql
-- Simplesmente atualiza o registro
UPDATE dim_customer
SET customer_tier = 'gold', city = 'New York'
WHERE customer_key = 123;
```

**Tipo 2: Adicionar nova linha (MAIS COMUM)**
```sql
-- Mantém histórico com versões
CREATE TABLE dim_customer_scd2 (
    customer_key INT PRIMARY KEY,
    customer_id VARCHAR(50),
    customer_name VARCHAR(200),
    customer_tier VARCHAR(20),
    city VARCHAR(100),
    effective_date DATE,
    expiration_date DATE,
    is_current BOOLEAN,
    version INT
);

-- Inserir nova versão
INSERT INTO dim_customer_scd2
SELECT
    NEXTVAL('customer_key_seq'),
    customer_id,
    customer_name,
    'gold' as customer_tier,  -- Novo valor
    'New York' as city,
    CURRENT_DATE as effective_date,
    '9999-12-31' as expiration_date,
    TRUE as is_current,
    version + 1
FROM dim_customer_scd2
WHERE customer_id = 'C123' AND is_current = TRUE;

-- Expirar versão antiga
UPDATE dim_customer_scd2
SET expiration_date = CURRENT_DATE - 1,
    is_current = FALSE
WHERE customer_id = 'C123' AND version = (
    SELECT MAX(version) - 1 FROM dim_customer_scd2 WHERE customer_id = 'C123'
);
```

**Tipo 3: Adicionar coluna**
```sql
-- Mantém valor anterior em coluna separada
ALTER TABLE dim_customer
ADD COLUMN previous_tier VARCHAR(20),
ADD COLUMN tier_change_date DATE;
```

---

### 2. Data Vault 2.0

**Conceito:** Metodologia de modelagem para Enterprise DW, focada em auditoria e rastreabilidade.

#### Componentes:

**1. Hubs (Entidades de negócio)**
```sql
CREATE TABLE hub_customer (
    hub_customer_key CHAR(32) PRIMARY KEY,  -- Hash MD5
    customer_id VARCHAR(50) UNIQUE,  -- Business key
    load_date TIMESTAMP,
    record_source VARCHAR(100)
);

CREATE TABLE hub_product (
    hub_product_key CHAR(32) PRIMARY KEY,
    product_id VARCHAR(50) UNIQUE,
    load_date TIMESTAMP,
    record_source VARCHAR(100)
);
```

**2. Links (Relacionamentos)**
```sql
CREATE TABLE link_order (
    link_order_key CHAR(32) PRIMARY KEY,  -- Hash de todas as chaves
    hub_customer_key CHAR(32),
    hub_product_key CHAR(32),
    hub_store_key CHAR(32),
    order_id VARCHAR(50),
    load_date TIMESTAMP,
    record_source VARCHAR(100),
    FOREIGN KEY (hub_customer_key) REFERENCES hub_customer(hub_customer_key),
    FOREIGN KEY (hub_product_key) REFERENCES hub_product(hub_product_key)
);
```

**3. Satellites (Atributos e contexto)**
```sql
CREATE TABLE sat_customer (
    hub_customer_key CHAR(32),
    load_date TIMESTAMP,
    customer_name VARCHAR(200),
    email VARCHAR(200),
    customer_tier VARCHAR(20),
    city VARCHAR(100),
    hash_diff CHAR(32),  -- Hash dos atributos para detectar mudanças
    record_source VARCHAR(100),
    PRIMARY KEY (hub_customer_key, load_date),
    FOREIGN KEY (hub_customer_key) REFERENCES hub_customer(hub_customer_key)
);

CREATE TABLE sat_order (
    link_order_key CHAR(32),
    load_date TIMESTAMP,
    order_date DATE,
    quantity INT,
    unit_price DECIMAL(10,2),
    total_amount DECIMAL(12,2),
    hash_diff CHAR(32),
    record_source VARCHAR(100),
    PRIMARY KEY (link_order_key, load_date)
);
```

**Vantagens do Data Vault:**
- Auditável: Rastreia origem de cada dado
- Escalável: Fácil adicionar novas fontes
- Histórico completo: Todas as mudanças preservadas
- Paralelizável: Cargas independentes

**Desvantagens:**
- Complexidade: Muitas tabelas
- Performance: Queries podem ser complexas
- Requer camada de apresentação (marts)

---

### 3. Data Warehouses Modernos

#### 3.1 Snowflake

```sql
-- Criar database e schema
CREATE DATABASE analytics_dw;
CREATE SCHEMA sales_mart;

-- Criar tabela com clustering
CREATE TABLE sales_mart.fact_sales (
    sale_id BIGINT,
    sale_date DATE,
    product_id INT,
    customer_id INT,
    amount DECIMAL(10,2)
)
CLUSTER BY (sale_date, customer_id);

-- Time Travel (acesso a dados históricos)
SELECT * FROM fact_sales
AT (TIMESTAMP => '2024-01-01 00:00:00');

SELECT * FROM fact_sales
BEFORE (STATEMENT => '01a4c8f5-0000-0000-0000-000000000000');

-- Zero-copy cloning
CREATE TABLE fact_sales_dev CLONE fact_sales;

-- Materialized views
CREATE MATERIALIZED VIEW mv_daily_sales AS
SELECT
    sale_date,
    product_id,
    SUM(amount) as total_amount,
    COUNT(*) as transaction_count
FROM fact_sales
GROUP BY sale_date, product_id;
```

#### 3.2 BigQuery (Google Cloud)

```sql
-- Tabelas particionadas por data
CREATE TABLE `project.dataset.sales`
PARTITION BY DATE(sale_date)
CLUSTER BY customer_id, product_id
AS SELECT * FROM source_table;

-- Particionamento por range de inteiros
CREATE TABLE `project.dataset.events`
PARTITION BY RANGE_BUCKET(user_id, GENERATE_ARRAY(0, 100000, 1000))
AS SELECT * FROM source_events;

-- Tabelas externas (query direto no GCS)
CREATE EXTERNAL TABLE `project.dataset.external_sales`
OPTIONS (
  format = 'PARQUET',
  uris = ['gs://bucket/path/*.parquet']
);

-- BI Engine para cache
ALTER TABLE `project.dataset.sales`
SET OPTIONS (
  max_staleness = INTERVAL 1 HOUR
);
```

#### 3.3 Redshift (AWS)

```sql
-- Distribution styles
CREATE TABLE fact_sales (
    sale_id BIGINT,
    customer_id INT,
    product_id INT,
    amount DECIMAL(10,2)
)
DISTKEY(customer_id)  -- Co-locate por customer_id
SORTKEY(sale_date);   -- Ordenar por data

-- Distribution styles:
-- KEY: Distribui por hash de uma coluna
-- ALL: Cópia completa em cada nó (dimensões pequenas)
-- EVEN: Round-robin (padrão)

-- Sort keys
-- Compound: Ordem importa (WHERE date AND customer)
-- Interleaved: Ordem não importa (filtros variados)

CREATE TABLE dim_customer (
    customer_id INT,
    customer_name VARCHAR(200),
    country VARCHAR(50)
)
DISTSTYLE ALL  -- Tabela pequena, replicar em todos os nós
SORTKEY(customer_id);

-- Vacuum e Analyze
VACUUM FULL fact_sales;
ANALYZE fact_sales;
```

---

### 4. Data Lakes e Lakehouses

#### 4.1 Arquitetura de Data Lake

**Camadas:**
```
Raw/Bronze Layer:
  - Dados brutos, imutáveis
  - Formato original
  - Particionado por data de ingestão

Processed/Silver Layer:
  - Dados limpos e validados
  - Formato otimizado (Parquet)
  - Particionado por business keys

Curated/Gold Layer:
  - Dados agregados
  - Modelagem dimensional
  - Otimizado para consumo
```

**Estrutura de diretórios:**
```
s3://data-lake/
   raw/
      source=salesforce/
         table=accounts/
            year=2024/
               month=01/
                  day=01/
                     data.json.gz
      source=postgresql/
          table=orders/
              snapshot=2024-01-01/
                  data.parquet
   processed/
      domain=sales/
         entity=customers/
            year=2024/month=01/
               part-00000.parquet
   curated/
       mart=sales/
           fact_sales/
              year=2024/quarter=Q1/
                 data.parquet
           dim_customer/
               snapshot=2024-01-01/
                   data.parquet
```

#### 4.2 Delta Lake

**Conceito:** Adiciona ACID transactions e time travel ao Data Lake

```python
from pyspark.sql import SparkSession
from delta import *

# Configurar Spark com Delta
spark = SparkSession.builder \
    .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
    .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog") \
    .getOrCreate()

# Escrever Delta table
df = spark.read.parquet("s3://bucket/raw/sales/")
df.write.format("delta") \
    .mode("overwrite") \
    .partitionBy("year", "month") \
    .save("s3://bucket/delta/sales/")

# ACID updates
from delta.tables import DeltaTable

delta_table = DeltaTable.forPath(spark, "s3://bucket/delta/sales/")

# UPSERT (merge)
delta_table.alias("target") \
    .merge(
        updates.alias("source"),
        "target.sale_id = source.sale_id"
    ) \
    .whenMatchedUpdate(set={
        "amount": "source.amount",
        "updated_at": "current_timestamp()"
    }) \
    .whenNotMatchedInsert(values={
        "sale_id": "source.sale_id",
        "amount": "source.amount",
        "created_at": "current_timestamp()"
    }) \
    .execute()

# DELETE
delta_table.delete("sale_date < '2023-01-01'")

# Time Travel
df_v1 = spark.read.format("delta") \
    .option("versionAsOf", 0) \
    .load("s3://bucket/delta/sales/")

df_yesterday = spark.read.format("delta") \
    .option("timestampAsOf", "2024-01-01") \
    .load("s3://bucket/delta/sales/")

# Ver histórico
delta_table.history().show()

# Optimize (compaction)
delta_table.optimize().executeCompaction()

# Z-ordering (multi-dimensional clustering)
delta_table.optimize().executeZOrderBy("customer_id", "product_id")

# Vacuum (limpar old files)
delta_table.vacuum(168)  # 7 dias
```

#### 4.3 Apache Iceberg

```python
from pyspark.sql import SparkSession

spark = SparkSession.builder \
    .config("spark.sql.catalog.my_catalog", "org.apache.iceberg.spark.SparkCatalog") \
    .config("spark.sql.catalog.my_catalog.type", "hive") \
    .getOrCreate()

# Criar tabela Iceberg
spark.sql("""
    CREATE TABLE my_catalog.db.sales (
        sale_id BIGINT,
        customer_id INT,
        sale_date DATE,
        amount DECIMAL(10,2)
    )
    USING iceberg
    PARTITIONED BY (days(sale_date))
""")

# Schema evolution
spark.sql("ALTER TABLE my_catalog.db.sales ADD COLUMN discount DECIMAL(10,2)")

# Time travel
spark.sql("""
    SELECT * FROM my_catalog.db.sales
    VERSION AS OF 'snapshot-id-here'
""")

# Hidden partitioning (não precisa especificar nas queries)
spark.sql("SELECT * FROM my_catalog.db.sales WHERE sale_date = '2024-01-01'")
# Automaticamente usa a partição!
```

---

### 5. Formatos de Arquivo

#### 5.1 Comparação

| Formato | Tipo | Compressão | Schema | Splittable | Uso |
|---------|------|------------|--------|------------|-----|
| CSV | Text | Sim | Não | Sim | Simples, legível |
| JSON | Text | Sim | Parcial | Não | APIs, semi-estruturado |
| Avro | Binário | Sim | Sim | Sim | Streaming, schema evolution |
| Parquet | Binário | Sim | Sim | Sim | Analytics, columnar |
| ORC | Binário | Sim | Sim | Sim | Hive, columnar |

#### 5.2 Parquet (RECOMENDADO para analytics)

**Vantagens:**
- Columnar: Lê apenas colunas necessárias
- Compressão eficiente: 5-10x menor que CSV
- Predicate pushdown: Filtra antes de ler
- Schema embutido
- Suporte a tipos complexos (arrays, structs, maps)

```python
import pandas as pd

# Ler Parquet
df = pd.read_parquet(
    's3://bucket/data.parquet',
    columns=['col1', 'col2'],  # Lê apenas colunas necessárias
    filters=[('year', '=', 2024), ('month', '=', 1)]  # Predicate pushdown
)

# Escrever Parquet
df.to_parquet(
    's3://bucket/output.parquet',
    engine='pyarrow',
    compression='snappy',  # snappy: rápido, gzip: menor, zstd: balanceado
    index=False,
    partition_cols=['year', 'month']
)

# PySpark
spark.read.parquet("s3://bucket/data.parquet") \
    .select("col1", "col2") \
    .filter("year = 2024") \
    .write.parquet("s3://bucket/output.parquet", mode="overwrite")
```

---

### 6. Estratégias de Particionamento

#### 6.1 Particionamento por Data (MAIS COMUM)

```python
# Spark
df.write.partitionBy("year", "month", "day") \
    .parquet("s3://bucket/data/")

# Estrutura resultante:
# s3://bucket/data/
#   year=2024/
#     month=01/
#       day=01/
#         part-00000.parquet
#       day=02/
#         part-00000.parquet

# Query otimizada
spark.read.parquet("s3://bucket/data/") \
    .filter("year = 2024 AND month = 1")  # Lê apenas partições necessárias
```

#### 6.2 Bucketing (Hashing)

```python
# Distribuir dados uniformemente
df.write.bucketBy(100, "customer_id") \
    .sortBy("sale_date") \
    .saveAsTable("sales_bucketed")

# Benefício: JOINs mais rápidos
sales.join(customers, "customer_id")  # Evita shuffle se ambas bucketed
```

#### 6.3 Hive Partitioning

```python
# Adiciona partições dinamicamente
spark.sql("""
    INSERT OVERWRITE TABLE sales
    PARTITION (year, month)
    SELECT *, YEAR(sale_date), MONTH(sale_date)
    FROM raw_sales
""")
```

---

## =» Exercícios Práticos

### Exercício 1: Modelar Star Schema para E-commerce
Crie modelo dimensional completo com:
- Fato de vendas
- Dimensões de produto, cliente, tempo, loja
- Implemente SCD Type 2 para clientes

=Á [exercicios/ex01-star-schema.sql](./exercicios/ex01-star-schema.sql)

### Exercício 2: Implementar Data Vault
Converta modelo relacional em Data Vault:
- Criar hubs, links e satellites
- Implementar carga incremental
- Query com JOINs complexos

=Á [exercicios/ex02-data-vault/](./exercicios/ex02-data-vault/)

### Exercício 3: Data Lake com Delta Lake
Construa pipeline de Data Lake:
- Bronze: ingestão raw
- Silver: limpeza e validação
- Gold: agregações e marts
- Implementar UPSERT e time travel

=Á [exercicios/ex03-delta-lake/](./exercicios/ex03-delta-lake/)

---

## <¯ Projeto Prático: Modern Data Warehouse

**Objetivo:** Construir um Data Warehouse completo end-to-end

**Requisitos:**
1. Modelagem dimensional (star schema)
2. ETL com Spark
3. SCD Type 2 para dimensões
4. Particionamento otimizado
5. Formato Parquet
6. Queries analíticas complexas

=Á [projeto/modern-data-warehouse/](./projeto/modern-data-warehouse/)

---

##  Checklist de Conclusão

- [ ] Modelar star schema completo
- [ ] Implementar SCD Type 2
- [ ] Trabalhar com Data Vault 2.0
- [ ] Criar Data Lake com 3 camadas
- [ ] Usar Delta Lake ou Iceberg
- [ ] Otimizar com Parquet e particionamento
- [ ] Completar projeto do DW

---

## = Próximos Passos

**Módulo 3:** Processamento de Dados em Larga Escala
- Apache Spark profundo
- Otimizações avançadas
- Distributed computing

[Ver Módulo 3](../03-processamento-larga-escala/README.md)
