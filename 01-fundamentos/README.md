# =0 Módulo 1: Fundamentos de Engenharia de Dados

## =Ë Visão Geral
Este módulo cobre os fundamentos essenciais que todo Engenheiro de Dados sênior deve dominar. São conceitos que você usará diariamente independente da stack ou empresa.

**Duração:** 3-4 semanas
**Nível:** Básico-Intermediário
**Pré-requisitos:** Conhecimentos básicos de programação

---

## <¯ Objetivos de Aprendizado

Ao final deste módulo, você será capaz de:
-  Projetar arquiteturas de sistemas de dados
-  Escrever SQL complexo e otimizado
-  Programar em Python para engenharia de dados
-  Aplicar estruturas de dados adequadas para big data
-  Usar Docker para containerização
-  Trabalhar eficientemente com Git e Linux

---

## =Ú Conteúdo

### 1. Arquitetura de Sistemas de Dados

#### 1.1 Fundamentos de Arquitetura

**Conceitos Essenciais:**
- **OLTP vs OLAP**: Entenda quando usar cada um
  - OLTP: Transações online, baixa latência, muitas escritas
  - OLAP: Análises, queries complexas, agregações

- **Batch vs Streaming**: Trade-offs e casos de uso
  - Batch: Processamento periódico, maior throughput
  - Streaming: Processamento contínuo, menor latência

- **Data Warehouse vs Data Lake vs Data Lakehouse**
  - DW: Estruturado, schema-on-write, otimizado para BI
  - DL: Não estruturado, schema-on-read, armazena tudo
  - DLH: Combina flexibilidade do lake com governança do warehouse

**Padrões Arquiteturais:**

1. **Lambda Architecture**
   ```
   Data Sources ’ Batch Layer  ’ Serving Layer ’ Applications
                “ Speed Layer —
   ```
   - Batch Layer: Processamento completo e preciso
   - Speed Layer: Processamento incremental e rápido
   - Serving Layer: Merge das duas visões
   - Trade-offs: Complexidade vs completude

2. **Kappa Architecture**
   ```
   Data Sources ’ Streaming Layer ’ Serving Layer ’ Applications
   ```
   - Simplificação da Lambda
   - Tudo é stream
   - Reprocessamento através de replay

3. **Data Mesh**
   - Domain-oriented decentralized data ownership
   - Data as a product
   - Self-serve data infrastructure
   - Federated computational governance

=Ö **Leitura:** [teoria/arquiteturas-dados.md](./teoria/arquiteturas-dados.md)

---

### 2. SQL Avançado

#### 2.1 Window Functions (Funções de Janela)

**Conceitos:**
Window functions operam em um conjunto de linhas relacionadas à linha atual.

```sql
-- ROW_NUMBER: Numera linhas dentro de uma partição
SELECT
    employee_id,
    department,
    salary,
    ROW_NUMBER() OVER (PARTITION BY department ORDER BY salary DESC) as rank
FROM employees;

-- RANK vs DENSE_RANK
-- RANK: Pula números após empates (1,2,2,4)
-- DENSE_RANK: Não pula (1,2,2,3)
SELECT
    product_name,
    category,
    revenue,
    RANK() OVER (PARTITION BY category ORDER BY revenue DESC) as rank,
    DENSE_RANK() OVER (PARTITION BY category ORDER BY revenue DESC) as dense_rank
FROM products;

-- LAG e LEAD: Acessar linhas anteriores/posteriores
SELECT
    date,
    revenue,
    LAG(revenue, 1) OVER (ORDER BY date) as prev_revenue,
    revenue - LAG(revenue, 1) OVER (ORDER BY date) as revenue_diff
FROM daily_sales;

-- RUNNING TOTALS com SUM
SELECT
    date,
    amount,
    SUM(amount) OVER (ORDER BY date) as running_total
FROM transactions;

-- Moving Averages
SELECT
    date,
    price,
    AVG(price) OVER (
        ORDER BY date
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ) as moving_avg_7days
FROM stock_prices;
```

#### 2.2 CTEs (Common Table Expressions) e Recursão

