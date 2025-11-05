# =€ Módulo 8: Performance e Otimização

## =Ë Visão Geral

Performance é critical em data engineering. Queries lentas custam tempo e dinheiro. Este módulo cobre técnicas avançadas de otimização para SQL, Spark, storage e networking.

**Duração:** 4-5 semanas | **Nível:** Avançado

---

## <¯ Objetivos

-  Otimizar queries SQL (10x-100x speedup)
-  Tuning de Spark jobs
-  Implementar caching efetivo
-  Otimizar storage e I/O
-  Capacity planning
-  Cost optimization

---

## =Ú Conteúdo

### 1. Query Optimization Fundamentals

#### 1.1 Query Execution Plan

```sql
-- EXPLAIN ANALYZE mostra o plano de execução real
EXPLAIN ANALYZE
SELECT
    c.customer_name,
    COUNT(*) as order_count,
    SUM(o.amount) as total_amount
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id
WHERE o.order_date >= '2024-01-01'
GROUP BY c.customer_id, c.customer_name;

/*
Exemplo de output:

GroupAggregate (cost=1000..2000 rows=100) (actual time=15..25 rows=95)
  Group Key: c.customer_id
  -> Sort (cost=900..950 rows=100) (actual time=10..12 rows=1000)
        Sort Key: c.customer_id
        -> Hash Join (cost=100..500 rows=1000) (actual time=2..8 rows=1000)
              Hash Cond: (o.customer_id = c.customer_id)
              -> Seq Scan on orders o (cost=0..400 rows=5000) (actual time=0..4 rows=5000)
                    Filter: (order_date >= '2024-01-01')
              -> Hash (cost=50..50 rows=100) (actual time=1..1 rows=100)
                    -> Seq Scan on customers c (cost=0..50 rows=100)

Planning Time: 0.5 ms
Execution Time: 27 ms
*/
```

**Como ler:**
- **cost=X..Y**: Estimativa (X=startup, Y=total)
- **rows=N**: Linhas estimadas
- **actual time=X..Y**: Tempo real (ms)
- **Seq Scan**: Full table scan (ruim para tabelas grandes)
- **Index Scan**: Usa índice (geralmente bom)
- **Hash Join**: Join usando hash table

#### 1.2 Índices Estratégicos

```sql
-- 1. B-TREE INDEX (padrão, maioria dos casos)
CREATE INDEX idx_orders_customer ON orders(customer_id);

-- 2. COMPOSITE INDEX (múltiplas colunas)
-- Ordem importa! Coloque coluna mais seletiva primeiro
CREATE INDEX idx_orders_customer_date ON orders(customer_id, order_date);

-- Bom para:
-- WHERE customer_id = X AND order_date = Y
-- WHERE customer_id = X
-- Não usa para: WHERE order_date = Y (segunda coluna)

-- 3. PARTIAL INDEX (apenas subset dos dados)
CREATE INDEX idx_active_orders
ON orders(customer_id, order_date)
WHERE status = 'active';

-- Reduz tamanho do índice em ~80% se apenas 20% são active

-- 4. COVERING INDEX (inclui colunas adicionais)
CREATE INDEX idx_orders_covering
ON orders(customer_id, order_date)
INCLUDE (amount, status);

-- Query pode ser respondida apenas pelo índice (index-only scan)

-- 5. EXPRESSION INDEX
CREATE INDEX idx_customer_email_lower
ON customers(LOWER(email));

-- Permite query:
SELECT * FROM customers WHERE LOWER(email) = 'user@example.com';

-- 6. GIN INDEX (para arrays, JSONB, full-text search)
CREATE INDEX idx_tags_gin ON products USING GIN(tags);

-- Permite:
SELECT * FROM products WHERE tags @> ARRAY['electronics', 'sale'];
```

**Quando NÃO criar índice:**
- Tabela pequena (< 1000 rows)
- Coluna com baixa cardinalidade (poucos valores distintos)
- Muitas escritas (índice degrada performance de INSERT/UPDATE)
- Coluna raramente usada em WHERE/JOIN

#### 1.3 Query Rewrite Patterns

