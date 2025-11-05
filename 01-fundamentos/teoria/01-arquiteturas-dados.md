# Arquiteturas de Sistemas de Dados

## 1. OLTP vs OLAP

### OLTP (Online Transaction Processing)

**Características:**
- **Foco**: Transações rápidas e frequentes
- **Operações**: INSERT, UPDATE, DELETE
- **Dados**: Atuais, operacionais
- **Normalização**: Alta (3NF ou superior)
- **Usuários**: Milhares simultâneos
- **Tamanho**: GB a TB
- **Performance**: Milissegundos

**Exemplos de uso:**
- Sistemas bancários
- E-commerce (carrinho, checkout)
- CRM (gestão de clientes)
- ERP (planejamento de recursos)

**Bancos OLTP populares:**
```
PostgreSQL, MySQL, Oracle, SQL Server, MongoDB
```

**Exemplo prático:**
```sql
-- Transação de pedido (OLTP)
BEGIN TRANSACTION;

-- 1. Criar pedido
INSERT INTO orders (user_id, total_amount, status, created_at)
VALUES (12345, 299.99, 'pending', NOW())
RETURNING order_id INTO @order_id;

-- 2. Adicionar itens
INSERT INTO order_items (order_id, product_id, quantity, price)
VALUES 
    (@order_id, 101, 2, 99.99),
    (@order_id, 205, 1, 100.01);

-- 3. Atualizar inventário
UPDATE inventory 
SET quantity = quantity - 2,
    last_updated = NOW()
WHERE product_id = 101;

UPDATE inventory 
SET quantity = quantity - 1,
    last_updated = NOW()
WHERE product_id = 205;

-- 4. Registrar pagamento
INSERT INTO payments (order_id, amount, payment_method, status)
VALUES (@order_id, 299.99, 'credit_card', 'pending');

COMMIT;

-- Características OLTP desta transação:
-- ✅ Múltiplas tabelas (normalizado)
-- ✅ ACID compliance (atomicidade)
-- ✅ Escrita intensiva
-- ✅ Resposta em < 100ms
-- ✅ Dados operacionais atuais
```

### OLAP (Online Analytical Processing)

**Características:**
- **Foco**: Análises complexas e reports
- **Operações**: SELECT com agregações
- **Dados**: Históricos, consolidados
- **Normalização**: Baixa (Star/Snowflake Schema)
- **Usuários**: Dezenas a centenas
- **Tamanho**: TB a PB
- **Performance**: Segundos a minutos

**Exemplos de uso:**
- Business Intelligence
- Data Analytics
- Relatórios gerenciais
- Dashboards executivos

**Bancos OLAP populares:**
```
Snowflake, Redshift, BigQuery, Synapse Analytics, ClickHouse
```

**Exemplo prático:**
```sql
-- Análise de vendas (OLAP)
WITH monthly_sales AS (
    SELECT
        DATE_TRUNC('month', order_date) as month,
        product_category,
        region,
        SUM(total_amount) as total_sales,
        COUNT(DISTINCT customer_id) as unique_customers,
        COUNT(*) as num_orders,
        AVG(total_amount) as avg_order_value
    FROM fact_sales f
    JOIN dim_product p ON f.product_id = p.product_id
    JOIN dim_location l ON f.location_id = l.location_id
    WHERE order_date >= '2023-01-01'
    GROUP BY 1, 2, 3
),
growth_calc AS (
    SELECT
        month,
        product_category,
        region,
        total_sales,
        LAG(total_sales) OVER (
            PARTITION BY product_category, region 
            ORDER BY month
        ) as prev_month_sales,
        (total_sales - LAG(total_sales) OVER (
            PARTITION BY product_category, region 
            ORDER BY month
        )) / NULLIF(LAG(total_sales) OVER (
            PARTITION BY product_category, region 
            ORDER BY month
        ), 0) * 100 as growth_pct
    FROM monthly_sales
)
SELECT
    month,
    product_category,
    region,
    total_sales,
    prev_month_sales,
    growth_pct,
    CASE
        WHEN growth_pct > 20 THEN '🚀 Alto Crescimento'
        WHEN growth_pct > 0 THEN '📈 Crescimento'
        WHEN growth_pct = 0 THEN '➡️ Estável'
        ELSE '📉 Declínio'
    END as trend
FROM growth_calc
WHERE month >= '2024-01-01'
ORDER BY month DESC, total_sales DESC;

-- Características OLAP desta query:
-- ✅ Leitura pesada (sem writes)
-- ✅ Agregações complexas (SUM, AVG, COUNT)
-- ✅ Window functions (LAG, PARTITION BY)
-- ✅ Múltiplos JOINs com fact/dimension tables
-- ✅ Análise de tendências temporais
-- ✅ Pode levar segundos para executar
-- ✅ Processa milhões/bilhões de linhas
```