```sql
-- CTE Simples
WITH high_value_customers AS (
    SELECT
        customer_id,
        SUM(order_value) as total_spent
    FROM orders
    WHERE order_date >= '2024-01-01'
    GROUP BY customer_id
    HAVING SUM(order_value) > 10000
)
SELECT
    c.customer_name,
    hvc.total_spent,
    c.loyalty_tier
FROM high_value_customers hvc
JOIN customers c ON hvc.customer_id = c.customer_id;

-- CTE Recursiva: Hierarquias organizacionais
WITH RECURSIVE employee_hierarchy AS (
    -- Caso base: CEOs (sem manager)
    SELECT
        employee_id,
        employee_name,
        manager_id,
        1 as level,
        CAST(employee_name AS VARCHAR(1000)) as path
    FROM employees
    WHERE manager_id IS NULL

    UNION ALL

    -- Caso recursivo
    SELECT
        e.employee_id,
        e.employee_name,
        e.manager_id,
        eh.level + 1,
        eh.path || ' > ' || e.employee_name
    FROM employees e
    INNER JOIN employee_hierarchy eh ON e.manager_id = eh.employee_id
)
SELECT * FROM employee_hierarchy ORDER BY level, path;
```

#### 2.3 Query Optimization

**Conceitos Fundamentais:**

1. **Índices**
   ```sql
   -- B-Tree Index (padrão)
   CREATE INDEX idx_customer_email ON customers(email);

   -- Composite Index
   CREATE INDEX idx_orders_customer_date
   ON orders(customer_id, order_date);

   -- Partial Index
   CREATE INDEX idx_active_users
   ON users(email)
   WHERE is_active = true;

   -- Covering Index
   CREATE INDEX idx_orders_covering
   ON orders(customer_id, order_date)
   INCLUDE (order_value, status);
   ```

2. **EXPLAIN ANALYZE**
   ```sql
   EXPLAIN ANALYZE
   SELECT c.customer_name, COUNT(*) as order_count
   FROM customers c
   JOIN orders o ON c.customer_id = o.customer_id
   WHERE o.order_date >= '2024-01-01'
   GROUP BY c.customer_id, c.customer_name;
   ```

   **Como ler:**
   - Seq Scan: Lê tabela inteira (ruim para tabelas grandes)
   - Index Scan: Usa índice (geralmente bom)
   - Bitmap Heap Scan: Usa índice + heap (ótimo para múltiplas condições)
   - Hash Join vs Nested Loop vs Merge Join
   - Cost: Estimativa do banco (não é tempo real)
   - Actual Time: Tempo real de execução

3. **Query Rewrite Patterns**
   ```sql
   -- L RUIM: Função na coluna indexada
   SELECT * FROM users WHERE YEAR(created_at) = 2024;

   --  BOM: Permite uso de índice
   SELECT * FROM users
   WHERE created_at >= '2024-01-01'
   AND created_at < '2025-01-01';

   -- L RUIM: OR com diferentes colunas
   SELECT * FROM products
   WHERE category = 'electronics' OR brand = 'Samsung';

   --  BOM: UNION com índices separados
   SELECT * FROM products WHERE category = 'electronics'
   UNION
   SELECT * FROM products WHERE brand = 'Samsung';

   -- L RUIM: NOT IN com subquery
   SELECT * FROM customers
   WHERE customer_id NOT IN (
       SELECT customer_id FROM orders
   );

   --  BOM: LEFT JOIN com NULL check
   SELECT c.* FROM customers c
   LEFT JOIN orders o ON c.customer_id = o.customer_id
   WHERE o.customer_id IS NULL;
   ```

=Ö **Material:** [teoria/sql-avancado.md](./teoria/sql-avancado.md)
=» **Exercícios:** [exercicios/sql-challenges.md](./exercicios/sql-challenges.md)

---

### 3. Python para Engenharia de Dados

#### 3.1 Bibliotecas Essenciais

**Pandas Avançado:**
```python
import pandas as pd
import numpy as np

# Leitura eficiente
df = pd.read_csv(
    'large_file.csv',
    usecols=['col1', 'col2', 'col3'],  # Lê apenas colunas necessárias
    dtype={'col1': 'category'},  # Otimiza uso de memória
    parse_dates=['date_col'],
    chunksize=10000  # Processa em chunks
)

# Method chaining para código limpo
result = (
    df
    .query('revenue > 1000')
    .assign(
        profit=lambda x: x['revenue'] - x['cost'],
        profit_margin=lambda x: x['profit'] / x['revenue']
    )
    .groupby('category')
    .agg({
        'revenue': ['sum', 'mean'],
        'profit': 'sum'
    })
    .reset_index()
)

# Operações vetorizadas (muito mais rápidas que loops)
# L RUIM: Loop
for idx, row in df.iterrows():
    df.at[idx, 'new_col'] = row['col1'] * row['col2']

#  BOM: Vetorizado
df['new_col'] = df['col1'] * df['col2']

# Window operations
df['moving_avg'] = df.groupby('customer_id')['amount'].transform(
    lambda x: x.rolling(window=7).mean()
)
```

