#  Módulo 7: Data Quality e Governança

## =Ë Visão Geral

Data Quality é crítico para decisões de negócio. Dados ruins custam milhões e destroem confiança. Este módulo cobre frameworks, ferramentas e práticas para garantir qualidade e governança de dados em escala.

**Duração:** 3-4 semanas | **Nível:** Intermediário-Avançado

---

## <¯ Objetivos

-  Implementar data quality checks automatizados
-  Trabalhar com Great Expectations e dbt tests
-  Configurar data catalogs e lineage
-  Implementar data observability
-  Garantir compliance (GDPR, LGPD)
-  Criar SLAs e SLOs para dados

---

## =Ú Conteúdo

### 1. Fundamentos de Data Quality

#### 1.1 Dimensões de Qualidade

**6 Dimensões Críticas:**

1. **Accuracy (Precisão)**
   - Dados refletem a realidade?
   - Exemplo: Email válido, CPF correto

2. **Completeness (Completude)**
   - Todos os dados estão presentes?
   - Exemplo: % de nulls aceitável

3. **Consistency (Consistência)**
   - Dados são consistentes entre sistemas?
   - Exemplo: Mesmo cliente, mesmo ID

4. **Timeliness (Atualidade)**
   - Dados são frescos?
   - Exemplo: SLA de 2 horas

5. **Validity (Validade)**
   - Dados seguem regras de negócio?
   - Exemplo: Data no futuro = inválido

6. **Uniqueness (Unicidade)**
   - Sem duplicatas?
   - Exemplo: Email único por usuário

#### 1.2 Tipos de Checks

```python
# Exemplo conceitual de checks

class DataQualityChecks:
    """Suite de checks de qualidade"""

    # 1. SCHEMA CHECKS
    def check_schema(self, df, expected_schema):
        """Valida schema (colunas, tipos)"""
        assert set(df.columns) == set(expected_schema.keys())
        for col, dtype in expected_schema.items():
            assert df[col].dtype == dtype

    # 2. NULL CHECKS
    def check_null_rate(self, df, column, max_null_rate=0.05):
        """Valida taxa de nulls"""
        null_rate = df[column].isna().sum() / len(df)
        assert null_rate <= max_null_rate, f"Null rate {null_rate} > {max_null_rate}"

    # 3. RANGE CHECKS
    def check_range(self, df, column, min_val, max_val):
        """Valida valores dentro de range"""
        invalid = df[(df[column] < min_val) | (df[column] > max_val)]
        assert len(invalid) == 0, f"Found {len(invalid)} values out of range"

    # 4. UNIQUENESS CHECKS
    def check_uniqueness(self, df, columns):
        """Valida unicidade"""
        duplicates = df[df.duplicated(subset=columns, keep=False)]
        assert len(duplicates) == 0, f"Found {len(duplicates)} duplicates"

    # 5. REFERENTIAL INTEGRITY
    def check_foreign_key(self, df, column, reference_df, reference_column):
        """Valida foreign key"""
        orphans = ~df[column].isin(reference_df[reference_column])
        assert orphans.sum() == 0, f"Found {orphans.sum()} orphan records"

    # 6. BUSINESS RULES
    def check_business_rule(self, df, rule_function):
        """Valida regra de negócio customizada"""
        violations = df[~df.apply(rule_function, axis=1)]
        assert len(violations) == 0, f"Found {len(violations)} violations"
```

---

### 2. Great Expectations

**Great Expectations** é o framework mais popular para data quality em Python.

#### 2.1 Setup e Configuração

```python
import great_expectations as ge
from great_expectations.data_context import DataContext

# Inicializar Great Expectations
context = DataContext()

# Criar Expectation Suite
suite = context.create_expectation_suite(
    expectation_suite_name="sales_data_suite",
    overwrite_existing=True
)
```

#### 2.2 Expectation Examples

