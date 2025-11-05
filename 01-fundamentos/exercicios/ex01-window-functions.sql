-- ============================================================================
-- EXERCÍCIOS: SQL Window Functions e Query Avançado
-- Nível: Intermediário-Avançado
-- Objetivo: Dominar window functions, CTEs e otimização de queries
-- ============================================================================

-- ============================================================================
-- PARTE 1: Setup do Schema e Dados de Teste
-- ============================================================================

-- Criar tabelas
CREATE TABLE customers (
    customer_id SERIAL PRIMARY KEY,
    customer_name VARCHAR(100),
    email VARCHAR(100),
    signup_date DATE,
    country VARCHAR(50),
    customer_tier VARCHAR(20) -- 'bronze', 'silver', 'gold'
);

CREATE TABLE products (
    product_id SERIAL PRIMARY KEY,
    product_name VARCHAR(200),
    category VARCHAR(50),
    price DECIMAL(10,2),
    cost DECIMAL(10,2)
);

CREATE TABLE orders (
    order_id SERIAL PRIMARY KEY,
    customer_id INT REFERENCES customers(customer_id),
    order_date DATE,
    order_value DECIMAL(10,2),
    status VARCHAR(20) -- 'pending', 'completed', 'cancelled'
);

CREATE TABLE order_items (
    order_item_id SERIAL PRIMARY KEY,
    order_id INT REFERENCES orders(order_id),
    product_id INT REFERENCES products(product_id),
    quantity INT,
    unit_price DECIMAL(10,2)
);

-- Inserir dados de teste
INSERT INTO customers (customer_name, email, signup_date, country, customer_tier)
SELECT
    'Customer ' || i,
    'customer' || i || '@example.com',
    '2023-01-01'::DATE + (random() * 365)::INT,
    CASE (random() * 4)::INT
        WHEN 0 THEN 'USA'
        WHEN 1 THEN 'Brazil'
        WHEN 2 THEN 'UK'
        ELSE 'Germany'
    END,
    CASE (random() * 3)::INT
        WHEN 0 THEN 'bronze'
        WHEN 1 THEN 'silver'
        ELSE 'gold'
    END
FROM generate_series(1, 1000) i;

INSERT INTO products (product_name, category, price, cost)
SELECT
    'Product ' || i,
    CASE (random() * 4)::INT
        WHEN 0 THEN 'Electronics'
        WHEN 1 THEN 'Clothing'
        WHEN 2 THEN 'Books'
        ELSE 'Home'
    END,
    (random() * 1000 + 10)::DECIMAL(10,2),
    (random() * 500 + 5)::DECIMAL(10,2)
FROM generate_series(1, 500) i;

INSERT INTO orders (customer_id, order_date, order_value, status)
SELECT
    (random() * 999 + 1)::INT,
    '2023-01-01'::DATE + (random() * 365)::INT,
    (random() * 1000 + 50)::DECIMAL(10,2),
    CASE (random() * 10)::INT
        WHEN 0 THEN 'cancelled'
        WHEN 1 THEN 'pending'
        ELSE 'completed'
    END
FROM generate_series(1, 10000) i;

INSERT INTO order_items (order_id, product_id, quantity, unit_price)
SELECT
    o.order_id,
    (random() * 499 + 1)::INT,
    (random() * 5 + 1)::INT,
    p.price
FROM orders o
CROSS JOIN LATERAL (
    SELECT price FROM products WHERE product_id = (random() * 499 + 1)::INT LIMIT 1
) p
WHERE random() < 0.3; -- 30% dos pedidos têm itens

-- ============================================================================
-- EXERCÍCIO 1: Ranking e Top N
-- ============================================================================

-- 1.1 Liste os top 3 produtos mais vendidos (por quantidade) em cada categoria
-- Resultado esperado: categoria, produto, quantidade vendida, rank
-- Dica: Use ROW_NUMBER() ou RANK()

-- SUA SOLUÇÃO AQUI:
-- TODO: Implementar query


-- SOLUÇÃO:
WITH product_sales AS (
    SELECT
        p.category,
        p.product_name,
        SUM(oi.quantity) as total_quantity,
        SUM(oi.quantity * oi.unit_price) as total_revenue
    FROM order_items oi
    JOIN products p ON oi.product_id = p.product_id
    JOIN orders o ON oi.order_id = o.order_id
    WHERE o.status = 'completed'
    GROUP BY p.category, p.product_name
)
SELECT
    category,
    product_name,
    total_quantity,
    total_revenue,
    ROW_NUMBER() OVER (PARTITION BY category ORDER BY total_quantity DESC) as rank
