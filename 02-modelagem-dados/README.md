# 🗄️ Módulo 2: Modelagem e Armazenamento de Dados

**Duração:** 4-5 semanas | **Nível:** Intermediário

## 📋 Visão Geral

Aprenda a modelar, armazenar e organizar dados para análises eficientes em grande escala.

## 🎯 Objetivos

- ✅ Modelagem dimensional (Star, Snowflake)
- ✅ Data Vault 2.0
- ✅ Data Warehouses modernos
- ✅ Data Lakes e Lakehouses
- ✅ Formatos de arquivo otimizados
- ✅ Particionamento e indexação

## 📚 Conteúdo

### 1. Modelagem Dimensional

**Star Schema:**
```
      DIM_PRODUTO
           |
DIM_DATA - FACT_VENDAS - DIM_CLIENTE
           |
      DIM_LOJA
```

- Fact Tables (métricas, FK's)
- Dimension Tables (contexto, SK's)
- Slowly Changing Dimensions (SCD Type 1, 2, 3)
- Surrogate Keys vs Natural Keys

**Snowflake Schema:**
- Dimensões normalizadas
- Menos redundância
- Mais joins necessários

### 2. Data Vault 2.0

**Componentes:**
- **Hubs**: Entidades de negócio (Cliente, Produto)
- **Links**: Relacionamentos (Pedido)
- **Satellites**: Atributos descritivos

**Vantagens:**
- Auditável (histórico completo)
- Escalável (paralelização)
- Flexível (adicionar fontes)

### 3. Data Warehouses

**Snowflake:**
- Separação compute/storage
- Auto-scaling
- Zero-copy cloning
- Time Travel

**AWS Redshift:**
- Columnar storage
- MPP architecture
- Distribution styles (KEY, ALL, EVEN)
- Sort keys

**Google BigQuery:**
- Serverless
- SQL ANSI
- Streaming ingestion
- Partitioning/Clustering

### 4. Data Lakes

**Arquitetura:**
```
Bronze (Raw) → Silver (Cleaned) → Gold (Curated)
```

**Governança:**
- Data Catalog (Glue, Purview)
- Data Lineage
- Access control (IAM, RBAC)
- Data Quality

### 5. Formatos de Arquivo

| Formato | Tipo | Compressão | Uso |
|---------|------|------------|-----|
| **Parquet** | Columnar | Snappy | Analytics, Spark |
| **ORC** | Columnar | Zlib | Hive, Presto |
| **Avro** | Row | Deflate | Streaming, Kafka |
| **Delta Lake** | Lakehouse | Snappy | ACID, Time Travel |
| **Iceberg** | Lakehouse | Various | Schema evolution |

### 6. Otimizações

**Particionamento:**
```python
# By date
/data/year=2024/month=01/day=15/data.parquet

# By category
/data/category=electronics/data.parquet

# Multi-level
/data/year=2024/month=01/category=books/data.parquet
```

**Bucketing:**
```sql
CREATE TABLE sales
USING parquet
PARTITIONED BY (year, month)
CLUSTERED BY (customer_id) INTO 100 BUCKETS;
```

## 🎯 Exercícios

### Exercício 1: Star Schema
Modelar DW para e-commerce:
- Fatos: Vendas, Devoluções
- Dimensões: Cliente, Produto, Tempo, Loja

### Exercício 2: SCD Type 2
Implementar histórico de mudanças em dimensões

### Exercício 3: Data Lake
Criar pipeline Bronze→Silver→Gold com validações

## 📖 Recursos

- **Livro**: "The Data Warehouse Toolkit" (Kimball)
- **Curso**: Snowflake Hands-on Essentials
- **Docs**: Delta Lake Documentation

## ✅ Checklist

- [ ] Criei Star Schema completo
- [ ] Implementei Data Vault
- [ ] Usei Snowflake/Redshift/BigQuery
- [ ] Organizei Data Lake em camadas
- [ ] Otimizei com particionamento
- [ ] Escolho formato certo para cada caso

## 🚀 Próximos Passos

➡️ **[Módulo 3: Processamento em Larga Escala](../03-processamento-larga-escala/)**