```python
import pandas as pd
import great_expectations as ge

# Carregar dados
df = ge.from_pandas(pd.read_csv("sales.csv"))

# 1. SCHEMA EXPECTATIONS
df.expect_table_columns_to_match_ordered_list([
    "sale_id", "customer_id", "product_id", "amount", "sale_date"
])

df.expect_column_values_to_be_of_type("sale_id", "int64")
df.expect_column_values_to_be_of_type("amount", "float64")

# 2. NULL EXPECTATIONS
df.expect_column_values_to_not_be_null("sale_id")
df.expect_column_values_to_not_be_null("customer_id")

# Permitir alguns nulls
df.expect_column_values_to_not_be_null(
    "discount_code",
    mostly=0.7  # 70% não-null é aceitável
)

# 3. RANGE EXPECTATIONS
df.expect_column_values_to_be_between(
    "amount",
    min_value=0,
    max_value=100000,
    mostly=0.99  # 99% dos valores
)

df.expect_column_values_to_be_between(
    "sale_date",
    min_value="2020-01-01",
    max_value="2025-12-31"
)

# 4. SET MEMBERSHIP
df.expect_column_values_to_be_in_set(
    "status",
    ["pending", "completed", "cancelled", "refunded"]
)

df.expect_column_distinct_values_to_be_in_set(
    "country",
    ["USA", "Brazil", "UK", "Germany", "France"]
)

# 5. UNIQUENESS
df.expect_column_values_to_be_unique("sale_id")
df.expect_compound_columns_to_be_unique(["customer_id", "sale_date"])

# 6. STATISTICAL EXPECTATIONS
df.expect_column_mean_to_be_between("amount", min_value=50, max_value=500)
df.expect_column_median_to_be_between("amount", min_value=100, max_value=300)
df.expect_column_stdev_to_be_between("amount", min_value=10, max_value=1000)

# 7. REGEX PATTERNS
df.expect_column_values_to_match_regex(
    "email",
    regex=r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
)

df.expect_column_values_to_match_regex(
    "phone",
    regex=r'^\+?1?\d{9,15}$'
)

# 8. CUSTOM EXPECTATIONS
df.expect_column_values_to_match_regex_list(
    "product_id",
    regex_list=[r'^PROD-\d{6}$']  # Formato: PROD-123456
)

# 9. FRESHNESS
from datetime import datetime, timedelta

df.expect_column_max_to_be_between(
    "sale_date",
    min_value=(datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d"),
    max_value=datetime.now().strftime("%Y-%m-%d")
)

# 10. AGGREGATE CHECKS
df.expect_table_row_count_to_be_between(min_value=1000, max_value=1000000)

df.expect_column_proportion_of_unique_values_to_be_between(
    "customer_id",
    min_value=0.8,  # Pelo menos 80% únicos
    max_value=1.0
)

# Validar todas as expectations
results = df.validate()

if results['success']:
    print(" All checks passed!")
else:
    print("L Some checks failed:")
    for result in results['results']:
        if not result['success']:
            print(f"  - {result['expectation_config']['expectation_type']}")
            print(f"    Column: {result['expectation_config'].get('kwargs', {}).get('column')}")
```

#### 2.3 Checkpoint e Validação Automática

```python
# checkpoint.yaml
"""
name: sales_checkpoint
config_version: 1.0
class_name: SimpleCheckpoint
run_name_template: "%Y%m%d-%H%M%S-sales-validation"

validations:
  - batch_request:
      datasource_name: my_datasource
      data_connector_name: default_inferred_data_connector_name
      data_asset_name: sales
    expectation_suite_name: sales_data_suite

action_list:
  - name: store_validation_result
    action:
      class_name: StoreValidationResultAction
  - name: update_data_docs
    action:
      class_name: UpdateDataDocsAction
  - name: send_slack_notification_on_failure
    action:
      class_name: SlackNotificationAction
      slack_webhook: ${SLACK_WEBHOOK}
      notify_on: failure
"""

# Executar checkpoint
result = context.run_checkpoint(
    checkpoint_name="sales_checkpoint",
    batch_request={
        "datasource_name": "my_datasource",
        "data_asset_name": "sales",
        "options": {
            "path": "s3://bucket/data/sales/2024-01-15.parquet"
        }
    }
)

if not result["success"]:
    raise Exception("Data quality validation failed!")
```

#### 2.4 Integração com Airflow