FROM product_sales
QUALIFY rank <= 3  -- Postgres 14+, senão use subquery
ORDER BY category, rank;


-- 1.2 Para cada cliente, mostre seu primeiro pedido e último pedido
-- Resultado: customer_id, customer_name, first_order_date, first_order_value,
--            last_order_date, last_order_value, total_orders
-- Dica: Use FIRST_VALUE() e LAST_VALUE()

-- SUA SOLUÇÃO AQUI:
-- TODO: Implementar query


-- SOLUÇÃO:
SELECT DISTINCT
    c.customer_id,
    c.customer_name,
    FIRST_VALUE(o.order_date) OVER w as first_order_date,
    FIRST_VALUE(o.order_value) OVER w as first_order_value,
    LAST_VALUE(o.order_date) OVER w_full as last_order_date,
    LAST_VALUE(o.order_value) OVER w_full as last_order_value,
    COUNT(*) OVER (PARTITION BY c.customer_id) as total_orders
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id
WHERE o.status = 'completed'
WINDOW
    w AS (PARTITION BY c.customer_id ORDER BY o.order_date ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING),
    w_full AS (PARTITION BY c.customer_id ORDER BY o.order_date ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING)
ORDER BY c.customer_id;


-- ============================================================================
-- EXERCÍCIO 2: Running Totals e Moving Averages
-- ============================================================================

-- 2.1 Calcule o revenue acumulado (running total) por dia
-- Resultado: date, daily_revenue, running_total
-- Dica: Use SUM() OVER (ORDER BY date)

-- SUA SOLUÇÃO AQUI:
-- TODO: Implementar query


-- SOLUÇÃO:
SELECT
    order_date,
    SUM(order_value) as daily_revenue,
    SUM(SUM(order_value)) OVER (ORDER BY order_date) as running_total,
    AVG(SUM(order_value)) OVER (
        ORDER BY order_date
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ) as moving_avg_7_days
FROM orders
WHERE status = 'completed'
GROUP BY order_date
ORDER BY order_date;


-- 2.2 Calcule a média móvel de 7 dias das vendas
-- Resultado: date, daily_revenue, moving_avg_7_days
-- Dica: Use AVG() OVER (ORDER BY date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW)

-- SUA SOLUÇÃO AQUI:
-- TODO: Implementar query


-- ============================================================================
-- EXERCÍCIO 3: Análise Cohort
-- ============================================================================

-- 3.1 Análise de retenção por cohort (mês de signup)
-- Para cada cohort (mês de signup), calcule quantos clientes fizeram pedidos
-- em cada mês subsequente
-- Resultado: signup_month, order_month, months_since_signup, customers_count

-- SUA SOLUÇÃO AQUI:
-- TODO: Implementar query


-- SOLUÇÃO:
WITH customer_cohorts AS (
    SELECT
        customer_id,
        DATE_TRUNC('month', signup_date) as cohort_month
    FROM customers
),
customer_orders AS (
    SELECT
        o.customer_id,
        DATE_TRUNC('month', o.order_date) as order_month
    FROM orders o
    WHERE o.status = 'completed'
)
SELECT
    cc.cohort_month,
    co.order_month,
    EXTRACT(YEAR FROM AGE(co.order_month, cc.cohort_month)) * 12 +
    EXTRACT(MONTH FROM AGE(co.order_month, cc.cohort_month)) as months_since_signup,
    COUNT(DISTINCT co.customer_id) as customers_count,
    COUNT(DISTINCT co.customer_id)::FLOAT /
        NULLIF(COUNT(DISTINCT CASE WHEN co.order_month = cc.cohort_month THEN co.customer_id END), 0) * 100
        as retention_rate
FROM customer_cohorts cc
LEFT JOIN customer_orders co ON cc.customer_id = co.customer_id
GROUP BY cc.cohort_month, co.order_month
ORDER BY cc.cohort_month, co.order_month;


-- ============================================================================
-- EXERCÍCIO 4: LAG e LEAD - Análise de Crescimento
-- ============================================================================

