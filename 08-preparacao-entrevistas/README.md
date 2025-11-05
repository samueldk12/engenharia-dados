# 💼 Módulo 8: Preparação para Entrevistas

**Duração:** 4-6 semanas | **Nível:** Todos os níveis

## 📋 Visão Geral

Prepare-se para entrevistas técnicas e comportamentais em empresas de tecnologia.

## 🎯 Objetivos

- ✅ System Design de Data Engineering
- ✅ Coding (SQL, Python)
- ✅ Perguntas comportamentais (STAR method)
- ✅ Case studies
- ✅ Negociação de oferta

## 📚 Conteúdo

### 1. System Design

**Tópicos comuns:**
- Design Data Warehouse
- Real-time Analytics Pipeline
- ETL at Scale
- Data Lake Architecture
- CDC Pipeline

**Framework:**
1. Requirements (functional, non-functional)
2. Capacity Estimation (QPS, storage, bandwidth)
3. High-level Design
4. Detailed Design
5. Trade-offs

**Exemplo: Design Uber Data Pipeline**
```
Requirements:
- 10M trips/day
- Real-time driver location (1M drivers)
- Analytics dashboard (1h latency OK)

Architecture:
Drivers → Mobile App → API Gateway → Kafka → Flink → PostgreSQL/Redis
                                                    ↓
                                                 S3 Data Lake
                                                    ↓
                                            Spark (batch) → Redshift → Tableau
```

### 2. Coding

**SQL:**
- Window functions
- CTEs
- Complex joins
- Performance optimization

**Python:**
- Data structures (dict, set, list)
- Algorithms (sorting, searching)
- Pandas operations
- PySpark transformations

### 3. Perguntas Comportamentais

**STAR Method:**
- Situation
- Task
- Action
- Result

**Exemplos:**
- "Tell me about a time you had to optimize a slow pipeline"
- "Describe a conflict with a team member"
- "How do you handle tight deadlines?"

### 4. Empresas-alvo

**FAANG+ for Data Engineering:**
- Meta/Facebook
- Amazon
- Google
- Netflix
- Uber
- Airbnb
- LinkedIn
- Twitter/X

**Níveis:**
- E3/L3 (Junior): 0-2 anos
- E4/L4 (Mid): 2-5 anos
- E5/L5 (Senior): 5-8 anos
- E6+/L6+ (Staff+): 8+ anos

## 🎯 Exercícios

Ver **[10-projetos-entrevista/](../../10-projetos-entrevista/)** para projetos práticos

## 📖 Recursos

- **Book**: "Cracking the Coding Interview"
- **Practice**: LeetCode, HackerRank
- **Mock Interviews**: interviewing.io
- **System Design**: SystemDesignPrimer

## ✅ Checklist

- [ ] Resolvi 100+ SQL problems
- [ ] Fiz 50+ Python exercises
- [ ] Pratiquei 20+ system designs
- [ ] Mock interviews (5+)
- [ ] Preparei perguntas comportamentais
- [ ] Atualizei LinkedIn/Resume

## 🎉 Parabéns!

Você completou todos os 8 módulos! Agora você está pronto para:
- Aplicar para posições Senior
- Passar em entrevistas FAANG
- Construir pipelines de dados em escala

**Continue praticando com:**
- [Projetos Práticos](../../09-projetos-praticos/)
- [Projetos de Entrevista](../../10-projetos-entrevista/)
- [Certificações](../../11-certificacoes/)