**Polars: A alternativa moderna ao Pandas**
```python
import polars as pl

# Lazy evaluation para otimização automática
df = (
    pl.scan_csv('large_file.csv')
    .filter(pl.col('revenue') > 1000)
    .with_columns([
        (pl.col('revenue') - pl.col('cost')).alias('profit'),
        (pl.col('profit') / pl.col('revenue')).alias('profit_margin')
    ])
    .groupby('category')
    .agg([
        pl.col('revenue').sum().alias('total_revenue'),
        pl.col('profit').sum().alias('total_profit')
    ])
    .collect()  # Executa toda a query otimizada
)
```

#### 3.2 Async Python para I/O

```python
import asyncio
import aiohttp
import aiobotocore

# Requisições HTTP paralelas
async def fetch_data(session, url):
    async with session.get(url) as response:
        return await response.json()

async def fetch_all_data(urls):
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_data(session, url) for url in urls]
        results = await asyncio.gather(*tasks)
        return results

# Uso
urls = ['http://api.com/1', 'http://api.com/2', ...]
results = asyncio.run(fetch_all_data(urls))

# S3 async
async def upload_to_s3(bucket, key, data):
    session = aiobotocore.get_session()
    async with session.create_client('s3') as client:
        await client.put_object(
            Bucket=bucket,
            Key=key,
            Body=data
        )
```

#### 3.3 Data Classes e Type Hints

```python
from dataclasses import dataclass
from typing import List, Dict, Optional
from datetime import datetime
from enum import Enum

class OrderStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"

@dataclass
class Order:
    order_id: str
    customer_id: str
    items: List[Dict[str, any]]
    total_amount: float
    status: OrderStatus
    created_at: datetime
    shipped_at: Optional[datetime] = None

    def calculate_tax(self, rate: float) -> float:
        return self.total_amount * rate

    @property
    def is_completed(self) -> bool:
        return self.status == OrderStatus.DELIVERED

# Type hints para documentação e validação
def process_orders(
    orders: List[Order],
    min_amount: float
) -> Dict[str, float]:
    """
    Processa lista de pedidos e retorna estatísticas.

    Args:
        orders: Lista de objetos Order
        min_amount: Valor mínimo para considerar

    Returns:
        Dicionário com estatísticas calculadas
    """
    filtered = [o for o in orders if o.total_amount >= min_amount]
    return {
        'total_revenue': sum(o.total_amount for o in filtered),
        'avg_order_value': sum(o.total_amount for o in filtered) / len(filtered)
    }
```

=Ö **Material:** [teoria/python-data-engineering.md](./teoria/python-data-engineering.md)
=» **Exercícios:** [exercicios/python-challenges.py](./exercicios/python-challenges.py)

---

### 4. Estruturas de Dados para Big Data

#### 4.1 Hash Tables e Partitioning

**Conceito:** Base para particionamento distribuído

```python
def hash_partition(key: str, num_partitions: int) -> int:
    """Distribui chaves uniformemente entre partições"""
    return hash(key) % num_partitions

# Exemplo: Distribuir 1M de user_ids em 100 partições
user_ids = range(1000000)
partition_counts = {}

for user_id in user_ids:
    partition = hash_partition(str(user_id), 100)
    partition_counts[partition] = partition_counts.get(partition, 0) + 1

# Verificar distribuição uniforme
print(f"Min: {min(partition_counts.values())}")
print(f"Max: {max(partition_counts.values())}")
print(f"Avg: {sum(partition_counts.values()) / len(partition_counts)}")
```

**Aplicações em Big Data:**
- Kafka partitioning
- Spark shuffle
- Database sharding
- Distributed caching

#### 4.2 Bloom Filters

**Conceito:** Estrutura probabilística para teste de pertencimento

```python
from bitarray import bitarray
import mmh3

class BloomFilter:
    def __init__(self, size: int, hash_count: int):
        self.size = size
        self.hash_count = hash_count
        self.bit_array = bitarray(size)
        self.bit_array.setall(0)

    def add(self, item: str):
        for i in range(self.hash_count):
            digest = mmh3.hash(item, i) % self.size
            self.bit_array[digest] = 1

    def check(self, item: str) -> bool:
        for i in range(self.hash_count):
            digest = mmh3.hash(item, i) % self.size
            if self.bit_array[digest] == 0:
                return False
        return True  # Pode ser falso positivo

# Uso: Verificar se email já existe antes de query no DB
bf = BloomFilter(size=1000000, hash_count=5)
bf.add("user@example.com")

if bf.check("newuser@example.com"):
    # Pode existir, fazer query no DB
    result = db.query("SELECT * FROM users WHERE email = ?")
else:
    # Definitivamente não existe, pular query
    result = None
```