```python
from airflow import DAG
from airflow.operators.python import PythonOperator
from great_expectations_provider.operators.great_expectations import GreatExpectationsOperator

def validate_data_quality(**context):
    """Task de validação de qualidade"""
    import great_expectations as ge

    context_ge = ge.data_context.DataContext()

    result = context_ge.run_checkpoint(
        checkpoint_name="sales_checkpoint",
        batch_request={...}
    )

    if not result["success"]:
        # Enviar alerta
        send_alert("Data quality validation failed!")
        raise Exception("Validation failed")

with DAG('sales_etl_with_quality', ...) as dag:

    extract = PythonOperator(...)

    # Great Expectations operator
    validate_data = GreatExpectationsOperator(
        task_id='validate_data',
        data_context_root_dir='/path/to/great_expectations',
        checkpoint_name='sales_checkpoint',
        fail_task_on_validation_failure=True
    )

    transform = PythonOperator(...)
    load = PythonOperator(...)

    extract >> validate_data >> transform >> load
```

---

### 3. dbt Tests

**dbt** (data build tool) é essencial para analytics engineering e inclui testes nativos.

#### 3.1 dbt Built-in Tests

```yaml
# models/schema.yml
version: 2

models:
  - name: fact_sales
    description: "Tabela fato de vendas"
    columns:
      - name: sale_id
        description: "ID único da venda"
        tests:
          - unique
          - not_null

      - name: customer_id
        description: "ID do cliente"
        tests:
          - not_null
          - relationships:
              to: ref('dim_customer')
              field: customer_id

      - name: product_id
        tests:
          - not_null
          - relationships:
              to: ref('dim_product')
              field: product_id

      - name: amount
        tests:
          - not_null
          - dbt_utils.expression_is_true:
              expression: ">= 0"

      - name: sale_date
        tests:
          - not_null
          - dbt_utils.expression_is_true:
              expression: ">= '2020-01-01'"

      - name: status
        tests:
          - not_null
          - accepted_values:
              values: ['pending', 'completed', 'cancelled', 'refunded']
```

#### 3.2 Custom dbt Tests

```sql
-- tests/assert_positive_revenue.sql
-- Testa se receita diária é sempre positiva

SELECT
    sale_date,
    SUM(amount) as daily_revenue
FROM {{ ref('fact_sales') }}
WHERE status = 'completed'
GROUP BY sale_date
HAVING SUM(amount) <= 0
```

```sql
-- tests/assert_no_future_dates.sql
-- Testa se não há datas no futuro

SELECT *
FROM {{ ref('fact_sales') }}
WHERE sale_date > CURRENT_DATE
```

```sql
-- tests/assert_referential_integrity.sql
-- Testa integridade referencial manualmente

SELECT
    fs.customer_id
FROM {{ ref('fact_sales') }} fs
LEFT JOIN {{ ref('dim_customer') }} dc
    ON fs.customer_id = dc.customer_id
WHERE dc.customer_id IS NULL
```

#### 3.3 dbt Test Macros

```sql
-- macros/test_recency.sql
{% macro test_recency(model, field, max_age_days=1) %}

SELECT COUNT(*) as stale_records
FROM {{ model }}
WHERE {{ field }} < CURRENT_DATE - INTERVAL '{{ max_age_days }} days'

{% endmacro %}
```

Uso:
```yaml
models:
  - name: fact_sales
    tests:
      - test_recency:
          field: sale_date
          max_age_days: 2
```

---

### 4. Data Catalogs

#### 4.1 Apache Atlas

```python
from apache_atlas.client.base_client import AtlasClient
from apache_atlas.model.instance import AtlasEntity

# Conectar ao Atlas
client = AtlasClient('http://atlas-server:21000', ('admin', 'admin'))

# Criar entidade de dataset
dataset_entity = AtlasEntity(
    typeName='hive_table',
    attributes={
        'qualifiedName': 'sales@prod',
        'name': 'sales',
        'description': 'Tabela de vendas',
        'owner': 'data-engineering-team',
        'createTime': 1609459200000,
        'columns': [
            {
                'name': 'sale_id',
                'type': 'bigint',
                'description': 'ID único da venda'
            },
            {
                'name': 'customer_id',
                'type': 'bigint',
                'description': 'ID do cliente'
            }
        ],
        'tags': ['pii', 'prod', 'critical']
    }
)

# Criar no Atlas
client.entity.create_entity(dataset_entity)
```

