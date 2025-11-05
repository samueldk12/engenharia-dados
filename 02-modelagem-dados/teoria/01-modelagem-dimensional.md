# 📊 Modelagem Dimensional: Star Schema e Data Vault

## 📋 Índice

1. [Modelagem Dimensional vs Normalizada](#modelagem-dimensional-vs-normalizada)
2. [Star Schema](#star-schema)
3. [Snowflake Schema](#snowflake-schema)
4. [Data Vault 2.0](#data-vault-20)
5. [Slowly Changing Dimensions (SCD)](#slowly-changing-dimensions-scd)
6. [Fact Tables: Tipos e Patterns](#fact-tables-tipos-e-patterns)
7. [Comparação de Abordagens](#comparação-de-abordagens)

---

## Modelagem Dimensional vs Normalizada

### OLTP (3NF - Third Normal Form)

**Objetivo:** Eliminar redundância e garantir consistência transacional

**Características:**
- Tabelas altamente normalizadas (3NF ou BCNF)
- Muitas tabelas pequenas
- Muitos JOINs necessários
- Otimizado para INSERT/UPDATE/DELETE
- Integridade referencial rigorosa

**Exemplo OLTP (E-commerce):**

```sql
-- Sistema OLTP normalizado
CREATE TABLE users (
    user_id INT PRIMARY KEY,
    email VARCHAR(255) UNIQUE,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    created_at TIMESTAMP
);

CREATE TABLE addresses (
    address_id INT PRIMARY KEY,
    user_id INT REFERENCES users(user_id),
    street VARCHAR(255),
    city VARCHAR(100),
    state VARCHAR(50),
    country VARCHAR(50),
    postal_code VARCHAR(20),
    address_type VARCHAR(20)  -- shipping, billing
);

CREATE TABLE orders (
    order_id INT PRIMARY KEY,
    user_id INT REFERENCES users(user_id),
    shipping_address_id INT REFERENCES addresses(address_id),
    billing_address_id INT REFERENCES addresses(address_id),
    order_date TIMESTAMP,
    status VARCHAR(50)
);

CREATE TABLE order_items (
    order_item_id INT PRIMARY KEY,
    order_id INT REFERENCES orders(order_id),
    product_id INT REFERENCES products(product_id),
    quantity INT,
    unit_price DECIMAL(10,2)
);

-- Query OLTP (muitos JOINs)
SELECT 
    u.email,
    u.first_name || ' ' || u.last_name as customer_name,
    o.order_id,
    o.order_date,
    sa.city as shipping_city,
    p.product_name,
    oi.quantity,
    oi.unit_price
FROM orders o
JOIN users u ON o.user_id = u.user_id
JOIN addresses sa ON o.shipping_address_id = sa.address_id
JOIN order_items oi ON o.order_id = oi.order_id
JOIN products p ON oi.product_id = p.product_id
WHERE o.order_date >= '2024-01-01';
```

### OLAP (Dimensional Modeling)

**Objetivo:** Otimizar para leitura e análise

**Características:**
- Denormalização intencional
- Fact tables (métricas) + Dimension tables (contexto)
- Menos JOINs
- Otimizado para SELECT e agregações
- Redundância aceita para performance

---

## Star Schema

### Conceito

**Star Schema** é a forma mais simples de modelagem dimensional:
- **Fact Table** no centro (métricas/medidas)
- **Dimension Tables** ao redor (contexto)
- Dimensões não normalizadas (flat)

### Exemplo Completo: E-commerce Star Schema

```sql
-- DIMENSION TABLES

-- Dim Tempo (Date Dimension)
CREATE TABLE dim_tempo (
    data_key INT PRIMARY KEY,         -- 20240115 (surrogate key)
    data_completa DATE NOT NULL,
    ano INT,
    trimestre INT,
    mes INT,
    mes_nome VARCHAR(20),
    semana_ano INT,
    dia_mes INT,
    dia_semana INT,
    dia_semana_nome VARCHAR(20),
    fim_de_semana BOOLEAN,
    feriado BOOLEAN,
    feriado_nome VARCHAR(100)
);

-- Dim Cliente (Customer Dimension) - SCD Type 2
CREATE TABLE dim_cliente (
    cliente_key BIGINT PRIMARY KEY,   -- Surrogate key
    cliente_id INT NOT NULL,          -- Natural key (business key)
    email VARCHAR(255),
    nome_completo VARCHAR(200),
    data_nascimento DATE,
    genero VARCHAR(20),
    
    -- Endereço (denormalizado)
    cidade VARCHAR(100),
    estado VARCHAR(50),
    pais VARCHAR(50),
    cep VARCHAR(20),
    
    -- Segmento
    segmento VARCHAR(50),             -- VIP, Regular, Novo
    lifetime_value DECIMAL(12,2),
    
    -- SCD Type 2 fields
    data_inicio DATE NOT NULL,
    data_fim DATE,                    -- NULL = registro atual
    registro_ativo BOOLEAN DEFAULT TRUE,
    
    UNIQUE (cliente_id, data_inicio)
);

-- Dim Produto (Product Dimension)
CREATE TABLE dim_produto (
    produto_key INT PRIMARY KEY,
    produto_id INT NOT NULL UNIQUE,
    nome_produto VARCHAR(255),
    descricao TEXT,
    sku VARCHAR(100),
    
    -- Hierarquia de categoria (denormalizada)
    categoria_nivel1 VARCHAR(100),    -- Eletrônicos
    categoria_nivel2 VARCHAR(100),    -- Smartphones
    categoria_nivel3 VARCHAR(100),    -- iPhone
    
    -- Atributos
    marca VARCHAR(100),
    preco_sugerido DECIMAL(10,2),
    peso_kg DECIMAL(8,2),
    
    -- Metadata
    data_lancamento DATE,
    ativo BOOLEAN DEFAULT TRUE
);

-- Dim Promoção (Promotion Dimension)
CREATE TABLE dim_promocao (
    promocao_key INT PRIMARY KEY,
    promocao_id INT,
    nome_promocao VARCHAR(200),
    tipo_desconto VARCHAR(50),        -- percentual, valor_fixo, frete_gratis
    valor_desconto DECIMAL(10,2),
    data_inicio DATE,
    data_fim DATE,
    
    -- Caso especial: sem promoção
    CONSTRAINT chk_sem_promocao CHECK (
        promocao_id = 0 OR promocao_id IS NOT NULL
    )
);

-- FACT TABLE

-- Fact Vendas (Sales Fact)
CREATE TABLE fact_vendas (
    venda_id BIGINT PRIMARY KEY,
    
    -- Foreign Keys para Dimensions
    data_key INT NOT NULL REFERENCES dim_tempo(data_key),
    cliente_key BIGINT NOT NULL REFERENCES dim_cliente(cliente_key),
    produto_key INT NOT NULL REFERENCES dim_produto(produto_key),
    promocao_key INT REFERENCES dim_promocao(promocao_key),
    
    -- Degenerate Dimensions (dimensões sem tabela própria)
    pedido_id INT NOT NULL,
    item_pedido_id INT NOT NULL,
    
    -- Métricas Aditivas
    quantidade INT NOT NULL,
    valor_unitario DECIMAL(10,2) NOT NULL,
    valor_desconto DECIMAL(10,2) DEFAULT 0,
    valor_frete DECIMAL(10,2) DEFAULT 0,
    valor_total DECIMAL(12,2) NOT NULL,
    custo_produto DECIMAL(10,2),
    
    -- Métricas Derivadas (calculadas)
    valor_liquido DECIMAL(12,2) GENERATED ALWAYS AS 
        (valor_total - valor_desconto) STORED,
    margem_lucro DECIMAL(12,2) GENERATED ALWAYS AS 
        (valor_total - custo_produto) STORED,
    margem_lucro_percentual DECIMAL(5,2) GENERATED ALWAYS AS 
        ((valor_total - custo_produto) / NULLIF(valor_total, 0) * 100) STORED,
    
    -- Metadata
    data_carga TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes para performance
CREATE INDEX idx_fact_vendas_data ON fact_vendas(data_key);
CREATE INDEX idx_fact_vendas_cliente ON fact_vendas(cliente_key);
CREATE INDEX idx_fact_vendas_produto ON fact_vendas(produto_key);
CREATE INDEX idx_fact_vendas_pedido ON fact_vendas(pedido_id);
```

### Queries Analíticas com Star Schema

```sql
-- 1. Vendas totais por mês e categoria
SELECT 
    t.ano,
    t.mes_nome,
    p.categoria_nivel1,
    SUM(f.valor_total) as receita_total,
    SUM(f.quantidade) as unidades_vendidas,
    COUNT(DISTINCT f.cliente_key) as clientes_unicos,
    AVG(f.valor_total) as ticket_medio
FROM fact_vendas f
JOIN dim_tempo t ON f.data_key = t.data_key
JOIN dim_produto p ON f.produto_key = p.produto_key
WHERE t.ano = 2024
GROUP BY t.ano, t.mes, t.mes_nome, p.categoria_nivel1
ORDER BY t.ano, t.mes, receita_total DESC;

-- 2. Top 10 clientes por lifetime value
SELECT 
    c.nome_completo,
    c.segmento,
    c.cidade,
    c.pais,
    COUNT(DISTINCT f.pedido_id) as total_pedidos,
    SUM(f.valor_total) as lifetime_value,
    AVG(f.valor_total) as ticket_medio,
    MAX(t.data_completa) as ultima_compra
FROM fact_vendas f
JOIN dim_cliente c ON f.cliente_key = c.cliente_key
JOIN dim_tempo t ON f.data_key = t.data_key
WHERE c.registro_ativo = TRUE
GROUP BY c.cliente_key, c.nome_completo, c.segmento, c.cidade, c.pais
ORDER BY lifetime_value DESC
LIMIT 10;

-- 3. Análise de sazonalidade (vendas por dia da semana)
SELECT 
    t.dia_semana_nome,
    t.fim_de_semana,
    COUNT(DISTINCT f.pedido_id) as total_pedidos,
    SUM(f.valor_total) as receita_total,
    AVG(f.valor_total) as ticket_medio,
    SUM(f.quantidade) as unidades_vendidas
FROM fact_vendas f
JOIN dim_tempo t ON f.data_key = t.data_key
WHERE t.ano = 2024
GROUP BY t.dia_semana, t.dia_semana_nome, t.fim_de_semana
ORDER BY t.dia_semana;

-- 4. Efetividade de promoções
SELECT 
    pr.nome_promocao,
    pr.tipo_desconto,
    COUNT(DISTINCT f.pedido_id) as pedidos_com_promocao,
    SUM(f.valor_total) as receita_total,
    SUM(f.valor_desconto) as desconto_total,
    SUM(f.valor_liquido) as receita_liquida,
    AVG(f.quantidade) as media_itens_por_pedido
FROM fact_vendas f
JOIN dim_promocao pr ON f.promocao_key = pr.promocao_key
WHERE pr.promocao_id > 0  -- Excluir "sem promoção"
GROUP BY pr.promocao_key, pr.nome_promocao, pr.tipo_desconto
ORDER BY receita_liquida DESC;
```

---

## Snowflake Schema

### Conceito

**Snowflake Schema** é uma variação do Star Schema onde dimensões são normalizadas em sub-dimensões.

**Vantagens:**
- Menos redundância de dados
- Menor tamanho de armazenamento
- Melhor para atualização de dimensões

**Desvantagens:**
- Mais JOINs = queries mais lentas
- Mais complexo de manter

### Exemplo: Snowflake Schema

```sql
-- Star Schema DENORMALIZADO
CREATE TABLE dim_produto_star (
    produto_key INT PRIMARY KEY,
    produto_id INT,
    nome_produto VARCHAR(255),
    categoria_nivel1 VARCHAR(100),  -- Redundante
    categoria_nivel2 VARCHAR(100),  -- Redundante
    categoria_nivel3 VARCHAR(100),  -- Redundante
    marca VARCHAR(100),             -- Redundante
    marca_pais VARCHAR(50)          -- Redundante
);

-- Snowflake Schema NORMALIZADO
CREATE TABLE dim_produto_snowflake (
    produto_key INT PRIMARY KEY,
    produto_id INT,
    nome_produto VARCHAR(255),
    categoria_key INT REFERENCES dim_categoria(categoria_key),
    marca_key INT REFERENCES dim_marca(marca_key)
);

CREATE TABLE dim_categoria (
    categoria_key INT PRIMARY KEY,
    categoria_nivel1 VARCHAR(100),
    categoria_nivel2 VARCHAR(100),
    categoria_nivel3 VARCHAR(100)
);

CREATE TABLE dim_marca (
    marca_key INT PRIMARY KEY,
    marca_nome VARCHAR(100),
    marca_pais VARCHAR(50)
);

-- Query com Snowflake (mais JOINs)
SELECT 
    p.nome_produto,
    c.categoria_nivel1,
    c.categoria_nivel2,
    m.marca_nome,
    m.marca_pais,
    SUM(f.valor_total) as receita
FROM fact_vendas f
JOIN dim_produto_snowflake p ON f.produto_key = p.produto_key
JOIN dim_categoria c ON p.categoria_key = c.categoria_key
JOIN dim_marca m ON p.marca_key = m.marca_key
GROUP BY p.nome_produto, c.categoria_nivel1, c.categoria_nivel2, m.marca_nome, m.marca_pais;
```

**Recomendação:** Use **Star Schema** na maioria dos casos. Snowflake só se justifica quando economia de storage é crítica.

---

## Data Vault 2.0

### Conceito

**Data Vault** é uma metodologia de modelagem para Enterprise Data Warehouses que prioriza:
- **Auditabilidade**: Rastreamento completo de mudanças
- **Escalabilidade**: Adicionar novos dados sem reestruturar
- **Flexibilidade**: Acomodar mudanças de requisitos

### Componentes do Data Vault

1. **Hubs**: Entidades de negócio (chaves de negócio únicas)
2. **Links**: Relacionamentos entre Hubs
3. **Satellites**: Atributos descritivos e histórico

### Exemplo: Data Vault

```sql
-- HUB: Entidade Cliente
CREATE TABLE hub_cliente (
    cliente_hub_key BIGINT PRIMARY KEY,      -- Hash da business key
    cliente_id INT NOT NULL UNIQUE,          -- Business key (natural key)
    load_timestamp TIMESTAMP NOT NULL,
    record_source VARCHAR(50) NOT NULL,      -- Sistema origem (CRM, ERP, etc)
    
    INDEX idx_hub_cliente_bk (cliente_id)
);

-- HUB: Entidade Produto
CREATE TABLE hub_produto (
    produto_hub_key BIGINT PRIMARY KEY,
    produto_id INT NOT NULL UNIQUE,
    load_timestamp TIMESTAMP NOT NULL,
    record_source VARCHAR(50) NOT NULL
);

-- LINK: Relacionamento Compra (Cliente → Produto)
CREATE TABLE link_compra (
    compra_link_key BIGINT PRIMARY KEY,      -- Hash (cliente_hub_key + produto_hub_key + pedido_id)
    cliente_hub_key BIGINT NOT NULL REFERENCES hub_cliente(cliente_hub_key),
    produto_hub_key BIGINT NOT NULL REFERENCES hub_produto(produto_hub_key),
    pedido_id INT NOT NULL,                  -- Business key do pedido
    load_timestamp TIMESTAMP NOT NULL,
    record_source VARCHAR(50) NOT NULL,
    
    INDEX idx_link_compra_cliente (cliente_hub_key),
    INDEX idx_link_compra_produto (produto_hub_key)
);

-- SATELLITE: Atributos do Cliente (com histórico)
CREATE TABLE sat_cliente_dados (
    cliente_hub_key BIGINT NOT NULL REFERENCES hub_cliente(cliente_hub_key),
    load_timestamp TIMESTAMP NOT NULL,       -- SCD Type 2: data da mudança
    load_end_timestamp TIMESTAMP,            -- NULL = registro atual
    
    -- Atributos descritivos
    nome_completo VARCHAR(200),
    email VARCHAR(255),
    data_nascimento DATE,
    cidade VARCHAR(100),
    estado VARCHAR(50),
    pais VARCHAR(50),
    segmento VARCHAR(50),
    
    -- Metadata
    record_source VARCHAR(50) NOT NULL,
    hash_diff BIGINT NOT NULL,               -- Hash dos atributos (detectar mudanças)
    
    PRIMARY KEY (cliente_hub_key, load_timestamp)
);

-- SATELLITE: Métricas da Compra
CREATE TABLE sat_compra_metricas (
    compra_link_key BIGINT NOT NULL REFERENCES link_compra(compra_link_key),
    load_timestamp TIMESTAMP NOT NULL,
    
    -- Métricas
    quantidade INT,
    valor_unitario DECIMAL(10,2),
    valor_desconto DECIMAL(10,2),
    valor_total DECIMAL(12,2),
    
    record_source VARCHAR(50) NOT NULL,
    hash_diff BIGINT NOT NULL,
    
    PRIMARY KEY (compra_link_key, load_timestamp)
);
```

### Vantagens do Data Vault

- ✅ **Auditabilidade total**: Cada mudança é rastreada
- ✅ **Escalabilidade**: Adicionar novos Hubs/Links sem impacto
- ✅ **Cargas paralelas**: Hubs, Links e Satellites podem ser carregados independentemente
- ✅ **Histórico completo**: Satellites mantêm todo o histórico

### Desvantagens do Data Vault

- ❌ **Complexidade**: Muitas tabelas e JOINs
- ❌ **Performance**: Queries precisam de muitas joins
- ❌ **Curva de aprendizado**: Requer treinamento específico

**Recomendação:** Use Data Vault em **Enterprise Data Warehouses** com requisitos rigorosos de auditoria. Para a maioria dos casos, **Star Schema é suficiente**.

---

## Slowly Changing Dimensions (SCD)

### SCD Type 0: Retain Original

**Uso:** Dados que nunca mudam (ex: data de nascimento)

```sql
CREATE TABLE dim_cliente_type0 (
    cliente_id INT PRIMARY KEY,
    data_nascimento DATE NOT NULL  -- Nunca muda
);
```

### SCD Type 1: Overwrite

**Uso:** Correções ou quando histórico não importa

```sql
-- Antes
UPDATE dim_cliente
SET email = 'novo_email@example.com'
WHERE cliente_id = 123;

-- Histórico é perdido
```

### SCD Type 2: Add New Row

**Uso:** Rastrear histórico completo (mais comum)

```sql
-- Implementação SCD Type 2
CREATE TABLE dim_cliente_type2 (
    cliente_key BIGINT PRIMARY KEY,   -- Surrogate key
    cliente_id INT NOT NULL,          -- Business key
    nome VARCHAR(200),
    email VARCHAR(255),
    cidade VARCHAR(100),
    segmento VARCHAR(50),
    
    -- SCD Type 2 tracking
    data_inicio DATE NOT NULL,
    data_fim DATE,                    -- NULL = registro atual
    registro_ativo BOOLEAN NOT NULL DEFAULT TRUE
);

-- Inserir novo cliente
INSERT INTO dim_cliente_type2 
    (cliente_key, cliente_id, nome, email, cidade, segmento, data_inicio, data_fim, registro_ativo)
VALUES 
    (1, 123, 'João Silva', 'joao@example.com', 'São Paulo', 'Regular', '2024-01-01', NULL, TRUE);

-- Cliente mudou de cidade: criar novo registro
-- 1. Fechar registro antigo
UPDATE dim_cliente_type2
SET data_fim = '2024-06-15',
    registro_ativo = FALSE
WHERE cliente_id = 123 AND registro_ativo = TRUE;

-- 2. Inserir novo registro
INSERT INTO dim_cliente_type2
    (cliente_key, cliente_id, nome, email, cidade, segmento, data_inicio, data_fim, registro_ativo)
VALUES
    (2, 123, 'João Silva', 'joao@example.com', 'Rio de Janeiro', 'VIP', '2024-06-16', NULL, TRUE);

-- Query: pegar apenas registros atuais
SELECT * FROM dim_cliente_type2 WHERE registro_ativo = TRUE;

-- Query: histórico completo de um cliente
SELECT * FROM dim_cliente_type2 WHERE cliente_id = 123 ORDER BY data_inicio;
```

### SCD Type 3: Add New Column

**Uso:** Rastrear mudança específica (ex: apenas mudança anterior)

```sql
CREATE TABLE dim_cliente_type3 (
    cliente_id INT PRIMARY KEY,
    nome VARCHAR(200),
    cidade_atual VARCHAR(100),
    cidade_anterior VARCHAR(100),      -- Apenas última mudança
    data_mudanca_cidade DATE
);

-- Atualização Type 3
UPDATE dim_cliente_type3
SET cidade_anterior = cidade_atual,
    cidade_atual = 'Rio de Janeiro',
    data_mudanca_cidade = '2024-06-16'
WHERE cliente_id = 123;
```

---

## Fact Tables: Tipos e Patterns

### Tipos de Fact Tables

#### 1. Transaction Fact Table

**Uso:** Uma linha por transação (mais granular)

```sql
CREATE TABLE fact_vendas_transacao (
    venda_id BIGINT PRIMARY KEY,
    data_key INT,
    cliente_key BIGINT,
    produto_key INT,
    pedido_id INT,              -- Degenerate dimension
    quantidade INT,
    valor_total DECIMAL(12,2)
);

-- Exemplo: Cada item vendido gera uma linha
-- Pedido 1001: iPhone (qty 1) + Case (qty 2) = 2 linhas na fact
```

#### 2. Periodic Snapshot Fact Table

**Uso:** Estado em um momento específico (ex: inventário diário)

```sql
CREATE TABLE fact_inventario_diario (
    data_key INT,
    produto_key INT,
    armazem_key INT,
    quantidade_disponivel INT,
    quantidade_reservada INT,
    quantidade_transito INT,
    PRIMARY KEY (data_key, produto_key, armazem_key)
);

-- Snapshot rodado todo dia à meia-noite
-- Cada produto tem UMA linha por dia
```

#### 3. Accumulating Snapshot Fact Table

**Uso:** Processos com múltiplos marcos (ex: pipeline de vendas)

```sql
CREATE TABLE fact_pedido_lifecycle (
    pedido_id INT PRIMARY KEY,
    
    -- Múltiplas datas (milestones)
    data_pedido_key INT,
    data_pagamento_key INT,
    data_envio_key INT,
    data_entrega_key INT,
    
    -- Métricas
    valor_pedido DECIMAL(12,2),
    dias_pagamento_envio INT,
    dias_envio_entrega INT,
    
    -- Status atual
    status VARCHAR(50)
);

-- Linha é ATUALIZADA conforme pedido avança
-- Pedido 1001:
-- Inserido: data_pedido_key = 20240115, demais = NULL
-- Pago:     data_pagamento_key = 20240116
-- Enviado:  data_envio_key = 20240117
-- Entregue: data_entrega_key = 20240120
```

### Métricas: Aditivas vs Semi-Aditivas vs Não-Aditivas

```sql
-- ADITIVAS: Podem somar em qualquer dimensão
quantidade INT,                    -- ✅ Pode somar por tempo, produto, cliente
valor_total DECIMAL(12,2),        -- ✅ Pode somar por qualquer dimensão

-- SEMI-ADITIVAS: Não podem somar por tempo
saldo_conta DECIMAL(12,2),        -- ❌ Não faz sentido somar saldos de Jan + Fev
quantidade_estoque INT,           -- ❌ Não faz sentido somar estoque de Jan + Fev

-- NÃO-ADITIVAS: Não podem somar em nenhuma dimensão
percentual_desconto DECIMAL(5,2), -- ❌ Não faz sentido somar percentuais
margem_percentual DECIMAL(5,2),   -- ❌ Usar média ponderada ao invés de soma

-- Como lidar com métricas semi-aditivas
SELECT 
    cliente_key,
    AVG(saldo_conta) as saldo_medio,    -- Média ao invés de soma
    MAX(saldo_conta) as saldo_maximo    -- Ou máximo
FROM fact_saldo_diario
GROUP BY cliente_key;
```

---

## Comparação de Abordagens

| Aspecto | Star Schema | Snowflake Schema | Data Vault |
|---------|-------------|------------------|------------|
| **Complexidade** | Baixa | Média | Alta |
| **Performance de Query** | Alta | Média | Baixa |
| **Manutenção** | Fácil | Média | Complexa |
| **Storage** | Maior (redundância) | Menor | Maior |
| **Auditabilidade** | Baixa | Baixa | Alta |
| **Escalabilidade** | Boa | Boa | Excelente |
| **Curva de Aprendizado** | Fácil | Fácil | Difícil |
| **Melhor para** | BI e Analytics | Storage limitado | Enterprise DW |

### Quando usar cada abordagem

**Star Schema:**
- ✅ BI e analytics tradicionais
- ✅ Equipes menores
- ✅ Performance de query é prioridade
- ✅ Maioria dos projetos

**Snowflake Schema:**
- ✅ Storage é muito caro
- ✅ Dimensões muito grandes
- ✅ Atualizações frequentes de dimensões

**Data Vault:**
- ✅ Enterprise Data Warehouse
- ✅ Auditoria rigorosa é mandatória
- ✅ Múltiplos sistemas fonte
- ✅ Equipe com expertise em Data Vault

---

## 🎯 Exercícios Práticos

1. **Modelar Star Schema:** Crie um star schema para uma plataforma de streaming (Netflix-like)
2. **Implementar SCD Type 2:** Implemente mudança de categoria de cliente (Bronze → Silver → Gold)
3. **Queries Analíticas:** Escreva queries para calcular:
   - Top 10 produtos por receita em cada trimestre
   - Análise de churn: clientes que não compraram nos últimos 90 dias
   - Coorte analysis: retenção por mês de primeira compra

---

## 📚 Referências

- Kimball, Ralph. "The Data Warehouse Toolkit" (3rd Edition)
- Linstedt, Dan. "Building a Scalable Data Warehouse with Data Vault 2.0"
- Inmon, Bill. "Building the Data Warehouse"

---

**Próximo:** [02-data-lake-arquitetura.md](./02-data-lake-arquitetura.md)
