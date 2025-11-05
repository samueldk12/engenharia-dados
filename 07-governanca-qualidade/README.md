# 🛡️ Módulo 7: Governança e Qualidade de Dados

**Duração:** 3-4 semanas | **Nível:** Intermediário-Avançado

## 📋 Visão Geral

Implemente governança, qualidade e segurança de dados em escala.

## 🎯 Objetivos

- ✅ Data Quality frameworks
- ✅ Data Lineage
- ✅ Data Cataloging
- ✅ Security e Compliance
- ✅ Observability

## 📚 Conteúdo

### 1. Data Quality

**Great Expectations:**
```python
import great_expectations as ge

df = ge.read_csv('data.csv')

# Expectations
df.expect_column_values_to_not_be_null('user_id')
df.expect_column_values_to_be_unique('email')
df.expect_column_values_to_be_between('age', 0, 120)
df.expect_column_values_to_match_regex('email', r'^[\w\.-]+@[\w\.-]+\.\w+$')

# Validate
results = df.validate()
```

### 2. Data Lineage

- End-to-end tracking
- Impact analysis
- Data discovery

**Tools:**
- Apache Atlas
- Marquez
- OpenLineage

### 3. Data Catalog

**AWS Glue Catalog:**
- Metadata repository
- Schema versioning
- Search and discovery

### 4. Security

- Encryption (at rest, in transit)
- Access control (IAM, RBAC)
- Data masking
- Audit logs

## ✅ Checklist

- [ ] Implemento data quality checks
- [ ] Rastreio lineage
- [ ] Uso data catalogs
- [ ] Aplico segurança adequada

## 🚀 Próximos Passos

➡️ **[Módulo 8: Preparação para Entrevistas](../08-preparacao-entrevistas/)**