#### 4.2 DataHub (LinkedIn)

```python
from datahub.emitter.mce_builder import make_data_platform_urn, make_dataset_urn
from datahub.emitter.mcp import MetadataChangeProposalWrapper
from datahub.emitter.rest_emitter import DatahubRestEmitter
from datahub.metadata.schema_classes import (
    DatasetPropertiesClass,
    OwnerClass,
    OwnershipClass,
    OwnershipTypeClass
)

# Configurar emitter
emitter = DatahubRestEmitter("http://datahub-gms:8080")

# Dataset URN
dataset_urn = make_dataset_urn(
    platform="snowflake",
    name="prod.analytics.fact_sales"
)

# Metadata: Properties
properties = DatasetPropertiesClass(
    description="Tabela fato de vendas - source of truth para revenue",
    customProperties={
        "refresh_frequency": "hourly",
        "data_classification": "confidential",
        "retention_days": "730",
        "owner_team": "data-engineering"
    }
)

# Metadata: Ownership
ownership = OwnershipClass(
    owners=[
        OwnerClass(
            owner="urn:li:corpuser:john.doe",
            type=OwnershipTypeClass.DATAOWNER
        )
    ]
)

# Emitir metadata
for metadata in [properties, ownership]:
    mcp = MetadataChangeProposalWrapper(
        entityType="dataset",
        entityUrn=dataset_urn,
        aspectName=metadata.__class__.__name__,
        aspect=metadata,
    )
    emitter.emit_mcp(mcp)

print(f" Metadata emitted for {dataset_urn}")
```

---

### 5. Data Lineage

#### 5.1 OpenLineage

```python
from openlineage.client import OpenLineageClient
from openlineage.client.run import RunEvent, RunState, Run, Job
from openlineage.client.facet import (
    SqlJobFacet,
    SourceCodeLocationJobFacet,
    NominalTimeRunFacet
)

# Cliente OpenLineage
client = OpenLineageClient(url="http://marquez:5000")

# Definir Job
job = Job(
    namespace="prod",
    name="sales_aggregation",
    facets={
        "sql": SqlJobFacet(
            query="""
                INSERT INTO sales_summary
                SELECT date, SUM(amount) as revenue
                FROM sales
                GROUP BY date
            """
        ),
        "sourceCodeLocation": SourceCodeLocationJobFacet(
            type="git",
            url="https://github.com/company/data-pipelines",
            repoUrl="https://github.com/company/data-pipelines",
            path="pipelines/sales_aggregation.py",
            version="main",
            tag="v1.2.3"
        )
    }
)

# Run START
run = Run(
    runId="550e8400-e29b-41d4-a716-446655440000",
    facets={
        "nominalTime": NominalTimeRunFacet(
            nominalStartTime="2024-01-15T10:00:00Z"
        )
    }
)

# Emitir START event
client.emit(
    RunEvent(
        eventType=RunState.START,
        eventTime="2024-01-15T10:00:00.000Z",
        run=run,
        job=job,
        inputs=[...],  # Input datasets
        outputs=[...],  # Output datasets
        producer="airflow"
    )
)

# ... processar ...

# Emitir COMPLETE event
client.emit(
    RunEvent(
        eventType=RunState.COMPLETE,
        eventTime="2024-01-15T10:15:00.000Z",
        run=run,
        job=job,
        inputs=[...],
        outputs=[...],
        producer="airflow"
    )
)
```

#### 5.2 Lineage com dbt

dbt automaticamente gera lineage através do DAG:

```sql
-- models/staging/stg_orders.sql
SELECT * FROM {{ source('raw', 'orders') }}

-- models/marts/fact_sales.sql
SELECT
    o.order_id,
    o.customer_id,
    oi.product_id,
    oi.amount
FROM {{ ref('stg_orders') }} o
JOIN {{ ref('stg_order_items') }} oi
    ON o.order_id = oi.order_id
```

Comando para visualizar:
```bash
dbt docs generate
dbt docs serve
```