```sql
-- L RUIM: Função em coluna indexada
SELECT * FROM orders
WHERE YEAR(order_date) = 2024;

--  BOM: Range query (usa índice)
SELECT * FROM orders
WHERE order_date >= '2024-01-01'
  AND order_date < '2025-01-01';


-- L RUIM: OR com colunas diferentes
SELECT * FROM customers
WHERE email = 'test@test.com'
   OR phone = '1234567890';

--  BOM: UNION (cada parte usa índice)
SELECT * FROM customers WHERE email = 'test@test.com'
UNION
SELECT * FROM customers WHERE phone = '1234567890';


-- L RUIM: NOT IN com subquery
SELECT * FROM customers
WHERE customer_id NOT IN (
    SELECT customer_id FROM orders
);

--  BOM: LEFT JOIN com NULL check
SELECT c.*
FROM customers c
LEFT JOIN orders o ON c.customer_id = o.customer_id
WHERE o.customer_id IS NULL;


-- L RUIM: DISTINCT com ORDER BY
SELECT DISTINCT customer_id
FROM orders
ORDER BY order_date;  -- order_date não está no SELECT!

--  BOM: Window function ou subquery
SELECT DISTINCT customer_id
FROM (
    SELECT customer_id, order_date
    FROM orders
    ORDER BY order_date
) ordered_orders;


-- L RUIM: COUNT(*) em tabela grande
SELECT COUNT(*) FROM orders;  -- Lento!

--  BOM: Usar estatísticas do sistema
SELECT reltuples::BIGINT AS estimate
FROM pg_class
WHERE relname = 'orders';


-- L RUIM: OFFSET para paginação profunda
SELECT * FROM orders
ORDER BY order_id
LIMIT 20 OFFSET 1000000;  -- Muito lento!

--  BOM: Keyset pagination
SELECT * FROM orders
WHERE order_id > :last_seen_id
ORDER BY order_id
LIMIT 20;
```

#### 1.4 Join Optimization

```sql
-- 1. Join order importa! Menor tabela primeiro
-- L RUIM
SELECT *
FROM orders o  -- 10M rows
JOIN customers c ON o.customer_id = c.customer_id  -- 100K rows
WHERE c.country = 'USA';

--  BOM: Filter customers first
SELECT *
FROM customers c  -- 100K -> 20K após filter
JOIN orders o ON c.customer_id = o.customer_id
WHERE c.country = 'USA';


-- 2. Use INNER JOIN quando possível (mais rápido que OUTER)
-- Se você não precisa de linhas sem match, use INNER


-- 3. Pre-aggregate antes de JOIN
-- L RUIM
SELECT
    c.customer_name,
    SUM(o.amount)
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id
GROUP BY c.customer_id, c.customer_name;

--  BOM: Aggregate first
WITH order_totals AS (
    SELECT customer_id, SUM(amount) as total
    FROM orders
    GROUP BY customer_id
)
SELECT c.customer_name, ot.total
FROM customers c
JOIN order_totals ot ON c.customer_id = ot.customer_id;


-- 4. Use EXISTS instead of IN para large subqueries
-- L RUIM
SELECT * FROM customers
WHERE customer_id IN (
    SELECT customer_id FROM orders WHERE amount > 1000
);

--  BOM
SELECT * FROM customers c
WHERE EXISTS (
    SELECT 1 FROM orders o
    WHERE o.customer_id = c.customer_id
    AND o.amount > 1000
);
```

---

### 2. Spark Performance Tuning

#### 2.1 Memory Configuration

```python
from pyspark.sql import SparkSession

# Configuração otimizada
spark = SparkSession.builder \
    .appName("OptimizedApp") \
    .config("spark.executor.memory", "8g") \
    .config("spark.executor.memoryOverhead", "2g")  # 20-25% da executor memory \
    .config("spark.driver.memory", "4g") \
    .config("spark.driver.memoryOverhead", "1g") \
    .config("spark.memory.fraction", "0.8")  # % para execution e storage \
    .config("spark.memory.storageFraction", "0.5")  # Split entre cache e execution \
    .getOrCreate()

"""
Memory breakdown:
- executor.memory: 8GB (JVM heap)
- executor.memoryOverhead: 2GB (off-heap, Python, etc)
- Total per executor: 10GB

Dentro dos 8GB heap:
- 80% (6.4GB) para Spark (execution + storage)
  - 50% (3.2GB) para caching
  - 50% (3.2GB) para execution
- 20% (1.6GB) para user code (UDFs, etc)
"""

# Regras gerais:
# - executor.memory: 4-8GB (sweet spot)
# - executor.cores: 4-5 (mais = mais overhead)
# - Num executors: depende do cluster size
# - Total executor memory: não exceder 75% da node memory
```

