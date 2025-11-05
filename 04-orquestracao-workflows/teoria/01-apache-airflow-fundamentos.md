# 🔄 Apache Airflow: Orquestração de Workflows

## 📋 Índice

1. [O que é Apache Airflow](#o-que-é-apache-airflow)
2. [Arquitetura do Airflow](#arquitetura-do-airflow)
3. [DAGs (Directed Acyclic Graphs)](#dags-directed-acyclic-graphs)
4. [Operators](#operators)
5. [Task Dependencies](#task-dependencies)
6. [Scheduling e Backfilling](#scheduling-e-backfilling)
7. [XComs e Task Communication](#xcoms-e-task-communication)
8. [Best Practices](#best-practices)

---

## O que é Apache Airflow

**Apache Airflow** é uma plataforma para criar, agendar e monitorar workflows programaticamente.

### Por que Airflow?

**Antes (Cron Jobs):**
```bash
# crontab
0 2 * * * /scripts/extract.sh
30 2 * * * /scripts/transform.sh  # Espero que extract terminou...
0 3 * * * /scripts/load.sh        # Espero que transform terminou...
```

**Problemas:**
- ❌ Sem dependências explícitas
- ❌ Sem retry automático
- ❌ Sem visualização
- ❌ Difícil de debugar

**Com Airflow:**
```python
extract >> transform >> load  # Dependências claras
# + Retry automático
# + UI para monitoramento
# + Logs centralizados
```

### Conceitos Fundamentais

- **DAG (Directed Acyclic Graph)**: Workflow completo
- **Task**: Uma unidade de trabalho (rodar script, query SQL, etc)
- **Operator**: Template para criar tasks
- **Executor**: Como tasks são executadas (Local, Celery, Kubernetes)
- **Scheduler**: Agenda DAGs baseado no schedule_interval

---

## Arquitetura do Airflow

```
┌──────────────────────────────────────────────────┐
│                Web Server (UI)                   │
│          http://localhost:8080                   │
└─────────────────┬────────────────────────────────┘
                  │
┌─────────────────▼────────────────────────────────┐
│                Metadata Database                 │
│    (PostgreSQL/MySQL - state, logs, etc)        │
└─────────────────▲────────────────────────────────┘
                  │
┌─────────────────┴────────────────────────────────┐
│                  Scheduler                       │
│  (monitora DAGs, agenda tasks, envia p/ queue)  │
└─────────────────┬────────────────────────────────┘
                  │
┌─────────────────▼────────────────────────────────┐
│                  Executor                        │
│           (LocalExecutor/CeleryExecutor)        │
└─────────────────┬────────────────────────────────┘
                  │
         ┌────────┴────────┐
         │                 │
    ┌────▼─────┐     ┌────▼─────┐
    │ Worker 1 │     │ Worker 2 │
    │ (executa │     │ (executa │
    │  tasks)  │     │  tasks)  │
    └──────────┘     └──────────┘
```

### Componentes

**1. Web Server:**
- Interface web para monitorar DAGs
- Ver logs
- Trigger DAGs manualmente
- Gerenciar connections, variables

**2. Scheduler:**
- Monitora pasta `dags/` para novos DAGs
- Agenda tasks baseado em `schedule_interval`
- Envia tasks para executor

**3. Executor:**
- **LocalExecutor**: Executa tasks em processos paralelos (mesmo servidor)
- **CeleryExecutor**: Distribui tasks entre múltiplos workers (escalável)
- **KubernetesExecutor**: Cria pods Kubernetes para cada task

**4. Metadata Database:**
- Armazena estado de DAGs, tasks, logs
- PostgreSQL ou MySQL (não usar SQLite em produção)

---

## DAGs (Directed Acyclic Graphs)

### Estrutura Básica

```python
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta

# Default args aplicados a todas as tasks
default_args = {
    'owner': 'data-eng',
    'depends_on_past': False,
    'email': ['alerts@company.com'],
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
    'execution_timeout': timedelta(hours=2)
}

# Definir DAG
dag = DAG(
    dag_id='etl_pipeline',
    default_args=default_args,
    description='ETL pipeline para processar vendas',
    schedule_interval='0 2 * * *',  # Todo dia às 2am
    start_date=datetime(2024, 1, 1),
    catchup=False,  # Não executar DAGs anteriores
    tags=['etl', 'sales'],
    max_active_runs=1  # Apenas 1 execução por vez
)

# Definir tasks
def extract_data(**context):
    print(f"Extracting data for {context['ds']}")  # ds = execution_date
    # Lógica de extração
    return "extraction_successful"

extract = PythonOperator(
    task_id='extract_data',
    python_callable=extract_data,
    dag=dag
)

transform = BashOperator(
    task_id='transform_data',
    bash_command='python /scripts/transform.py --date {{ ds }}',
    dag=dag
)

load = BashOperator(
    task_id='load_data',
    bash_command='python /scripts/load.py --date {{ ds }}',
    dag=dag
)

# Definir dependências
extract >> transform >> load
```

### Context Variables (Jinja Templates)

```python
# Airflow fornece variáveis de contexto via Jinja2
BashOperator(
    task_id='process',
    bash_command='''
        python script.py \
            --date {{ ds }}                    \
            --date_nodash {{ ds_nodash }}      \
            --yesterday {{ yesterday_ds }}     \
            --execution_date {{ execution_date }} \
            --dag_id {{ dag.dag_id }}          \
            --task_id {{ task.task_id }}
    '''
)

# ds = 2024-01-15
# ds_nodash = 20240115
# yesterday_ds = 2024-01-14
# execution_date = datetime object
```

### Macros Úteis

```python
# Data/hora
{{ ds }}                          # 2024-01-15
{{ ds_nodash }}                   # 20240115
{{ ts }}                          # 2024-01-15T10:30:45+00:00
{{ macros.ds_add(ds, 7) }}       # 2024-01-22 (add 7 days)
{{ macros.ds_format(ds, '%Y-%m-%d', '%Y/%m/%d') }}  # 2024/01/15

# Filesystem
{{ var.value.data_path }}         # Variable do Airflow
{{ conn.my_db.host }}            # Connection do Airflow

# Conditional
{% if execution_date.day == 1 %}
    # Executar apenas no primeiro dia do mês
{% endif %}
```

---

## Operators

### PythonOperator

```python
from airflow.operators.python import PythonOperator

def my_function(param1, param2, **context):
    # Acessar context variables
    execution_date = context['execution_date']
    dag_run = context['dag_run']
    
    print(f"Processing {param1} and {param2}")
    return {"result": "success"}

task = PythonOperator(
    task_id='python_task',
    python_callable=my_function,
    op_args=['value1'],           # Positional args
    op_kwargs={'param2': 'value2'},  # Keyword args
    dag=dag
)
```

### BashOperator

```python
from airflow.operators.bash import BashOperator

# Comando simples
task1 = BashOperator(
    task_id='simple_bash',
    bash_command='echo "Hello from Airflow"',
    dag=dag
)

# Script com argumentos
task2 = BashOperator(
    task_id='run_script',
    bash_command='python /scripts/process.py --date {{ ds }}',
    env={'ENV_VAR': 'production'},  # Environment variables
    dag=dag
)

# Multi-line script
task3 = BashOperator(
    task_id='complex_bash',
    bash_command='''
        set -e  # Falha se qualquer comando falhar
        
        echo "Starting process..."
        python extract.py
        python transform.py
        python load.py
        
        echo "Process completed successfully"
    ''',
    dag=dag
)
```

### SQLOperators

```python
from airflow.providers.postgres.operators.postgres import PostgresOperator
from airflow.providers.mysql.operators.mysql import MySqlOperator

# PostgreSQL
create_table = PostgresOperator(
    task_id='create_table',
    postgres_conn_id='postgres_default',  # Connection configurada no UI
    sql='''
        CREATE TABLE IF NOT EXISTS sales_summary (
            date DATE PRIMARY KEY,
            total_sales DECIMAL(12,2),
            order_count INT
        );
    ''',
    dag=dag
)

# Inserir dados
insert_data = PostgresOperator(
    task_id='insert_data',
    postgres_conn_id='postgres_default',
    sql='''
        INSERT INTO sales_summary (date, total_sales, order_count)
        SELECT 
            '{{ ds }}'::DATE,
            SUM(amount),
            COUNT(*)
        FROM orders
        WHERE order_date = '{{ ds }}'
        ON CONFLICT (date) DO UPDATE
        SET total_sales = EXCLUDED.total_sales,
            order_count = EXCLUDED.order_count;
    ''',
    dag=dag
)

# SQL de arquivo externo
load_from_file = PostgresOperator(
    task_id='load_from_file',
    postgres_conn_id='postgres_default',
    sql='sql/complex_query.sql',  # Arquivo com query
    params={'min_amount': 100},   # Parâmetros: {{ params.min_amount }}
    dag=dag
)
```

### SparkSubmitOperator

```python
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator

spark_job = SparkSubmitOperator(
    task_id='spark_process',
    application='/path/to/spark_job.py',
    conn_id='spark_default',
    conf={
        'spark.executor.memory': '4g',
        'spark.executor.cores': '2'
    },
    application_args=['--date', '{{ ds }}'],
    dag=dag
)
```

### EmailOperator

```python
from airflow.operators.email import EmailOperator

send_alert = EmailOperator(
    task_id='send_email',
    to=['team@company.com'],
    subject='ETL Pipeline Completed - {{ ds }}',
    html_content='''
        <h3>ETL Pipeline Status</h3>
        <p>Date: {{ ds }}</p>
        <p>Status: SUCCESS</p>
    ''',
    dag=dag
)
```

### Sensors

Sensors esperam por uma condição antes de continuar:

```python
from airflow.sensors.filesystem import FileSensor
from airflow.sensors.external_task import ExternalTaskSensor

# Esperar arquivo aparecer
wait_for_file = FileSensor(
    task_id='wait_for_file',
    filepath='/data/input/sales_{{ ds }}.csv',
    poke_interval=60,  # Verifica a cada 60 segundos
    timeout=3600,      # Timeout após 1 hora
    mode='poke',       # 'poke' ou 'reschedule'
    dag=dag
)

# Esperar outra DAG terminar
wait_for_upstream = ExternalTaskSensor(
    task_id='wait_for_upstream_dag',
    external_dag_id='upstream_pipeline',
    external_task_id='final_task',
    execution_delta=timedelta(hours=1),  # Execução 1h antes
    dag=dag
)
```

---

## Task Dependencies

### Dependency Syntax

```python
# Notação clássica (bitshift)
task1 >> task2          # task2 depende de task1
task1 >> [task2, task3] # task2 e task3 dependem de task1
[task1, task2] >> task3 # task3 depende de task1 E task2

# Equivalent: set_downstream / set_upstream
task1.set_downstream(task2)
task2.set_upstream(task1)

# Complex dependencies
task1 >> task2 >> task4
task1 >> task3 >> task4

# É equivalente a:
"""
    task1
   /     \
  v       v
task2   task3
   \     /
    v   v
    task4
"""
```

### Branching (Conditional Logic)

```python
from airflow.operators.python import BranchPythonOperator

def choose_branch(**context):
    execution_date = context['execution_date']
    
    # Lógica condicional
    if execution_date.day == 1:
        return 'monthly_task'  # Task ID
    else:
        return 'daily_task'

branch = BranchPythonOperator(
    task_id='branch_task',
    python_callable=choose_branch,
    dag=dag
)

daily_task = BashOperator(
    task_id='daily_task',
    bash_command='echo "Daily process"',
    dag=dag
)

monthly_task = BashOperator(
    task_id='monthly_task',
    bash_command='echo "Monthly process"',
    dag=dag
)

# Juntar branches
join = BashOperator(
    task_id='join',
    bash_command='echo "Joining"',
    trigger_rule='none_failed_min_one_success',  # Executa se qualquer branch suceder
    dag=dag
)

branch >> [daily_task, monthly_task] >> join
```

### Trigger Rules

```python
# Por padrão: all_success (todos predecessores devem suceder)

task = BashOperator(
    task_id='my_task',
    bash_command='echo "Hello"',
    trigger_rule='all_success',  # Padrão
    dag=dag
)

# Outras opções:
# all_success      - Todos predecessores sucederam (padrão)
# all_failed       - Todos predecessores falharam
# all_done         - Todos terminaram (sucesso ou falha)
# one_success      - Pelo menos 1 sucesso
# one_failed       - Pelo menos 1 falha
# none_failed      - Nenhum falhou (pode ter skipped)
# none_skipped     - Nenhum foi pulado
# none_failed_min_one_success  - Útil após branching

# Exemplo: Cleanup task que SEMPRE executa
cleanup = BashOperator(
    task_id='cleanup',
    bash_command='rm -rf /tmp/airflow_temp',
    trigger_rule='all_done',  # Executa mesmo se pipeline falhou
    dag=dag
)
```

---

## Scheduling e Backfilling

### Schedule Interval

```python
# Cron expression
schedule_interval='0 2 * * *'   # Todo dia às 2am
schedule_interval='*/15 * * * *'  # A cada 15 minutos
schedule_interval='0 0 * * 0'   # Todo domingo à meia-noite

# Macros do Airflow
schedule_interval='@daily'      # 00:00 UTC
schedule_interval='@hourly'     # Toda hora
schedule_interval='@weekly'     # Domingo 00:00
schedule_interval='@monthly'    # Primeiro dia do mês 00:00
schedule_interval='@yearly'     # 1 de Janeiro 00:00

# Timedelta (intervalo)
schedule_interval=timedelta(hours=6)  # A cada 6 horas

# None (manual trigger apenas)
schedule_interval=None
```

### Execution Date vs Logical Date

```python
# IMPORTANTE: execution_date NÃO é quando a DAG rodou!
# execution_date = início do período de dados

# Exemplo: DAG com schedule_interval='@daily'
# Se agendado para 2024-01-15 02:00:
# - execution_date (logical_date) = 2024-01-15 00:00:00
# - Data dos dados = 2024-01-15 (dia inteiro)
# - Execução real = 2024-01-16 00:00:00 (no final do período)

# Processar dados do dia anterior:
yesterday = '{{ yesterday_ds }}'

# Processar dados do dia atual (execution_date):
today = '{{ ds }}'
```

### Catchup

```python
# catchup=True: Executar DAGs passadas desde start_date
dag = DAG(
    dag_id='etl_pipeline',
    start_date=datetime(2024, 1, 1),
    schedule_interval='@daily',
    catchup=True  # Vai executar para TODOS os dias desde 2024-01-01
)

# catchup=False: Apenas próxima execução (recomendado)
dag = DAG(
    dag_id='etl_pipeline',
    start_date=datetime(2024, 1, 1),
    schedule_interval='@daily',
    catchup=False  # Ignora execuções passadas
)
```

### Backfilling Manual

```bash
# Executar DAG para período específico
airflow dags backfill \
    --start-date 2024-01-01 \
    --end-date 2024-01-31 \
    etl_pipeline

# Clear tasks e re-executar
airflow tasks clear \
    --start-date 2024-01-15 \
    --end-date 2024-01-15 \
    etl_pipeline
```

---

## XComs e Task Communication

### XCom (Cross-Communication)

XCom permite tasks compartilharem dados pequenos:

```python
def extract_data(**context):
    data = {'record_count': 1000, 'file_path': '/data/output.csv'}
    
    # Retornar valor -> automaticamente vai para XCom
    return data

def transform_data(**context):
    # Puxar do XCom
    ti = context['ti']  # TaskInstance
    data = ti.xcom_pull(task_ids='extract_data')
    
    print(f"Processing {data['record_count']} records from {data['file_path']}")
    
    # Push manual para XCom
    ti.xcom_push(key='transform_result', value={'status': 'success'})

extract = PythonOperator(
    task_id='extract_data',
    python_callable=extract_data,
    dag=dag
)

transform = PythonOperator(
    task_id='transform_data',
    python_callable=transform_data,
    dag=dag
)

extract >> transform
```

### TaskFlow API (Airflow 2.0+)

Sintaxe mais simples usando decorators:

```python
from airflow.decorators import dag, task
from datetime import datetime

@dag(
    schedule_interval='@daily',
    start_date=datetime(2024, 1, 1),
    catchup=False
)
def etl_pipeline():
    
    @task
    def extract():
        data = {'record_count': 1000}
        return data  # Automaticamente vai para XCom
    
    @task
    def transform(data: dict):
        # data vem do XCom automaticamente
        print(f"Transforming {data['record_count']} records")
        return {'status': 'transformed'}
    
    @task
    def load(data: dict):
        print(f"Loading data: {data}")
    
    # Pipeline
    extracted_data = extract()
    transformed_data = transform(extracted_data)
    load(transformed_data)

# Instanciar DAG
dag = etl_pipeline()
```

---

## Best Practices

### 1. Idempotência

Tasks devem produzir mesmo resultado se executadas múltiplas vezes:

```python
# ❌ Não idempotente
INSERT INTO table VALUES (...)

# ✅ Idempotente
INSERT INTO table VALUES (...)
ON CONFLICT (id) DO UPDATE SET ...

# ✅ Idempotente (delete + insert)
DELETE FROM table WHERE date = '{{ ds }}';
INSERT INTO table SELECT * FROM source WHERE date = '{{ ds }}';
```

### 2. Use Variables e Connections

```python
# ❌ Hardcoded
db_host = 'localhost'
api_key = 'secret123'

# ✅ Use Variables (UI: Admin > Variables)
from airflow.models import Variable
db_host = Variable.get('db_host')
api_key = Variable.get('api_key')  # Masked na UI se contém "password", "secret", etc

# ✅ Use Connections (UI: Admin > Connections)
from airflow.hooks.base import BaseHook
conn = BaseHook.get_connection('my_postgres')
db_url = f"postgresql://{conn.login}:{conn.password}@{conn.host}:{conn.port}/{conn.schema}"
```

### 3. Tamanho de XCom

```python
# ❌ XCom NÃO é para grandes volumes
ti.xcom_push(key='large_data', value=large_dataframe)  # Vai para DB!

# ✅ Use storage externo
# 1. Salvar em S3/GCS
file_path = upload_to_s3(dataframe)
ti.xcom_push(key='file_path', value=file_path)

# 2. Próxima task lê de S3
file_path = ti.xcom_pull(key='file_path')
dataframe = read_from_s3(file_path)
```

### 4. Task Design

```python
# ❌ Uma task monolítica
def do_everything():
    extract()
    transform()
    load()
    validate()
    cleanup()

# ✅ Tasks pequenas e focadas
extract_task >> transform_task >> load_task >> validate_task >> cleanup_task

# Vantagens:
# - Retry apenas task que falhou
# - Paralelização onde possível
# - Logs separados
# - Mais fácil de debugar
```

### 5. Timeouts e SLAs

```python
task = PythonOperator(
    task_id='my_task',
    python_callable=my_function,
    execution_timeout=timedelta(hours=1),  # Task timeout
    sla=timedelta(hours=2),                # SLA - alert se ultrapassar
    dag=dag
)
```

### 6. Testing DAGs

```python
# tests/test_dags.py
import pytest
from airflow.models import DagBag

def test_dag_loaded():
    dagbag = DagBag()
    assert len(dagbag.import_errors) == 0, "DAG import errors"

def test_task_count():
    dagbag = DagBag()
    dag = dagbag.get_dag('etl_pipeline')
    assert len(dag.tasks) == 5

def test_contains_tasks():
    dagbag = DagBag()
    dag = dagbag.get_dag('etl_pipeline')
    tasks = [task.task_id for task in dag.tasks]
    assert 'extract' in tasks
    assert 'transform' in tasks
    assert 'load' in tasks
```

---

## 🎯 Checklist de Produção

- ✅ Use `catchup=False` (na maioria dos casos)
- ✅ Configure `email_on_failure` e `email_on_retry`
- ✅ Defina `retries` e `retry_delay`
- ✅ Use `execution_timeout` para evitar tasks travadas
- ✅ Tasks devem ser idempotentes
- ✅ Não use XCom para dados grandes
- ✅ Use Variables e Connections (não hardcode)
- ✅ Configure metadata database (Postgres/MySQL)
- ✅ Use CeleryExecutor ou KubernetesExecutor em produção
- ✅ Configure SLA alerts para tasks críticas
- ✅ Logs em storage externo (S3/GCS)
- ✅ Teste DAGs em ambiente de dev primeiro

---

## 📚 Referências

- [Airflow Documentation](https://airflow.apache.org/docs/)
- [Airflow Best Practices](https://airflow.apache.org/docs/apache-airflow/stable/best-practices.html)
- [Astronomer Registry](https://registry.astronomer.io/) - Providers e DAG examples

---

**Próximo:** [02-airflow-production-deployment.md](./02-airflow-production-deployment.md)