Acesse `localhost:8080` para ver lineage interativo.

---

### 6. Data Observability

#### 6.1 Métricas-chave

```python
from dataclasses import dataclass
from datetime import datetime
from typing import Dict

@dataclass
class DatasetMetrics:
    """Métricas de observabilidade de dataset"""

    # Freshness
    last_updated: datetime
    age_minutes: float
    sla_minutes: float
    is_fresh: bool

    # Volume
    row_count: int
    expected_min_rows: int
    expected_max_rows: int
    is_volume_ok: bool

    # Schema
    column_count: int
    expected_columns: list
    actual_columns: list
    schema_changed: bool

    # Quality
    null_rate: Dict[str, float]
    duplicate_rate: float
    quality_score: float  # 0-100

    # Distribution
    mean_values: Dict[str, float]
    std_values: Dict[str, float]
    distribution_shift: bool

def calculate_metrics(df, sla_minutes=120):
    """Calcula métricas de observabilidade"""
    import pandas as pd

    # Freshness
    last_updated = pd.to_datetime(df['updated_at'].max())
    age = (datetime.now() - last_updated).total_seconds() / 60
    is_fresh = age <= sla_minutes

    # Volume
    row_count = len(df)
    is_volume_ok = 1000 <= row_count <= 1000000

    # Null rates
    null_rates = {
        col: df[col].isna().sum() / len(df)
        for col in df.columns
    }

    # Duplicates
    duplicate_rate = df.duplicated().sum() / len(df)

    # Quality score
    quality_score = (
        (1 - sum(null_rates.values()) / len(null_rates)) * 40 +
        (1 - duplicate_rate) * 30 +
        (1 if is_fresh else 0) * 30
    )

    return DatasetMetrics(
        last_updated=last_updated,
        age_minutes=age,
        sla_minutes=sla_minutes,
        is_fresh=is_fresh,
        row_count=row_count,
        expected_min_rows=1000,
        expected_max_rows=1000000,
        is_volume_ok=is_volume_ok,
        column_count=len(df.columns),
        expected_columns=[],
        actual_columns=list(df.columns),
        schema_changed=False,
        null_rate=null_rates,
        duplicate_rate=duplicate_rate,
        quality_score=quality_score,
        mean_values={},
        std_values={},
        distribution_shift=False
    )
```

#### 6.2 Alerting

```python
def check_and_alert(metrics: DatasetMetrics):
    """Verifica métricas e envia alertas"""

    alerts = []

    # Freshness alert
    if not metrics.is_fresh:
        alerts.append({
            'severity': 'HIGH',
            'type': 'FRESHNESS',
            'message': f'Data is {metrics.age_minutes:.0f}min old, SLA is {metrics.sla_minutes}min',
            'dataset': 'sales'
        })

    # Volume alert
    if not metrics.is_volume_ok:
        alerts.append({
            'severity': 'MEDIUM',
            'type': 'VOLUME',
            'message': f'Row count {metrics.row_count} outside expected range',
            'dataset': 'sales'
        })

    # Quality alert
    if metrics.quality_score < 80:
        alerts.append({
            'severity': 'HIGH',
            'type': 'QUALITY',
            'message': f'Quality score {metrics.quality_score:.1f} below threshold',
            'dataset': 'sales'
        })

    # Enviar alertas
    for alert in alerts:
        send_to_slack(alert)
        send_to_pagerduty(alert)

    return alerts
```

---

### 7. Compliance (GDPR, LGPD)

#### 7.1 Data Classification

```python
from enum import Enum

class DataClassification(Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"

class PIIType(Enum):
    NAME = "name"
    EMAIL = "email"
    PHONE = "phone"
    ADDRESS = "address"
    SSN = "ssn"
    CREDIT_CARD = "credit_card"

# Metadata de coluna
column_metadata = {
    'customer_id': {
        'classification': DataClassification.INTERNAL,
        'pii': False,
        'encryption_required': False
    },
    'customer_name': {
        'classification': DataClassification.CONFIDENTIAL,
        'pii': True,
        'pii_type': PIIType.NAME,
        'encryption_required': True,
        'gdpr_subject': True
    },
    'email': {
        'classification': DataClassification.CONFIDENTIAL,
        'pii': True,
        'pii_type': PIIType.EMAIL,
        'encryption_required': True,
        'gdpr_subject': True
    },
    'credit_card': {
        'classification': DataClassification.RESTRICTED,
        'pii': True,
        'pii_type': PIIType.CREDIT_CARD,
        'encryption_required': True,
        'tokenization_required': True,
        'pci_dss': True
    }
}
```