**Comparação lado a lado:**

| Aspecto | OLTP | OLAP |
|---------|------|------|
| **Propósito** | Operações diárias | Análises e decisões |
| **Operações** | INSERT, UPDATE, DELETE | SELECT complexos |
| **Queries** | Simples, rápidas | Complexas, lentas |
| **Dados** | Atuais | Históricos |
| **Volume por query** | Poucos registros | Milhões de registros |
| **Normalização** | Alta (3NF) | Baixa (Star Schema) |
| **Índices** | Muitos (B-Tree) | Poucos (Columnar) |
| **Throughput** | Alto (1000s TPS) | Baixo (10s queries/sec) |
| **Latência** | < 100ms | Segundos a minutos |
| **Backup** | Frequente (hourly) | Menos frequente (daily) |
| **Exemplos** | PostgreSQL, MySQL | Snowflake, Redshift |

---

## 2. Data Warehouse

### Definição e Propósito

Um **Data Warehouse (DW)** é um repositório centralizado de dados integrados de múltiplas fontes, otimizado para análise e relatórios.

**Características principais:**
- **Subject-oriented**: Organizado por assunto (vendas, clientes, produtos)
- **Integrated**: Dados de múltiplas fontes consolidados
- **Non-volatile**: Dados históricos não são alterados
- **Time-variant**: Mantém histórico temporal

### Arquitetura Kimball (Bottom-up)

```
Sources → ETL → Data Marts → Business Intelligence
(OLTP)         (Star Schema)  (Reports, Dashboards)
```

**Componentes:**
1. **Staging Area**: Dados brutos temporários
2. **Data Marts**: Áreas departamentais (Vendas, Marketing, Finanças)
3. **Presentation Layer**: Star/Snowflake Schema
4. **BI Layer**: Tableau, PowerBI, Looker

**Vantagens:**
- ✅ Rápida implementação (bottom-up)
- ✅ ROI mais rápido
- ✅ Flexível para mudanças
- ✅ Fácil de entender (dimensional)

### Arquitetura Inmon (Top-down)

```
Sources → ETL → Enterprise DW → Data Marts → BI
(OLTP)         (3NF Normalized)  (Denormalized)
```

**Componentes:**
1. **Staging Area**: Dados brutos
2. **Enterprise Data Warehouse**: Dados normalizados (3NF)
3. **Data Marts**: Views desnormalizadas
4. **BI Layer**: Relatórios

**Vantagens:**
- ✅ Única fonte da verdade
- ✅ Consistência de dados
- ✅ Escalável para enterprise
- ✅ Menos redundância

**Desvantagens:**
- ❌ Implementação longa (anos)
- ❌ Custo inicial alto
- ❌ Complexidade maior

### Star Schema (Kimball)

```
       DIM_TEMPO
           |
DIM_CLIENTE - FACT_VENDAS - DIM_PRODUTO
           |
       DIM_LOJA
```

**Fact Table (Fatos):**
- Métricas numéricas (vendas, quantidade, lucro)
- Foreign keys para dimensões
- Granularidade (nível de detalhe)

```sql
CREATE TABLE fact_vendas (
    venda_id BIGINT PRIMARY KEY,
    data_id INT NOT NULL,          -- FK para dim_tempo
    cliente_id INT NOT NULL,        -- FK para dim_cliente
    produto_id INT NOT NULL,        -- FK para dim_produto
    loja_id INT NOT NULL,           -- FK para dim_loja
    
    -- Métricas
    quantidade INT,
    valor_unitario DECIMAL(10,2),
    valor_total DECIMAL(10,2),
    custo DECIMAL(10,2),
    lucro DECIMAL(10,2),
    desconto DECIMAL(10,2),
    
    FOREIGN KEY (data_id) REFERENCES dim_tempo(data_id),
    FOREIGN KEY (cliente_id) REFERENCES dim_cliente(cliente_id),
    FOREIGN KEY (produto_id) REFERENCES dim_produto(produto_id),
    FOREIGN KEY (loja_id) REFERENCES dim_loja(loja_id)
);
```