#### 2.2 Shuffle Optimization

```python
# Shuffle é a operação mais cara no Spark!

# 1. Reduza shuffle partitions para small datasets
spark.conf.set("spark.sql.shuffle.partitions", "50")  # Default: 200

# Regra: 100-200MB por partition
# Se seu dataset final é 5GB:
# 5000MB / 100MB = 50 partitions

# 2. Use broadcast join para tabelas pequenas (< 10MB)
from pyspark.sql.functions import broadcast

df_large = spark.read.parquet("s3://bucket/large_table/")  # 1TB
df_small = spark.read.parquet("s3://bucket/small_table/")  # 5MB

# Force broadcast
df_result = df_large.join(broadcast(df_small), "key")

# 3. Repartition antes de operações pesadas
df = df.repartition(200, "customer_id")  # Distribui por hash de customer_id

# 4. Coalesce para reduzir partições (sem shuffle)
df = df.coalesce(10)  # Use ao final antes de write

# 5. Habilite AQE (Adaptive Query Execution) - Spark 3.0+
spark.conf.set("spark.sql.adaptive.enabled", "true")
spark.conf.set("spark.sql.adaptive.coalescePartitions.enabled", "true")
spark.conf.set("spark.sql.adaptive.skewJoin.enabled", "true")
```

#### 2.3 Data Skew Handling

```python
# Problema: Uma partition tem muito mais dados que outras

# Detectar skew
df.groupBy("partition_key").count().orderBy("count", ascending=False).show()

# Solução 1: Salting
from pyspark.sql.functions import rand, concat, lit

# Adiciona salt (número aleatório) à chave
df_salted = df.withColumn(
    "salted_key",
    concat(col("skewed_key"), lit("_"), (rand() * 10).cast("int"))
)

# Para join, explodir a tabela menor com todos os salts
df_small_exploded = df_small.withColumn(
    "salt",
    explode(array([lit(i) for i in range(10)]))
).withColumn(
    "salted_key",
    concat(col("key"), lit("_"), col("salt"))
)

result = df_salted.join(df_small_exploded, "salted_key")


# Solução 2: Isolate skewed keys
# Processar keys problemáticas separadamente
skewed_values = ['key1', 'key2', 'key3']

df_normal = df.filter(~col("key").isin(skewed_values))
df_skewed = df.filter(col("key").isin(skewed_values))

# Process separately with different strategies
result_normal = process_normal(df_normal)
result_skewed = process_skewed_with_broadcast(df_skewed)

result = result_normal.union(result_skewed)
```

#### 2.4 Caching Strategy

```python
from pyspark import StorageLevel

# Quando cachear?
# 1. DataFrame usado múltiplas vezes
# 2. Após operação cara (join, aggregate)
# 3. Em iterações (ML training)

df_expensive = df.filter(...).join(...).groupBy(...).agg(...)

# Cache em memória
df_expensive.cache()  # Ou persist(StorageLevel.MEMORY_AND_DISK)

# Usar múltiplas vezes
result1 = df_expensive.filter(...)
result2 = df_expensive.groupBy(...)

# Liberar cache quando não precisar mais
df_expensive.unpersist()


# Storage Levels:
# MEMORY_ONLY: Apenas RAM (rápido, pode perder dados)
# MEMORY_AND_DISK: RAM + Disk overflow (recomendado)
# DISK_ONLY: Apenas disco (lento)
# MEMORY_AND_DISK_SER: Serializado (economiza RAM, mais CPU)

# Exemplo com diferentes níveis
df.persist(StorageLevel.MEMORY_AND_DISK_SER)
```

#### 2.5 File Format Optimization

```python
# Parquet > ORC > CSV (para analytics)

# Escrever Parquet otimizado
df.write \
    .mode("overwrite") \
    .partitionBy("year", "month") \
    .option("compression", "snappy") \  # snappy: rápido, gzip: menor
    .parquet("s3://bucket/optimized/")

# Leitura otimizada
df = spark.read \
    .parquet("s3://bucket/optimized/") \
    .select("col1", "col2")  \  # Column pruning
    .filter("year = 2024")  \     # Partition pruning
    .filter("amount > 100")       # Predicate pushdown

# Coalesce files antes de escrever (evita small files)
df.coalesce(50).write.parquet("output/")

# Repartition para distribuir melhor
df.repartition(200, "customer_id").write.parquet("output/")
```

