# ⚡ Apache Spark: Fundamentos e Arquitetura

## 📋 Índice

1. [O que é Apache Spark](#o-que-é-apache-spark)
2. [Arquitetura do Spark](#arquitetura-do-spark)
3. [RDDs vs DataFrames vs Datasets](#rdds-vs-dataframes-vs-datasets)
4. [Transformações e Ações](#transformações-e-ações)
5. [Spark SQL](#spark-sql)
6. [Otimizações e Best Practices](#otimizações-e-best-practices)
7. [Spark Streaming](#spark-streaming)

---

## O que é Apache Spark

**Apache Spark** é um engine de processamento distribuído para big data, criado para ser:
- **Rápido**: Até 100x mais rápido que Hadoop MapReduce (in-memory)
- **Unificado**: Batch, streaming, SQL, ML e graph processing
- **Fácil de usar**: APIs em Scala, Python, Java, R, SQL

### Por que Spark?

**Antes (Hadoop MapReduce):**
```
Input → Map → Shuffle → Reduce → Output (salvo em disco)
Input → Map → Shuffle → Reduce → Output (salvo em disco)  # Cada job salva no HDFS
```

**Com Spark:**
```
Input → Transform → Transform → Transform → Action (tudo in-memory)
```

**Vantagens:**
- ✅ Processamento in-memory (cache de dados)
- ✅ DAG execution engine (otimiza query plan)
- ✅ APIs de alto nível (DataFrame, SQL)
- ✅ Lazy evaluation (só executa quando necessário)

---

## Arquitetura do Spark

### Componentes

```
┌─────────────────────────────────────────────────┐
│              Driver Program                      │
│  ┌──────────────────────────────────────┐       │
│  │        SparkContext                   │       │
│  │  (coordena execução distribuída)     │       │
│  └──────────────┬───────────────────────┘       │
└─────────────────┼───────────────────────────────┘
                  │
        ┌─────────┴─────────┐
        │                   │
   ┌────▼─────┐      ┌─────▼────┐
   │ Worker 1 │      │ Worker 2 │
   │          │      │          │
   │ Executor │      │ Executor │
   │ ┌──────┐ │      │ ┌──────┐ │
   │ │Task 1│ │      │ │Task 3│ │
   │ │Task 2│ │      │ │Task 4│ │
   │ └──────┘ │      │ └──────┘ │
   └──────────┘      └──────────┘
```

**Driver:**
- Executa a aplicação Spark (função main)
- Cria SparkContext
- Converte código em DAG de tasks
- Agenda tasks nos executors

**Executors:**
- Processos que executam tasks
- Armazenam dados em cache
- Reportam status ao Driver

**Cluster Manager:**
- YARN, Kubernetes, Mesos, Standalone
- Aloca recursos (CPU, memória)

### SparkSession (Spark 2.0+)

```python
from pyspark.sql import SparkSession

# Criar SparkSession (unified entry point)
spark = SparkSession.builder \
    .appName("MyApp") \
    .master("local[4]")  # Local com 4 threads, ou "yarn" para cluster
    .config("spark.executor.memory", "4g") \
    .config("spark.executor.cores", "2") \
    .enableHiveSupport() \
    .getOrCreate()

# SparkSession dá acesso a:
# - spark.sql()      → SQL queries
# - spark.read       → Leitura de dados
# - spark.sparkContext → RDD operations
```

---

## RDDs vs DataFrames vs Datasets

### 1. RDD (Resilient Distributed Dataset)

**Características:**
- API de baixo nível
- Type-safe (mas sem schema)
- Lazy evaluation
- Imutável

```python
# Criar RDD
rdd = spark.sparkContext.parallelize([1, 2, 3, 4, 5])

# Transformações
rdd2 = rdd.map(lambda x: x * 2)
rdd3 = rdd2.filter(lambda x: x > 5)

# Ação (trigger execution)
result = rdd3.collect()  # [6, 8, 10]

# RDD de texto
text_rdd = spark.sparkContext.textFile("hdfs://path/to/file.txt")
words = text_rdd.flatMap(lambda line: line.split(" "))
word_counts = words.map(lambda word: (word, 1)).reduceByKey(lambda a, b: a + b)
```

**Quando usar RDD:**
- Controle fino sobre particionamento
- Manipulação de dados não estruturados
- Algoritmos customizados de baixo nível

### 2. DataFrame

**Características:**
- API de alto nível (SQL-like)
- Schema definido (colunas tipadas)
- Catalyst optimizer (otimiza query plan)
- Tungsten execution (código gerado em tempo de execução)

```python
from pyspark.sql.functions import col, sum, avg, count, when

# Criar DataFrame
data = [
    ("Alice", 25, "Engineer", 100000),
    ("Bob", 30, "Manager", 120000),
    ("Charlie", 35, "Engineer", 110000),
    ("Diana", 28, "Analyst", 90000)
]
df = spark.createDataFrame(data, ["name", "age", "role", "salary"])

# Mostrar schema
df.printSchema()
# root
#  |-- name: string (nullable = true)
#  |-- age: long (nullable = true)
#  |-- role: string (nullable = true)
#  |-- salary: long (nullable = true)

# Operações
df.show()
df.select("name", "salary").show()
df.filter(col("age") > 28).show()
df.groupBy("role").agg(avg("salary").alias("avg_salary")).show()

# SQL-like
df.createOrReplaceTempView("employees")
spark.sql("SELECT role, AVG(salary) FROM employees GROUP BY role").show()
```

### 3. Dataset (Scala/Java only)

**Características:**
- Type-safe como RDD
- Otimizado como DataFrame
- Não disponível em Python (Python tem apenas DataFrame)

```scala
// Scala - Dataset
case class Employee(name: String, age: Int, role: String, salary: Double)

val ds = spark.read.json("employees.json").as[Employee]

// Type-safe operations
ds.filter(emp => emp.age > 30)
  .map(emp => emp.name)
  .show()
```

### Comparação

| Feature | RDD | DataFrame | Dataset |
|---------|-----|-----------|---------|
| **Type Safety** | ❌ Runtime | ❌ Runtime | ✅ Compile-time |
| **Optimization** | ❌ No | ✅ Catalyst | ✅ Catalyst |
| **Performance** | Baixa | Alta | Alta |
| **API Level** | Baixo | Alto | Alto |
| **Linguagens** | Todas | Todas | Scala/Java |
| **Usar quando** | Controle fino | Analytics | Type-safety |

**Recomendação:** Use **DataFrame** em 99% dos casos.

---

## Transformações e Ações

### Lazy Evaluation

Spark usa **lazy evaluation**: transformações só são executadas quando uma **ação** é chamada.

```python
# Nenhuma execução ainda
df2 = df.filter(col("age") > 30)         # Transformação
df3 = df2.select("name", "salary")       # Transformação

# Agora Spark executa TUDO de uma vez (otimizado)
df3.show()  # Ação - trigger execution
```

### Transformações (Lazy)

**Narrow Transformations** (sem shuffle):
```python
# map, filter, select - cada partição processa independente
df.select("name", "age")
df.filter(col("age") > 25)
df.withColumn("age_plus_10", col("age") + 10)
```

**Wide Transformations** (com shuffle):
```python
# groupBy, join - requer redistribuir dados entre partições
df.groupBy("role").count()
df1.join(df2, "id")
df.orderBy("salary")
```

### Ações (Eager - executam imediatamente)

```python
# Coletar dados para driver
df.collect()           # Retorna lista de Rows (CUIDADO: traz tudo para memória)
df.take(5)             # Primeiros 5 rows
df.first()             # Primeiro row
df.head(3)             # Primeiros 3 rows

# Mostrar dados
df.show()              # Mostra 20 rows
df.show(100, False)    # 100 rows, sem truncar strings

# Contar
df.count()             # Número de rows
df.distinct().count()  # Rows únicos

# Salvar
df.write.parquet("/path/to/output")
df.write.mode("overwrite").csv("/path/to/csv")

# Iterar (local)
for row in df.collect():
    print(row.name, row.age)
```

---

## Spark SQL

### Ler Dados

```python
# CSV
df = spark.read.csv("data.csv", header=True, inferSchema=True)

# Parquet (formato colunar otimizado)
df = spark.read.parquet("data.parquet")

# JSON
df = spark.read.json("data.json")

# JDBC (databases)
df = spark.read \
    .format("jdbc") \
    .option("url", "jdbc:postgresql://localhost:5432/mydb") \
    .option("dbtable", "users") \
    .option("user", "admin") \
    .option("password", "secret") \
    .load()

# Hive table
df = spark.table("warehouse.users")

# Opções avançadas
df = spark.read \
    .option("header", "true") \
    .option("inferSchema", "true") \
    .option("delimiter", "|") \
    .option("quote", '"') \
    .option("escape", "\\") \
    .csv("data.csv")
```

### Operações Comuns

```python
from pyspark.sql.functions import *

# SELECT
df.select("name", "age")
df.select(col("name"), (col("salary") * 1.1).alias("new_salary"))

# WHERE / FILTER
df.filter(col("age") > 30)
df.where((col("age") > 25) & (col("role") == "Engineer"))

# GROUP BY
df.groupBy("role").agg(
    count("*").alias("count"),
    avg("salary").alias("avg_salary"),
    max("salary").alias("max_salary")
)

# ORDER BY
df.orderBy(col("salary").desc())
df.orderBy("age", "name")

# JOIN
df1.join(df2, df1.id == df2.user_id, "inner")  # inner, left, right, outer

# UNION
df1.union(df2)  # Mesmas colunas

# DISTINCT
df.select("role").distinct()

# DROP DUPLICATES
df.dropDuplicates(["name", "age"])

# WITH COLUMN
df.withColumn("age_category", 
    when(col("age") < 30, "Young")
    .when(col("age") < 50, "Middle")
    .otherwise("Senior")
)

# DROP COLUMN
df.drop("temporary_col")

# RENAME COLUMN
df.withColumnRenamed("old_name", "new_name")
```

### Window Functions

```python
from pyspark.sql.window import Window

# Definir window
window_spec = Window.partitionBy("role").orderBy(col("salary").desc())

# Ranking
df.withColumn("rank", rank().over(window_spec)) \
  .withColumn("dense_rank", dense_rank().over(window_spec)) \
  .withColumn("row_number", row_number().over(window_spec)) \
  .show()

# Agregações em janela
window_agg = Window.partitionBy("role")

df.withColumn("avg_salary_by_role", avg("salary").over(window_agg)) \
  .withColumn("max_salary_by_role", max("salary").over(window_agg)) \
  .show()

# Lag / Lead
window_order = Window.partitionBy("role").orderBy("hire_date")

df.withColumn("previous_salary", lag("salary", 1).over(window_order)) \
  .withColumn("next_salary", lead("salary", 1).over(window_order)) \
  .show()

# Running total
df.withColumn("running_total", 
    sum("salary").over(Window.partitionBy("role").orderBy("hire_date")
                       .rowsBetween(Window.unboundedPreceding, Window.currentRow))
).show()
```

### SQL Queries

```python
# Registrar DataFrame como temp view
df.createOrReplaceTempView("employees")

# SQL Query
result = spark.sql("""
    SELECT 
        role,
        COUNT(*) as count,
        AVG(salary) as avg_salary,
        PERCENTILE_APPROX(salary, 0.5) as median_salary
    FROM employees
    WHERE age > 25
    GROUP BY role
    HAVING AVG(salary) > 100000
    ORDER BY avg_salary DESC
""")

result.show()

# CTEs (Common Table Expressions)
spark.sql("""
    WITH high_earners AS (
        SELECT * FROM employees WHERE salary > 100000
    ),
    role_stats AS (
        SELECT role, AVG(salary) as avg_sal FROM high_earners GROUP BY role
    )
    SELECT * FROM role_stats WHERE avg_sal > 110000
""").show()
```

---

## Otimizações e Best Practices

### 1. Particionamento

```python
# Repartition (full shuffle - caro)
df_repart = df.repartition(10)  # 10 partições
df_repart = df.repartition(10, "role")  # Particionar por coluna

# Coalesce (reduzir partições SEM shuffle)
df_coal = df.coalesce(2)  # Reduz para 2 partições (mais eficiente)

# Verificar número de partições
df.rdd.getNumPartitions()

# Salvar com particionamento
df.write.partitionBy("year", "month").parquet("/data/partitioned")
```

**Regra de ouro:** 1 partição = 1 core. Partições devem ter ~128MB-1GB cada.

### 2. Cache / Persist

```python
# Cache in-memory (padrão: MEMORY_AND_DISK)
df.cache()

# Persist com storage level customizado
from pyspark import StorageLevel
df.persist(StorageLevel.MEMORY_ONLY)
df.persist(StorageLevel.MEMORY_AND_DISK_SER)  # Serializado (menos memória)

# Usar cache quando:
# - DataFrame é reutilizado múltiplas vezes
# - Transformações custosas antes do cache

df_cached = df.filter(col("age") > 30).cache()
df_cached.count()  # Executa e cacheia
df_cached.groupBy("role").count().show()  # Usa cache
df_cached.select("name").show()  # Usa cache

# Liberar cache
df.unpersist()
```

### 3. Broadcast Join

Para joins com tabela pequena (<10MB):

```python
from pyspark.sql.functions import broadcast

# Join normal (shuffle dos dois lados)
df_large.join(df_small, "id")

# Broadcast join (df_small enviado para todos os executors)
df_large.join(broadcast(df_small), "id")

# Spark decide automaticamente se < spark.sql.autoBroadcastJoinThreshold (10MB)
```

### 4. Evitar Shuffles Desnecessários

```python
# ❌ Ruim: múltiplos shuffles
df.groupBy("role").count() \
  .filter(col("count") > 5) \
  .orderBy("count")

# ✅ Bom: filter antes do groupBy
df.filter(...)  # Reduz dados antes do shuffle
  .groupBy("role").count() \
  .orderBy("count")
```

### 5. Usar Catalyst Optimizer

```python
# DataFrame usa Catalyst optimizer automaticamente
df.filter(col("age") > 30).select("name")  # Otimizado

# RDD NÃO usa Catalyst
rdd.filter(lambda x: x[1] > 30).map(lambda x: x[0])  # Não otimizado

# Ver query plan
df.explain(True)  # Mostra: Parsed, Analyzed, Optimized, Physical plan
```

### 6. Evitar UDFs (User Defined Functions)

```python
# ❌ Lento: UDF em Python (serialização Python <-> JVM)
from pyspark.sql.functions import udf
from pyspark.sql.types import IntegerType

def age_category_udf(age):
    if age < 30: return 1
    elif age < 50: return 2
    else: return 3

age_cat = udf(age_category_udf, IntegerType())
df.withColumn("category", age_cat(col("age")))

# ✅ Rápido: usar funções nativas
df.withColumn("category",
    when(col("age") < 30, 1)
    .when(col("age") < 50, 2)
    .otherwise(3)
)

# Se UDF é necessária, use Pandas UDF (vetorizado)
from pyspark.sql.functions import pandas_udf
import pandas as pd

@pandas_udf(IntegerType())
def age_category_pandas(ages: pd.Series) -> pd.Series:
    return pd.cut(ages, bins=[0, 30, 50, 100], labels=[1, 2, 3])

df.withColumn("category", age_category_pandas(col("age")))
```

---

## Spark Streaming

### Structured Streaming

```python
# Ler stream de arquivos
stream_df = spark.readStream \
    .format("csv") \
    .option("header", "true") \
    .schema(schema) \
    .load("/data/streaming/input/")

# Transformações (mesmas APIs do DataFrame)
result = stream_df \
    .filter(col("value") > 100) \
    .groupBy("category").count()

# Escrever stream
query = result.writeStream \
    .outputMode("complete")  # complete, append, update
    .format("console") \
    .start()

query.awaitTermination()

# Stream de Kafka
kafka_df = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "localhost:9092") \
    .option("subscribe", "topic1") \
    .load()

# Processar mensagens
messages = kafka_df.selectExpr("CAST(value AS STRING)")

# Watermark para late data
stream_df.withWatermark("timestamp", "10 minutes") \
    .groupBy(window(col("timestamp"), "5 minutes"), "user_id") \
    .count()
```

### Triggers

```python
# Continuous (low latency ~1ms)
.trigger(continuous="1 second")

# Micro-batch (default)
.trigger(processingTime="5 seconds")

# One-time (processa dados disponíveis e para)
.trigger(once=True)

# Available-now (processa tudo que está disponível)
.trigger(availableNow=True)
```

---

## 🎯 Checklist de Performance

- ✅ Use DataFrame ao invés de RDD
- ✅ Particione dados apropriadamente (128MB-1GB por partição)
- ✅ Cache DataFrames reutilizados
- ✅ Use broadcast join para tabelas pequenas
- ✅ Evite UDFs Python (use funções nativas ou Pandas UDF)
- ✅ Use formatos colunares (Parquet, ORC)
- ✅ Filter dados cedo (pushdown predicates)
- ✅ Evite shuffles desnecessários
- ✅ Monitore Spark UI para identificar bottlenecks

---

## 📚 Referências

- [Spark Documentation](https://spark.apache.org/docs/latest/)
- [Spark: The Definitive Guide](https://www.oreilly.com/library/view/spark-the-definitive/9781491912201/)
- [High Performance Spark](https://www.oreilly.com/library/view/high-performance-spark/9781491943199/)

---

**Próximo:** [02-spark-performance-tuning.md](./02-spark-performance-tuning.md)
