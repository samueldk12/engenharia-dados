# 🔄 Módulo 4: Orquestração e Workflows

**Duração:** 3-4 semanas | **Nível:** Intermediário

## 📋 Visão Geral

Aprenda a orquestrar pipelines complexos de dados com frameworks modernos.

## 🎯 Objetivos

- ✅ Apache Airflow (DAGs, Operators)
- ✅ Prefect e Dagster
- ✅ CI/CD para pipelines
- ✅ Monitoramento e alertas
- ✅ Best practices de orquestração

## 📚 Conteúdo

### 1. Apache Airflow

**Conceitos:**
- DAG (Directed Acyclic Graph)
- Operators (Bash, Python, SQL, etc)
- Tasks e Dependencies
- Scheduler e Executor

**DAG Example:**
```python
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta

default_args = {
    'owner': 'dataeng',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'etl_pipeline',
    default_args=default_args,
    description='ETL Pipeline',
    schedule_interval='0 2 * * *',  # Daily at 2am
    catchup=False,
    tags=['etl', 'production'],
)

def extract_data(**context):
    # Extract logic
    data = fetch_from_api()
    context['ti'].xcom_push(key='raw_data', value=data)

def transform_data(**context):
    # Transform logic
    raw_data = context['ti'].xcom_pull(key='raw_data')
    transformed = clean_and_process(raw_data)
    return transformed

def load_data(**context):
    # Load logic
    data = context['ti'].xcom_pull(task_ids='transform')
    save_to_database(data)

# Tasks
extract = PythonOperator(
    task_id='extract',
    python_callable=extract_data,
    dag=dag,
)

transform = PythonOperator(
    task_id='transform',
    python_callable=transform_data,
    dag=dag,
)

load = PythonOperator(
    task_id='load',
    python_callable=load_data,
    dag=dag,
)

# Dependencies
extract >> transform >> load
```

**Operators:**
```python
# BashOperator
bash_task = BashOperator(
    task_id='run_script',
    bash_command='python /path/to/script.py',
)

# SQLOperator
from airflow.providers.postgres.operators.postgres import PostgresOperator

sql_task = PostgresOperator(
    task_id='insert_data',
    postgres_conn_id='postgres_default',
    sql="""
        INSERT INTO table SELECT * FROM staging;
    """,
)

# SparkSubmitOperator
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator

spark_task = SparkSubmitOperator(
    task_id='spark_job',
    application='/path/to/app.py',
    conn_id='spark_default',
    conf={'spark.executor.memory': '4g'},
)
```

### 2. Prefect

**Flow Example:**
```python
from prefect import flow, task
from prefect.deployments import Deployment
from prefect.server.schemas.schedules import CronSchedule

@task(retries=3, retry_delay_seconds=60)
def extract():
    return fetch_data()

@task
def transform(data):
    return clean_data(data)

@task
def load(data):
    save_data(data)

@flow(name="etl-pipeline")
def etl_flow():
    data = extract()
    clean_data = transform(data)
    load(clean_data)

# Deploy
deployment = Deployment.build_from_flow(
    flow=etl_flow,
    name="production",
    schedule=CronSchedule(cron="0 2 * * *"),
    work_queue_name="default",
)
deployment.apply()
```

### 3. Dagster

**Asset-based Approach:**
```python
from dagster import asset, Definitions, ScheduleDefinition

@asset
def raw_sales():
    return read_from_source()

@asset
def clean_sales(raw_sales):
    return clean_data(raw_sales)

@asset
def sales_report(clean_sales):
    return generate_report(clean_sales)

# Schedule
daily_schedule = ScheduleDefinition(
    job=define_asset_job("all_assets"),
    cron_schedule="0 2 * * *",
)

defs = Definitions(
    assets=[raw_sales, clean_sales, sales_report],
    schedules=[daily_schedule],
)
```

### 4. CI/CD para Pipelines

**GitHub Actions:**
```yaml
name: Deploy Airflow DAG

on:
  push:
    branches: [main]
    paths: ['dags/**']

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
      
      - name: Lint DAGs
        run: |
          python -m pytest tests/test_dags.py
      
      - name: Validate DAG syntax
        run: |
          python -c "from airflow.models import DagBag; DagBag('dags/')"
  
  deploy:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to Airflow
        run: |
          rsync -avz dags/ airflow@server:/opt/airflow/dags/
```

### 5. Monitoramento

**Métricas importantes:**
- Task success rate
- Duration (p50, p95, p99)
- Failure rate
- SLA misses

**Alerting:**
```python
# Airflow: Email on failure
default_args = {
    'email_on_failure': True,
    'email': ['team@example.com'],
}

# Airflow: Slack callback
from airflow.providers.slack.operators.slack_webhook import SlackWebhookOperator

def task_fail_slack_alert(context):
    slack_msg = f"""
    :red_circle: Task Failed
    *Task*: {context.get('task_instance').task_id}
    *Dag*: {context.get('task_instance').dag_id}
    *Execution Time*: {context.get('execution_date')}
    *Log*: {context.get('task_instance').log_url}
    """
    
    failed_alert = SlackWebhookOperator(
        task_id='slack_alert',
        webhook_token='YOUR_TOKEN',
        message=slack_msg,
    )
    return failed_alert.execute(context=context)

# Use in DAG
task = PythonOperator(
    task_id='my_task',
    python_callable=my_function,
    on_failure_callback=task_fail_slack_alert,
)
```

## 🎯 Exercícios

### Exercício 1: DAG Complexo
Criar pipeline com 10+ tasks e dependências

### Exercício 2: Error Handling
Implementar retry logic e fallbacks

### Exercício 3: CI/CD
Automatizar deploy de DAGs com testes

## 📖 Recursos

- **Docs**: Apache Airflow Documentation
- **Curso**: Astronomer Certification
- **Livro**: "Data Pipelines with Apache Airflow"

## ✅ Checklist

- [ ] Escrevo DAGs do Airflow
- [ ] Uso Operators apropriados
- [ ] Implemento error handling
- [ ] Monitoro pipelines
- [ ] Deploys automatizados

## 🚀 Próximos Passos

➡️ **[Módulo 5: Streaming e Real-time](../05-streaming-real-time/)**