---

### 3. Caching Strategies

#### 3.1 Redis Caching

```python
import redis
import json
from functools import wraps
from typing import Any, Callable

redis_client = redis.Redis(
    host='localhost',
    port=6379,
    db=0,
    decode_responses=True
)

def cache_result(ttl: int = 3600):
    """Decorator para cachear resultados de funções"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # Gerar cache key
            cache_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"

            # Tentar obter do cache
            cached = redis_client.get(cache_key)
            if cached:
                print(f" Cache HIT: {cache_key}")
                return json.loads(cached)

            # Cache miss: executar função
            print(f"L Cache MISS: {cache_key}")
            result = func(*args, **kwargs)

            # Salvar no cache
            redis_client.setex(
                cache_key,
                ttl,
                json.dumps(result)
            )

            return result
        return wrapper
    return decorator


# Uso
@cache_result(ttl=3600)  # Cache por 1 hora
def get_customer_metrics(customer_id: int):
    """Query cara que queremos cachear"""
    import psycopg2

    conn = psycopg2.connect("...")
    cur = conn.cursor()

    cur.execute("""
        SELECT
            SUM(amount) as total_spent,
            COUNT(*) as order_count,
            AVG(amount) as avg_order
        FROM orders
        WHERE customer_id = %s
    """, (customer_id,))

    result = cur.fetchone()
    return {
        'total_spent': float(result[0]),
        'order_count': int(result[1]),
        'avg_order': float(result[2])
    }

# Primeira chamada: executa query
metrics = get_customer_metrics(123)  # Cache MISS, ~500ms

# Segunda chamada: retorna do cache
metrics = get_customer_metrics(123)  # Cache HIT, ~5ms
```

#### 3.2 Application-Level Caching

```python
from functools import lru_cache
from datetime import datetime, timedelta

class CachedDataLoader:
    """Loader com cache in-memory e TTL"""

    def __init__(self, ttl_seconds=300):
        self.cache = {}
        self.ttl = timedelta(seconds=ttl_seconds)

    def get_or_load(self, key, loader_func):
        """Get from cache ou executa loader"""
        now = datetime.now()

        # Check cache
        if key in self.cache:
            value, timestamp = self.cache[key]
            if now - timestamp < self.ttl:
                return value

        # Load data
        value = loader_func()
        self.cache[key] = (value, now)
        return value

    def invalidate(self, key=None):
        """Invalidar cache"""
        if key:
            self.cache.pop(key, None)
        else:
            self.cache.clear()


# Uso
loader = CachedDataLoader(ttl_seconds=600)

def load_product_catalog():
    """Load heavy data"""
    import pandas as pd
    return pd.read_sql("SELECT * FROM products", con=engine)

# Cache automatically
products = loader.get_or_load("products", load_product_catalog)
```

---

### 4. Storage Optimization

#### 4.1 Compression

```python
import pandas as pd

# Comparação de compression

df = pd.read_csv("large_file.csv")

# Sem compressão
df.to_parquet("uncompressed.parquet", compression=None)
# Size: 1.0GB

# Snappy (padrão, balanceado)
df.to_parquet("snappy.parquet", compression="snappy")
# Size: 300MB, Read: 2s, Write: 3s

# Gzip (melhor compressão)
df.to_parquet("gzip.parquet", compression="gzip")
# Size: 200MB, Read: 5s, Write: 10s

# Zstd (melhor balanceado)
df.to_parquet("zstd.parquet", compression="zstd")
# Size: 220MB, Read: 2.5s, Write: 4s

"""
Recomendações:
- Snappy: Default, boa para queries frequentes
- Gzip: Storage crítico, dados raramente acessados
- Zstd: Melhor trade-off (requer Spark 3.0+)
- None: Apenas se processing speed é crítico
"""
```

#### 4.2 Partitioning Best Practices