#### 7.2 Data Masking

```python
import hashlib
from typing import Any

def mask_pii(value: Any, pii_type: PIIType) -> str:
    """Mascara dados PII"""

    if value is None:
        return None

    if pii_type == PIIType.EMAIL:
        # email@domain.com -> e***l@domain.com
        parts = str(value).split('@')
        if len(parts) == 2:
            username = parts[0]
            masked = username[0] + '***' + username[-1] if len(username) > 2 else '***'
            return f"{masked}@{parts[1]}"

    elif pii_type == PIIType.PHONE:
        # +1234567890 -> +123***7890
        phone = str(value)
        if len(phone) > 6:
            return phone[:4] + '***' + phone[-4:]

    elif pii_type == PIIType.CREDIT_CARD:
        # 1234567890123456 -> ****...3456
        cc = str(value).replace(' ', '')
        return '****' + cc[-4:]

    elif pii_type == PIIType.NAME:
        # John Doe -> J*** D***
        parts = str(value).split()
        return ' '.join([p[0] + '***' for p in parts])

    # Default: hash
    return hashlib.sha256(str(value).encode()).hexdigest()[:8]

# Uso
masked_df = df.copy()
for col, meta in column_metadata.items():
    if meta.get('pii'):
        masked_df[col] = df[col].apply(
            lambda x: mask_pii(x, meta['pii_type'])
        )
```

#### 7.3 Data Retention Policies

```sql
-- Automatizar deletion baseado em retenção

-- 1. Soft delete (recomendado)
UPDATE users
SET deleted_at = CURRENT_TIMESTAMP,
    is_deleted = TRUE,
    email = NULL,  -- Remover PII
    phone = NULL,
    address = NULL
WHERE user_id = :user_id
  AND gdpr_deletion_requested = TRUE;

-- 2. Anonymização
UPDATE users
SET
    name = 'ANONYMIZED_' || user_id,
    email = user_id || '@anonymized.local',
    phone = NULL,
    address = 'ANONYMIZED'
WHERE last_activity_date < CURRENT_DATE - INTERVAL '2 years'
  AND consent_marketing = FALSE;

-- 3. Hard delete (após período)
DELETE FROM users
WHERE is_deleted = TRUE
  AND deleted_at < CURRENT_DATE - INTERVAL '90 days';
```

---

## =» Exercícios Práticos

### Exercício 1: Great Expectations Suite
Crie suite completa para dataset de e-commerce.

=Á [exercicios/ex01-great-expectations.py](./exercicios/ex01-great-expectations.py)

### Exercício 2: dbt Tests
Implemente testes customizados para data warehouse.

=Á [exercicios/ex02-dbt-tests/](./exercicios/ex02-dbt-tests/)

### Exercício 3: Data Observability Dashboard
Construa dashboard de métricas de qualidade.

=Á [exercicios/ex03-observability-dashboard/](./exercicios/ex03-observability-dashboard/)

---

## <¯ Projeto Prático: Data Quality Platform

**Objetivo:** Plataforma completa de data quality

**Componentes:**
1. Great Expectations para validation
2. Airflow para orchestration
3. PostgreSQL para metrics storage
4. Grafana para dashboards
5. Slack para alerting

=Á [projeto/data-quality-platform/](./projeto/data-quality-platform/)

---

##  Checklist

- [ ] Implementar Great Expectations
- [ ] Criar dbt tests
- [ ] Configurar data catalog
- [ ] Implementar lineage tracking
- [ ] Setup observability
- [ ] Garantir GDPR compliance
- [ ] Criar alerting system

---

## = Próximos Passos

**Módulo 8:** Performance e Otimização

[Ver Módulo 8](../08-performance-otimizacao/README.md)
