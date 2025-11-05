# ☁️ Módulo 6: Cloud e Infraestrutura

**Duração:** 4-5 semanas | **Nível:** Intermediário-Avançado

## 📋 Visão Geral

Domine plataformas cloud (AWS, GCP, Azure) e infraestrutura como código.

## 🎯 Objetivos

- ✅ AWS data services (EMR, Glue, Redshift, Kinesis)
- ✅ GCP data services (BigQuery, Dataflow, Pub/Sub)
- ✅ Azure data services (Databricks, Data Factory, Synapse)
- ✅ Infrastructure as Code (Terraform)
- ✅ Cost optimization

## 📚 Conteúdo

### 1. AWS

**EMR (Elastic MapReduce):**
- Managed Hadoop/Spark
- Auto-scaling clusters
- Transient vs persistent

**Glue:**
- Serverless ETL
- Data Catalog
- Crawlers

**Redshift:**
- MPP Data Warehouse
- Columnar storage
- Distribution styles

**Kinesis:**
- Data Streams
- Data Firehose
- Data Analytics

### 2. GCP

**BigQuery:**
- Serverless DW
- SQL ANSI
- Partitioning/Clustering

**Dataflow:**
- Apache Beam
- Streaming/Batch

**Pub/Sub:**
- Messaging service
- Push/Pull subscriptions

### 3. Azure

**Databricks:**
- Unified analytics
- Delta Lake
- MLflow

**Data Factory:**
- ETL/ELT pipelines
- Integration runtime
- Data flows

**Synapse Analytics:**
- Unified workspace
- SQL pools
- Spark pools

### 4. Terraform

```hcl
# main.tf
provider "aws" {
  region = "us-east-1"
}

resource "aws_s3_bucket" "data_lake" {
  bucket = "my-data-lake"
  
  lifecycle_rule {
    enabled = true
    transition {
      days = 30
      storage_class = "STANDARD_IA"
    }
  }
}

resource "aws_glue_catalog_database" "catalog" {
  name = "data_catalog"
}
```

## ✅ Checklist

- [ ] Uso serviços AWS de dados
- [ ] Trabalho com BigQuery
- [ ] Provisiono infra com Terraform
- [ ] Otimizo custos cloud

## 🚀 Próximos Passos

➡️ **[Módulo 7: Governança e Qualidade](../07-governanca-qualidade/)**