-- 4.1 Calcule o crescimento mensal de revenue (% vs mês anterior)
-- Resultado: month, monthly_revenue, prev_month_revenue, growth_rate_pct

-- SUA SOLUÇÃO AQUI:
-- TODO: Implementar query


-- SOLUÇÃO:
WITH monthly_revenue AS (
    SELECT
        DATE_TRUNC('month', order_date) as month,
        SUM(order_value) as revenue
    FROM orders
    WHERE status = 'completed'
    GROUP BY DATE_TRUNC('month', order_date)
)
SELECT
    month,
    revenue as monthly_revenue,
    LAG(revenue, 1) OVER (ORDER BY month) as prev_month_revenue,
    ROUND(
        (revenue - LAG(revenue, 1) OVER (ORDER BY month)) /
        NULLIF(LAG(revenue, 1) OVER (ORDER BY month), 0) * 100,
        2
    ) as growth_rate_pct
FROM monthly_revenue
ORDER BY month;


-- 4.2 Identifique gaps entre pedidos de cada cliente
-- Resultado: customer_id, order_date, next_order_date, days_between_orders
-- Apenas clientes com mais de 1 pedido

-- SUA SOLUÇÃO AQUI:
-- TODO: Implementar query


-- SOLUÇÃO:
WITH customer_order_sequence AS (
    SELECT
        customer_id,
        order_date,
        LEAD(order_date, 1) OVER (PARTITION BY customer_id ORDER BY order_date) as next_order_date
    FROM orders
    WHERE status = 'completed'
)
SELECT
    customer_id,
    order_date,
    next_order_date,
    next_order_date - order_date as days_between_orders
FROM customer_order_sequence
WHERE next_order_date IS NOT NULL
ORDER BY days_between_orders DESC;


-- ============================================================================
-- EXERCÍCIO 5: Percentiles e Quartis
-- ============================================================================

-- 5.1 Calcule os quartis de order_value e classifique cada pedido
-- Resultado: order_id, order_value, quartile (1-4), quartile_label

-- SUA SOLUÇÃO AQUI:
-- TODO: Implementar query


-- SOLUÇÃO:
SELECT
    order_id,
    order_value,
    NTILE(4) OVER (ORDER BY order_value) as quartile,
    CASE NTILE(4) OVER (ORDER BY order_value)
        WHEN 1 THEN 'Low Value'
        WHEN 2 THEN 'Medium Value'
        WHEN 3 THEN 'High Value'
        WHEN 4 THEN 'Premium Value'
    END as quartile_label,
    PERCENT_RANK() OVER (ORDER BY order_value) as percentile
FROM orders
WHERE status = 'completed';


-- ============================================================================
-- EXERCÍCIO 6: CTEs Recursivas
-- ============================================================================

-- 6.1 Crie uma hierarquia de categorias (simples -> subcategorias)
-- E liste todos os produtos em cada nível da hierarquia

-- Primeiro, criar tabela de hierarquia de categorias
CREATE TABLE category_hierarchy (
    category_id SERIAL PRIMARY KEY,
    category_name VARCHAR(50),
    parent_category_id INT REFERENCES category_hierarchy(category_id)
);

INSERT INTO category_hierarchy (category_name, parent_category_id) VALUES
('All Products', NULL),
('Electronics', 1),
('Clothing', 1),
('Books', 1),
('Home', 1),
('Smartphones', 2),
('Laptops', 2),
('Men', 3),
('Women', 3);

-- SUA SOLUÇÃO: Liste toda a hierarquia com níveis
-- TODO: Implementar CTE recursiva


-- SOLUÇÃO:
WITH RECURSIVE category_tree AS (
    -- Caso base: categorias raiz
    SELECT
        category_id,
        category_name,
        parent_category_id,
        1 as level,
        CAST(category_name AS VARCHAR(1000)) as path
    FROM category_hierarchy
    WHERE parent_category_id IS NULL

    UNION ALL

    -- Caso recursivo: subcategorias
    SELECT
        ch.category_id,
        ch.category_name,
        ch.parent_category_id,
        ct.level + 1,
        ct.path || ' > ' || ch.category_name
    FROM category_hierarchy ch
    INNER JOIN category_tree ct ON ch.parent_category_id = ct.category_id
)
SELECT
    REPEAT('  ', level - 1) || category_name as category_hierarchy,
    level,
    path