**Dimension Tables (Dimensões):**
- Contexto descritivo
- Atributos textuais
- Surrogate keys (SK) e Natural keys (NK)

```sql
CREATE TABLE dim_produto (
    produto_id INT PRIMARY KEY,           -- Surrogate Key
    produto_nk VARCHAR(50) NOT NULL,      -- Natural Key (SKU)
    nome VARCHAR(200),
    descricao TEXT,
    categoria VARCHAR(100),
    subcategoria VARCHAR(100),
    marca VARCHAR(100),
    preco_sugerido DECIMAL(10,2),
    
    -- Metadados (SCD Type 2)
    valido_de TIMESTAMP,
    valido_ate TIMESTAMP,
    eh_atual BOOLEAN DEFAULT TRUE,
    versao INT DEFAULT 1
);

CREATE TABLE dim_tempo (
    data_id INT PRIMARY KEY,              -- YYYYMMDD
    data DATE NOT NULL,
    ano INT,
    trimestre INT,
    mes INT,
    semana INT,
    dia INT,
    dia_semana INT,
    nome_dia_semana VARCHAR(20),
    nome_mes VARCHAR(20),
    eh_fim_de_semana BOOLEAN,
    eh_feriado BOOLEAN,
    nome_feriado VARCHAR(100)
);
```

### Slowly Changing Dimensions (SCD)

**Type 0: Retain Original**
- Nunca muda
- Ex: Data de nascimento

**Type 1: Overwrite**
```sql
-- Antes
UPDATE dim_cliente 
SET endereco = 'Rua Nova, 123',
    cidade = 'São Paulo'
WHERE cliente_id = 1001;

-- Depois: Histórico perdido
```

**Type 2: Add New Row (mais comum)**
```sql
-- Desativar registro antigo
UPDATE dim_cliente 
SET valido_ate = CURRENT_TIMESTAMP,
    eh_atual = FALSE
WHERE cliente_id = 1001 AND eh_atual = TRUE;

-- Inserir novo registro
INSERT INTO dim_cliente (
    cliente_nk, nome, endereco, cidade,
    valido_de, valido_ate, eh_atual, versao
)
VALUES (
    'C1001', 'João Silva', 'Rua Nova, 123', 'São Paulo',
    CURRENT_TIMESTAMP, NULL, TRUE, 2
);

-- Resultado: Histórico completo mantido
-- Versão 1: Endereço antigo (2023-01-01 a 2024-01-15)
-- Versão 2: Endereço novo (2024-01-15 até presente)
```

**Type 3: Add New Column**
```sql
ALTER TABLE dim_cliente 
ADD COLUMN endereco_anterior VARCHAR(200),
ADD COLUMN data_mudanca_endereco TIMESTAMP;

UPDATE dim_cliente 
SET endereco_anterior = endereco,
    endereco = 'Rua Nova, 123',
    data_mudanca_endereco = CURRENT_TIMESTAMP
WHERE cliente_id = 1001;

-- Mantém apenas última mudança
```

---

## 3. Data Lake

### Conceito

**Data Lake** = Repositório centralizado de dados RAW em formato nativo (schema-on-read).

**Diferenças do DW:**
- **Schema**: Schema-on-read (aplicado na leitura) vs Schema-on-write
- **Dados**: Todos os tipos vs Apenas estruturados
- **Processamento**: ELT vs ETL
- **Usuários**: Data Scientists, Engineers vs Business Analysts

### Arquitetura em Camadas (Medallion)

```
┌─────────────────────────────────────────────────────────┐
│  BRONZE LAYER (Raw)                                     │
│  - Dados brutos, sem transformação                      │
│  - Formato original (JSON, CSV, Parquet)                │
│  - Append-only (imutável)                              │
│  - Particionado por data de ingestão                    │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│  SILVER LAYER (Refined)                                 │
│  - Dados limpos e validados                            │
│  - Schema enforced                                      │
│  - Deduplicação                                        │
│  - Tipo de dados corretos                              │
│  - Particionado por lógica de negócio                  │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│  GOLD LAYER (Curated)                                   │
│  - Dados agregados e prontos para consumo              │
│  - Features para ML                                     │
│  - Reports e dashboards                                 │
│  - Star schema (opcional)                              │
└─────────────────────────────────────────────────────────┘
```

### Exemplo prático com PySpark