```python
# 1. Particionar por coluna frequentemente filtrada
df.write.partitionBy("year", "month").parquet("output/")

# Estrutura:
# output/
#   year=2024/
#     month=01/
#       part-00000.parquet
#     month=02/
#       part-00000.parquet

# Query automaticamente faz partition pruning:
spark.read.parquet("output/").filter("year = 2024 AND month = 1")
# Lê apenas year=2024/month=01/


# 2. Evite over-partitioning
# L RUIM: Muitas partições pequenas
df.write.partitionBy("year", "month", "day", "hour").parquet("...")
# Result: 8760 partições/ano (365 days * 24 hours)
# Problema: Overhead de metadados, slow queries

#  BOM: Partições balanceadas (100-200MB cada)
df.write.partitionBy("year", "month").parquet("...")


# 3. Bucketing para joins frequentes
df.write \
    .bucketBy(100, "customer_id") \
    .sortBy("order_date") \
    .saveAsTable("orders_bucketed")

# Benefício: Joins evitam shuffle se ambas bucketed igual
```

---

### 5. Cost Optimization

#### 5.1 Cloud Cost Monitoring

```python
# AWS Cost per Query (Athena example)

def estimate_athena_cost(data_scanned_gb):
    """
    Athena: $5 per TB scanned
    """
    cost_per_gb = 5.0 / 1024  # $0.00488 per GB
    return data_scanned_gb * cost_per_gb

# Exemplo
data_scanned = 100  # GB
cost = estimate_athena_cost(data_scanned)
print(f"Query cost: ${cost:.2f}")  # $0.49

# Otimizações para reduzir custo:
# 1. Particionar dados
# 2. Usar Parquet (compressão ~5x)
# 3. Column pruning (SELECT apenas necessário)
# 4. CTAS para pre-aggregate

# Antes: Scan 100GB, $0.49
query = "SELECT * FROM sales WHERE year = 2024"

# Depois: Scan 20GB (partitioned), $0.10
query = "SELECT customer_id, amount FROM sales_partitioned WHERE year = 2024"
# Savings: 80%!
```

#### 5.2 Spot Instances para Batch

```python
# AWS EMR com Spot instances

emr_config = {
    "Instances": {
        "InstanceGroups": [
            {
                "Name": "Master",
                "Market": "ON_DEMAND",  # Master sempre on-demand
                "InstanceRole": "MASTER",
                "InstanceType": "r5.xlarge",
                "InstanceCount": 1
            },
            {
                "Name": "Core",
                "Market": "SPOT",  # Core pode ser spot
                "BidPrice": "0.30",  # Bid price
                "InstanceRole": "CORE",
                "InstanceType": "r5.2xlarge",
                "InstanceCount": 2
            },
            {
                "Name": "Task",
                "Market": "SPOT",  # Task ideal para spot
                "BidPrice": "0.30",
                "InstanceRole": "TASK",
                "InstanceType": "r5.2xlarge",
                "InstanceCount": 5
            }
        ]
    }
}

# Savings: 70-90% vs on-demand!
# On-demand r5.2xlarge: $0.504/hour
# Spot típico: $0.15/hour
# Savings: 70%

# Trade-off: Pode ser interrompido (mas task nodes são resilient)
```

---

## =» Exercícios Práticos

### Exercício 1: Query Optimization
Otimize queries lentas (de minutos para segundos).

=Á [exercicios/ex01-query-optimization.sql](./exercicios/ex01-query-optimization.sql)

### Exercício 2: Spark Tuning
Tune Spark job (de horas para minutos).

=Á [exercicios/ex02-spark-tuning.py](./exercicios/ex02-spark-tuning.py)

### Exercício 3: Caching Strategy
Implemente caching multi-layer.

=Á [exercicios/ex03-caching-strategy.py](./exercicios/ex03-caching-strategy.py)

---

## <¯ Projeto: Performance Audit

**Objetivo:** Auditar e otimizar sistema existente

**Deliverables:**
1. Identificar top 10 slow queries
2. Criar índices otimizados
3. Reescrever queries ineficientes
4. Tune Spark jobs
5. Implementar caching
6. Medir before/after

=Á [projeto/performance-audit/](./projeto/performance-audit/)

---

##  Checklist

- [ ] Analisar explain plans
- [ ] Criar índices estratégicos
- [ ] Reescrever queries
- [ ] Tune Spark configs
- [ ] Implementar caching
- [ ] Otimizar storage
- [ ] Reduzir custos 50%+

---

**Performance é journey, não destination. Continue monitorando e otimizando!** =€