**Aplicações:**
- Cache negativo (evitar queries desnecessárias)
- Deduplicação em streaming
- Verificação rápida de existência

#### 4.3 HyperLogLog

**Conceito:** Contagem aproximada de elementos únicos com espaço constante

```python
# Exemplo com biblioteca
from hyperloglog import HyperLogLog

hll = HyperLogLog(0.01)  # 1% de erro

# Adicionar 1 milhão de elementos únicos
for i in range(1000000):
    hll.add(str(i))

print(f"Estimativa: {len(hll)}")  # ~1000000
print(f"Memória usada: {hll.__sizeof__()} bytes")  # Muito menor que armazenar todos os IDs
```

**Aplicações:**
- Contar usuários únicos em escala
- Distinct count em streaming
- Análises aproximadas em tempo real

#### 4.4 Skip Lists

**Conceito:** Alternativa probabilística a árvores balanceadas

```python
import random

class SkipListNode:
    def __init__(self, value, level):
        self.value = value
        self.forward = [None] * (level + 1)

class SkipList:
    def __init__(self, max_level=16, p=0.5):
        self.max_level = max_level
        self.p = p
        self.header = SkipListNode(float('-inf'), max_level)
        self.level = 0

    def random_level(self):
        level = 0
        while random.random() < self.p and level < self.max_level:
            level += 1
        return level

    def search(self, target):
        current = self.header
        for i in range(self.level, -1, -1):
            while current.forward[i] and current.forward[i].value < target:
                current = current.forward[i]

        current = current.forward[0]
        return current and current.value == target
```

**Aplicações:**
- LSM Trees (RocksDB, LevelDB)
- Redis Sorted Sets
- Range queries eficientes

=Ö **Material:** [teoria/estruturas-dados-bigdata.md](./teoria/estruturas-dados-bigdata.md)
=» **Exercícios:** [exercicios/data-structures.py](./exercicios/data-structures.py)

---

### 5. Docker e Containerização

#### 5.1 Dockerfile para Data Engineering

```dockerfile
FROM python:3.11-slim

# Evitar prompts interativos
ENV DEBIAN_FRONTEND=noninteractive

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Criar usuário não-root
RUN useradd -m -u 1000 dataeng
WORKDIR /app
RUN chown dataeng:dataeng /app

# Copiar requirements e instalar dependências Python
COPY --chown=dataeng:dataeng requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código
COPY --chown=dataeng:dataeng . .

# Mudar para usuário não-root
USER dataeng

# Healthcheck
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python healthcheck.py

CMD ["python", "main.py"]
```

#### 5.2 Docker Compose para Stack Local

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_USER: dataeng
      POSTGRES_PASSWORD: dataeng
      POSTGRES_DB: datawarehouse
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U dataeng"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  kafka:
    image: confluentinc/cp-kafka:7.5.0
    depends_on:
      - zookeeper
    ports:
      - "9092:9092"
    environment:
      KAFKA_BROKER_ID: 1
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://localhost:9092
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1

  zookeeper:
    image: confluentinc/cp-zookeeper:7.5.0
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181
      ZOOKEEPER_TICK_TIME: 2000

  airflow:
    image: apache/airflow:2.7.0
    depends_on:
      - postgres
      - redis
    environment:
      AIRFLOW__CORE__EXECUTOR: CeleryExecutor
      AIRFLOW__DATABASE__SQL_ALCHEMY_CONN: postgresql+psycopg2://dataeng:dataeng@postgres/airflow
      AIRFLOW__CELERY__BROKER_URL: redis://redis:6379/0
      AIRFLOW__CELERY__RESULT_BACKEND: db+postgresql://dataeng:dataeng@postgres/airflow
    volumes:
      - ./dags:/opt/airflow/dags
      - ./logs:/opt/airflow/logs
      - ./plugins:/opt/airflow/plugins
    ports:
      - "8080:8080"

volumes:
  postgres_data:
  redis_data:
```

=Ö **Material:** [teoria/docker-containerization.md](./teoria/docker-containerization.md)
=» **Exercícios:** [exercicios/docker-exercises/](./exercicios/docker-exercises/)

---

### 6. Git e Controle de Versão

#### 6.1 Git Workflows para Data Engineering

**Git Flow para projetos de dados:**
```bash
# Feature branches
git checkout -b feature/add-customer-pipeline main
# Desenvolver
git commit -m "feat: add customer data ingestion"
git commit -m "feat: add customer transformations"
git push origin feature/add-customer-pipeline
# Criar PR para main

# Hotfix
git checkout -b hotfix/fix-null-handling main
git commit -m "fix: handle null values in revenue calculation"
git push origin hotfix/fix-null-handling
```

**Commits semânticos:**
```bash
feat: nova funcionalidade
fix: correção de bug
refactor: refatoração sem mudança de comportamento
perf: melhoria de performance
docs: documentação
test: testes
chore: tarefas de manutenção
```

#### 6.2 Git para Notebooks Jupyter

```bash
# .gitignore para projetos de dados
*.pyc
__pycache__/
.ipynb_checkpoints/
.env
*.log
data/raw/
data/processed/
models/
venv/
.DS_Store

# Configurar nbstripout para limpar outputs de notebooks
pip install nbstripout
nbstripout --install
```

=Ö **Material:** [teoria/git-version-control.md](./teoria/git-version-control.md)

---

## =» Exercícios Práticos

### Exercício 1: SQL Window Functions Challenge
Implemente queries para:
1. Top 3 produtos por categoria por mês
2. Running total de vendas por dia
3. Calcular diferença percentual vs mês anterior
4. Identificar primeiro e último pedido de cada cliente

=Á [exercicios/ex01-window-functions.sql](./exercicios/ex01-window-functions.sql)

### Exercício 2: Python Data Pipeline
Construa um pipeline que:
1. Lê dados de múltiplas fontes (CSV, JSON, API)
2. Valida e limpa dados
3. Transforma usando pandas/polars
4. Carrega em PostgreSQL
5. Gera relatório de qualidade

=Á [exercicios/ex02-python-pipeline/](./exercicios/ex02-python-pipeline/)

### Exercício 3: Containerização
1. Dockerize o pipeline do exercício 2
2. Crie docker-compose com DB e app
3. Adicione healthchecks
4. Implemente multi-stage build

=Á [exercicios/ex03-docker/](./exercicios/ex03-docker/)

---

## <¯ Projeto Prático: Sistema de Analytics Básico

**Objetivo:** Construir um sistema completo de analytics para e-commerce

**Requisitos:**
1. Ingestão de dados de vendas (CSV/API)
2. Banco PostgreSQL para armazenamento
3. Queries analíticas com SQL avançado
4. Pipeline Python automatizado
5. Containerização completa
6. Documentação e testes

**Métricas a calcular:**
- Revenue diário/mensal
- Top produtos
- Cohort analysis
- Customer lifetime value
- Churn rate

=Á [projeto/ecommerce-analytics/](./projeto/ecommerce-analytics/)

---

## =Ý Assessment Test

Teste seus conhecimentos:
1. 20 questões SQL (window functions, CTEs, optimization)
2. 15 questões Python (pandas, async, type hints)
3. 10 questões de arquitetura
4. 5 exercícios práticos de código

=Á [assessment/test.md](./assessment/test.md)

---

## =Ú Recursos Adicionais

### Livros
- "SQL Performance Explained" - Markus Winand
- "Fluent Python" - Luciano Ramalho
- "High Performance Python" - Micha Gorelick

### Cursos Online
- Mode SQL Tutorial (gratuito)
- Real Python (assinatura)
- DataCamp SQL Track

### Prática
- LeetCode SQL problems
- HackerRank SQL
- SQLZoo

---

##  Checklist de Conclusão

Antes de avançar para o próximo módulo, certifique-se de:
- [ ] Resolver todos os exercícios SQL
- [ ] Completar os exercícios Python
- [ ] Construir o projeto de analytics
- [ ] Passar no assessment test com 80%+
- [ ] Praticar queries de otimização
- [ ] Dominar Docker e docker-compose

---

## = Próximos Passos

Após dominar os fundamentos, você está pronto para:
- **Módulo 2:** Modelagem e Armazenamento de Dados
- Aprender Star Schema, Data Vault, Data Lakes
- Trabalhar com formatos como Parquet, ORC, Delta Lake

**Continue:** [../02-modelagem-dados/README.md](../02-modelagem-dados/README.md)

---

*Última atualização: 2025*