FROM category_tree
ORDER BY path;


-- ============================================================================
-- EXERCÍCIO 7: Query Optimization Challenge
-- ============================================================================

-- 7.1 OTIMIZE ESTA QUERY LENTA:
-- Query original (ineficiente):
SELECT
    c.customer_name,
    (SELECT COUNT(*) FROM orders o WHERE o.customer_id = c.customer_id) as order_count,
    (SELECT SUM(order_value) FROM orders o WHERE o.customer_id = c.customer_id) as total_spent
FROM customers c
WHERE YEAR(c.signup_date) = 2023;

-- SUA SOLUÇÃO OTIMIZADA:
-- TODO: Reescrever a query de forma mais eficiente


-- SOLUÇÃO OTIMIZADA:
SELECT
    c.customer_name,
    COUNT(o.order_id) as order_count,
    COALESCE(SUM(o.order_value), 0) as total_spent
FROM customers c
LEFT JOIN orders o ON c.customer_id = o.customer_id
WHERE c.signup_date >= '2023-01-01' AND c.signup_date < '2024-01-01'
GROUP BY c.customer_id, c.customer_name;

-- Criar índices para otimizar:
CREATE INDEX idx_customers_signup_date ON customers(signup_date);
CREATE INDEX idx_orders_customer_id ON orders(customer_id);
CREATE INDEX idx_orders_customer_date ON orders(customer_id, order_date);


-- ============================================================================
-- EXERCÍCIO 8: RFM Analysis (Recency, Frequency, Monetary)
-- ============================================================================

-- 8.1 Calcule o RFM score para cada cliente
-- Recency: dias desde último pedido
-- Frequency: número de pedidos
-- Monetary: valor total gasto

-- SUA SOLUÇÃO:
-- TODO: Implementar RFM analysis


-- SOLUÇÃO:
WITH customer_rfm AS (
    SELECT
        c.customer_id,
        c.customer_name,
        -- Recency: dias desde último pedido
        CURRENT_DATE - MAX(o.order_date) as days_since_last_order,
        -- Frequency: número de pedidos
        COUNT(o.order_id) as order_count,
        -- Monetary: valor total
        SUM(o.order_value) as total_value
    FROM customers c
    LEFT JOIN orders o ON c.customer_id = o.customer_id
    WHERE o.status = 'completed'
    GROUP BY c.customer_id, c.customer_name
),
rfm_scores AS (
    SELECT
        customer_id,
        customer_name,
        days_since_last_order,
        order_count,
        total_value,
        -- Recency score (menor é melhor)
        NTILE(5) OVER (ORDER BY days_since_last_order DESC) as r_score,
        -- Frequency score
        NTILE(5) OVER (ORDER BY order_count) as f_score,
        -- Monetary score
        NTILE(5) OVER (ORDER BY total_value) as m_score
    FROM customer_rfm
)
SELECT
    customer_id,
    customer_name,
    days_since_last_order,
    order_count,
    total_value,
    r_score,
    f_score,
    m_score,
    r_score + f_score + m_score as rfm_total_score,
    CASE
        WHEN r_score >= 4 AND f_score >= 4 AND m_score >= 4 THEN 'Champions'
        WHEN r_score >= 3 AND f_score >= 3 THEN 'Loyal Customers'
        WHEN r_score >= 4 THEN 'Potential Loyalists'
        WHEN r_score <= 2 AND f_score <= 2 THEN 'At Risk'
        WHEN r_score <= 2 THEN 'Lost'
        ELSE 'Regular'
    END as customer_segment
FROM rfm_scores
ORDER BY rfm_total_score DESC;


-- ============================================================================
-- EXERCÍCIO 9: Desafio Final - Dashboard Analytics Query
-- ============================================================================

-- 9.1 Crie uma query única que retorne métricas para um dashboard executivo:
-- - Revenue total (hoje, ontem, % mudança)
-- - Número de pedidos (hoje, ontem, % mudança)
-- - Top 5 produtos por revenue hoje
-- - Top 5 clientes por valor total (all time)
-- - Taxa de cancelamento (hoje vs média dos últimos 7 dias)

-- SUA SOLUÇÃO:
-- TODO: Implementar query complexa de dashboard