**Bronze → Silver:**
```python
from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.types import *

spark = SparkSession.builder.appName("DataLake").getOrCreate()

# BRONZE: Ler dados brutos
bronze_df = spark.read \
    .format("json") \
    .option("multiline", "true") \
    .load("s3://datalake/bronze/events/")

bronze_df.write \
    .format("parquet") \
    .partitionBy("year", "month", "day") \
    .mode("append") \
    .save("s3://datalake/bronze/events_parquet/")

# SILVER: Limpar e validar
silver_df = bronze_df \
    .filter(col("user_id").isNotNull()) \
    .filter(col("timestamp").isNotNull()) \
    .withColumn("timestamp", to_timestamp(col("timestamp"))) \
    .withColumn("date", to_date(col("timestamp"))) \
    .dropDuplicates(["event_id"]) \
    .withColumn("processed_at", current_timestamp())

# Data quality checks
from pyspark.sql.functions import count, countDistinct

quality_metrics = silver_df.agg(
    count("*").alias("total_records"),
    countDistinct("user_id").alias("unique_users"),
    countDistinct("event_id").alias("unique_events"),
    sum(when(col("user_id").isNull(), 1).otherwise(0)).alias("null_user_ids")
).collect()[0]

assert quality_metrics["null_user_ids"] == 0, "Null user_ids found!"

silver_df.write \
    .format("delta") \
    .partitionBy("date") \
    .mode("overwrite") \
    .save("s3://datalake/silver/events/")

# GOLD: Agregar para analytics
gold_df = silver_df \
    .groupBy("date", "user_id", "event_type") \
    .agg(
        count("*").alias("event_count"),
        countDistinct("session_id").alias("unique_sessions")
    )

gold_df.write \
    .format("delta") \
    .partitionBy("date") \
    .mode("overwrite") \
    .save("s3://datalake/gold/user_daily_events/")
```

### Data Lakehouse

**Conceito**: Combina melhores práticas de Data Lake + Data Warehouse

**Tecnologias:**
- **Delta Lake** (Databricks)
- **Apache Iceberg** (Netflix)
- **Apache Hudi** (Uber)

**Características:**
- ✅ ACID transactions
- ✅ Time travel
- ✅ Schema enforcement e evolution
- ✅ Performance de DW com flexibilidade de Data Lake
- ✅ Unified batch + streaming

**Exemplo Delta Lake:**
```python
from delta import *

# Escrever com Delta Lake
df.write \
    .format("delta") \
    .mode("overwrite") \
    .save("/data/delta/sales")

# Ler com time travel
df_yesterday = spark.read \
    .format("delta") \
    .option("versionAsOf", 1) \
    .load("/data/delta/sales")

df_last_week = spark.read \
    .format("delta") \
    .option("timestampAsOf", "2024-01-01") \
    .load("/data/delta/sales")

# MERGE (upsert)
from delta.tables import *

deltaTable = DeltaTable.forPath(spark, "/data/delta/sales")

deltaTable.alias("target").merge(
    source_df.alias("source"),
    "target.sale_id = source.sale_id"
).whenMatchedUpdate(set = {
    "quantity": "source.quantity",
    "updated_at": "current_timestamp()"
}).whenNotMatchedInsert(values = {
    "sale_id": "source.sale_id",
    "quantity": "source.quantity",
    "created_at": "current_timestamp()"
}).execute()

# Vacuum (limpar versões antigas)
deltaTable.vacuum(retentionHours=168)  # 7 dias
```

---

## Resumo Comparativo

| Aspecto | OLTP | Data Warehouse | Data Lake | Data Lakehouse |
|---------|------|----------------|-----------|----------------|
| **Dados** | Atuais | Históricos | Raw | Raw + Curados |
| **Schema** | Definido | Definido | Flexível | Flexível + Enforced |
| **Formato** | Tabelas | Star/Snow | Arquivos | Delta/Iceberg |
| **Usuários** | Apps | Analistas | Cientistas | Todos |
| **Custo** | $$$ | $$$$ | $ | $$ |
| **Performance** | Alta | Alta | Média | Alta |
| **Flexibilidade** | Baixa | Baixa | Alta | Alta |
| **ACID** | ✅ | ✅ | ❌ | ✅ |
| **Exemplos** | PostgreSQL | Snowflake | S3 | Delta Lake |

---

**Próximo**: [02-sql-avancado.md](./02-sql-avancado.md)