-- SOLUÇÃO (exemplo simplificado):
WITH todays_metrics AS (
    SELECT
        COUNT(*) as orders_today,
        SUM(order_value) as revenue_today,
        COUNT(CASE WHEN status = 'cancelled' THEN 1 END)::FLOAT / COUNT(*) * 100 as cancel_rate_today
    FROM orders
    WHERE order_date = CURRENT_DATE
),
yesterday_metrics AS (
    SELECT
        COUNT(*) as orders_yesterday,
        SUM(order_value) as revenue_yesterday
    FROM orders
    WHERE order_date = CURRENT_DATE - 1
),
top_products_today AS (
    SELECT
        p.product_name,
        SUM(oi.quantity * oi.unit_price) as revenue
    FROM order_items oi
    JOIN products p ON oi.product_id = p.product_id
    JOIN orders o ON oi.order_id = o.order_id
    WHERE o.order_date = CURRENT_DATE AND o.status = 'completed'
    GROUP BY p.product_name
    ORDER BY revenue DESC
    LIMIT 5
)
SELECT
    'Metrics Summary' as report_type,
    tm.orders_today,
    tm.revenue_today,
    ym.orders_yesterday,
    ym.revenue_yesterday,
    ROUND((tm.orders_today - ym.orders_yesterday)::NUMERIC / NULLIF(ym.orders_yesterday, 0) * 100, 2) as orders_change_pct,
    ROUND((tm.revenue_today - ym.revenue_yesterday) / NULLIF(ym.revenue_yesterday, 0) * 100, 2) as revenue_change_pct
FROM todays_metrics tm
CROSS JOIN yesterday_metrics ym;


-- ============================================================================
-- EXERCÍCIOS BÔNUS: Advanced Patterns
-- ============================================================================

-- BÔNUS 1: Implementar Slowly Changing Dimension Type 2
-- BÔNUS 2: Calcular Customer Lifetime Value (CLV)
-- BÔNUS 3: Detecção de anomalias em séries temporais usando média e desvio padrão
-- BÔNUS 4: Análise de cesta de compras (market basket analysis) com self-joins


-- ============================================================================
-- EXPLICAÇÕES E DICAS
-- ============================================================================

/*
WINDOW FUNCTIONS - Conceitos Chave:

1. PARTITION BY: Divide o resultado em grupos (como GROUP BY, mas sem colapsar linhas)
2. ORDER BY: Define a ordem dentro de cada partição
3. Frame Clause:
   - ROWS BETWEEN: Frame físico (número de linhas)
   - RANGE BETWEEN: Frame lógico (valores)
   - UNBOUNDED PRECEDING: Do início da partição
   - CURRENT ROW: Linha atual
   - N PRECEDING/FOLLOWING: N linhas antes/depois

4. Funções comuns:
   - ROW_NUMBER(): Numeração única
   - RANK(): Rank com gaps
   - DENSE_RANK(): Rank sem gaps
   - LAG/LEAD: Acessar linhas anteriores/posteriores
   - FIRST_VALUE/LAST_VALUE: Primeiro/último valor na janela
   - SUM/AVG/MIN/MAX: Agregações em janela
   - NTILE(n): Divide em n grupos

5. Performance:
   - Window functions são executadas DEPOIS de WHERE, GROUP BY, HAVING
   - Use índices nas colunas de PARTITION BY e ORDER BY
   - Evite múltiplas passadas reutilizando CTEs

QUERY OPTIMIZATION:
1. Evite subqueries correlacionadas -> Use JOINs
2. Evite funções em colunas indexadas no WHERE
3. Use EXPLAIN ANALYZE para entender o plano de execução
4. Crie índices compostos na ordem correta (WHERE, JOIN, ORDER BY)
5. Use LIMIT quando possível
*/


-- ============================================================================
-- RESPOSTAS E ANÁLISES
-- ============================================================================

-- As soluções acima são otimizadas e seguem best practices.
-- Compare suas soluções e entenda as diferenças!

-- Para verificar performance:
EXPLAIN ANALYZE
-- [sua query aqui]

-- Métricas importantes no EXPLAIN ANALYZE:
-- 1. Planning Time: Tempo para criar o plano
-- 2. Execution Time: Tempo real de execução
-- 3. Rows: Número de linhas processadas
-- 4. Cost: Estimativa do custo (não é tempo)
-- 5. Tipo de Scan: Seq Scan (ruim) vs Index Scan (bom)
