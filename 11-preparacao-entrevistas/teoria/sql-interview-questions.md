# =» 100+ Questões SQL para Entrevistas de Data Engineer

## =Ë Índice

1. [Window Functions](#1-window-functions)
2. [CTEs e Recursão](#2-ctes-e-recursão)
3. [Joins Complexos](#3-joins-complexos)
4. [Agregações e GROUP BY](#4-agregações-e-group-by)
5. [Subqueries](#5-subqueries)
6. [Date/Time Manipulation](#6-datetime-manipulation)
7. [String Manipulation](#7-string-manipulation)
8. [Query Optimization](#8-query-optimization)
9. [Real Interview Questions](#9-real-interview-questions)

---

## 1. Window Functions

### Q1: Second Highest Salary
**Dificuldade:** Fácil | **Empresa:** Amazon, Microsoft

```sql
-- Encontre o segundo maior salário de cada departamento

-- Solução 1: Window Function com DENSE_RANK
SELECT
    department_id,
    employee_name,
    salary
FROM (
    SELECT
        department_id,
        employee_name,
        salary,
        DENSE_RANK() OVER (PARTITION BY department_id ORDER BY salary DESC) as rank
    FROM employees
) ranked
WHERE rank = 2;

-- Solução 2: OFFSET
SELECT
    department_id,
    salary as second_highest_salary
FROM employees
GROUP BY department_id, salary
ORDER BY department_id, salary DESC
OFFSET 1 ROW
FETCH NEXT 1 ROW ONLY;

-- Solução 3: Subquery
SELECT
    department_id,
    MAX(salary) as second_highest_salary
FROM employees
WHERE salary < (
    SELECT MAX(salary)
    FROM employees e2
    WHERE e2.department_id = employees.department_id
)
GROUP BY department_id;
```

### Q2: Running Total
**Dificuldade:** Médio | **Empresa:** Google, Facebook

```sql
-- Calcule o running total de vendas por vendedor, resetando a cada mês

SELECT
    salesperson_id,
    sale_date,
    amount,
    SUM(amount) OVER (
        PARTITION BY salesperson_id, DATE_TRUNC('month', sale_date)
        ORDER BY sale_date
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) as running_total_month
FROM sales
ORDER BY salesperson_id, sale_date;
```

### Q3: Moving Average
**Dificuldade:** Médio | **Empresa:** Netflix, Spotify

```sql
-- Calcule média móvel de 7 dias das visualizações, ignorando valores nulos

SELECT
    view_date,
    views,
    AVG(views) OVER (
        ORDER BY view_date
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ) as moving_avg_7_days,
    -- Weighted moving average
    (
        views * 0.4 +
        LAG(views, 1) OVER (ORDER BY view_date) * 0.3 +
        LAG(views, 2) OVER (ORDER BY view_date) * 0.2 +
        LAG(views, 3) OVER (ORDER BY view_date) * 0.1
    ) as weighted_moving_avg
FROM daily_views
WHERE views IS NOT NULL
ORDER BY view_date;
```

### Q4: First and Last Value
**Dificuldade:** Médio | **Empresa:** Uber, Lyft

```sql
-- Para cada usuário, compare o primeiro e último pedido

SELECT DISTINCT
    user_id,
    FIRST_VALUE(order_date) OVER w as first_order_date,
    FIRST_VALUE(order_value) OVER w as first_order_value,
    LAST_VALUE(order_date) OVER w_full as last_order_date,
    LAST_VALUE(order_value) OVER w_full as last_order_value,
    LAST_VALUE(order_date) OVER w_full - FIRST_VALUE(order_date) OVER w as days_active
FROM orders
WINDOW
    w AS (PARTITION BY user_id ORDER BY order_date),
    w_full AS (
        PARTITION BY user_id
        ORDER BY order_date
        ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
    );
```

### Q5: Percentiles
**Dificuldade:** Médio | **Empresa:** Stripe, Square

```sql
-- Calcule percentis (25, 50, 75, 95, 99) de transaction amounts por merchant

SELECT
    merchant_id,
    COUNT(*) as transaction_count,
    PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY amount) as p25,
    PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY amount) as p50_median,
    PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY amount) as p75,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY amount) as p95,
    PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY amount) as p99
FROM transactions
WHERE status = 'completed'
GROUP BY merchant_id
HAVING COUNT(*) >= 100;  -- Apenas merchants com volume significativo
```

---

## 2. CTEs e Recursão

### Q6: Recursive Employee Hierarchy
**Dificuldade:** Difícil | **Empresa:** Amazon, Google

```sql
-- Construa a hierarquia completa de organização mostrando níveis

WITH RECURSIVE employee_hierarchy AS (
    -- Base case: CEOs (sem manager)
    SELECT
        employee_id,
        employee_name,
        manager_id,
        salary,
        1 as level,
        CAST(employee_name AS VARCHAR(1000)) as path,
        CAST(employee_id AS VARCHAR(1000)) as id_path
    FROM employees
    WHERE manager_id IS NULL

    UNION ALL

    -- Recursive case
    SELECT
        e.employee_id,
        e.employee_name,
        e.manager_id,
        e.salary,
        eh.level + 1,
        eh.path || ' > ' || e.employee_name,
        eh.id_path || ',' || e.employee_id
    FROM employees e
    INNER JOIN employee_hierarchy eh ON e.manager_id = eh.employee_id
    WHERE eh.level < 10  -- Prevent infinite recursion
)
SELECT
    level,
    REPEAT('  ', level - 1) || employee_name as indented_name,
    path,
    salary,
    -- Calcular total de pessoas sob gerenciamento
    (
        SELECT COUNT(*)
        FROM employee_hierarchy eh2
        WHERE eh2.id_path LIKE eh.id_path || '%'
        AND eh2.employee_id != eh.employee_id
    ) as total_reports
FROM employee_hierarchy eh
ORDER BY path;
```

### Q7: Date Sequence Generation
**Dificuldade:** Médio | **Empresa:** Airbnb, Booking.com

```sql
-- Gere série temporal diária preenchendo gaps nos dados

WITH RECURSIVE date_series AS (
    SELECT MIN(date) as date
    FROM sales

    UNION ALL

    SELECT date + INTERVAL '1 day'
    FROM date_series
    WHERE date < (SELECT MAX(date) FROM sales)
)
SELECT
    ds.date,
    COALESCE(s.revenue, 0) as revenue,
    COALESCE(s.orders, 0) as orders,
    -- Fill forward (usar último valor conhecido)
    COALESCE(
        s.revenue,
        LAG(s.revenue) IGNORE NULLS OVER (ORDER BY ds.date),
        0
    ) as revenue_filled_forward
FROM date_series ds
LEFT JOIN (
    SELECT
        date,
        SUM(amount) as revenue,
        COUNT(*) as orders
    FROM sales
    GROUP BY date
) s ON ds.date = s.date
ORDER BY ds.date;
```

### Q8: Graph Traversal (Friends of Friends)
**Dificuldade:** Difícil | **Empresa:** Facebook, LinkedIn

```sql
-- Encontre amigos de amigos (2 graus de separação)

WITH RECURSIVE friend_network AS (
    -- Base: Amigos diretos
    SELECT
        user_id,
        friend_id,
        1 as degree,
        ARRAY[user_id, friend_id] as path
    FROM friendships
    WHERE user_id = 123

    UNION

    -- Recursivo: Amigos de amigos
    SELECT
        fn.user_id,
        f.friend_id,
        fn.degree + 1,
        fn.path || f.friend_id
    FROM friend_network fn
    JOIN friendships f ON fn.friend_id = f.user_id
    WHERE fn.degree < 2
    AND f.friend_id != ALL(fn.path)  -- Evitar ciclos
)
SELECT
    friend_id,
    MIN(degree) as closest_degree,
    COUNT(*) as num_paths
FROM friend_network
WHERE friend_id != 123  -- Excluir o usuário original
GROUP BY friend_id
ORDER BY closest_degree, num_paths DESC;
```

---

## 3. Joins Complexos

### Q9: Self-Join for Comparisons
**Dificuldade:** Médio | **Empresa:** Twitter, Reddit

```sql
-- Encontre todos os pares de usuários que postaram no mesmo tópico

SELECT
    u1.user_id as user_id_1,
    u1.username as username_1,
    u2.user_id as user_id_2,
    u2.username as username_2,
    p1.topic_id,
    t.topic_name,
    COUNT(DISTINCT p1.post_id) as posts_user_1,
    COUNT(DISTINCT p2.post_id) as posts_user_2
FROM posts p1
INNER JOIN posts p2
    ON p1.topic_id = p2.topic_id
    AND p1.user_id < p2.user_id  -- Evitar duplicatas (A,B) e (B,A)
INNER JOIN users u1 ON p1.user_id = u1.user_id
INNER JOIN users u2 ON p2.user_id = u2.user_id
INNER JOIN topics t ON p1.topic_id = t.topic_id
GROUP BY u1.user_id, u1.username, u2.user_id, u2.username, p1.topic_id, t.topic_name
HAVING COUNT(DISTINCT p1.post_id) >= 3
   AND COUNT(DISTINCT p2.post_id) >= 3
ORDER BY posts_user_1 + posts_user_2 DESC;
```

### Q10: Complex Multi-Table Join
**Dificuldade:** Médio | **Empresa:** Amazon, eBay

```sql
-- Relatório completo de vendas com informações de cliente, produto, vendedor

SELECT
    o.order_id,
    o.order_date,
    c.customer_name,
    c.customer_tier,
    c.country,
    p.product_name,
    p.category,
    s.seller_name,
    s.seller_rating,
    oi.quantity,
    oi.unit_price,
    oi.quantity * oi.unit_price as line_total,
    -- Adicionar estatísticas agregadas
    SUM(oi.quantity * oi.unit_price) OVER (PARTITION BY o.order_id) as order_total,
    COUNT(*) OVER (PARTITION BY o.order_id) as items_in_order,
    -- Customer lifetime stats
    SUM(oi.quantity * oi.unit_price) OVER (PARTITION BY c.customer_id) as customer_ltv,
    COUNT(DISTINCT o.order_id) OVER (PARTITION BY c.customer_id) as customer_order_count
FROM orders o
INNER JOIN customers c ON o.customer_id = c.customer_id
INNER JOIN order_items oi ON o.order_id = oi.order_id
INNER JOIN products p ON oi.product_id = p.product_id
INNER JOIN sellers s ON p.seller_id = s.seller_id
WHERE o.status = 'completed'
  AND o.order_date >= CURRENT_DATE - INTERVAL '90 days';
```

---

## 4. Agregações e GROUP BY

### Q11: GROUPING SETS
**Dificuldade:** Avançado | **Empresa:** Google, Databricks

```sql
-- Agregações em múltiplos níveis (país, região, cidade) em uma query

SELECT
    country,
    region,
    city,
    SUM(revenue) as total_revenue,
    COUNT(DISTINCT customer_id) as unique_customers,
    AVG(order_value) as avg_order_value,
    -- Identificar nível de agregação
    GROUPING(country) as is_all_countries,
    GROUPING(region) as is_all_regions,
    GROUPING(city) as is_all_cities
FROM sales
WHERE order_date >= '2024-01-01'
GROUP BY GROUPING SETS (
    (country, region, city),  -- Detalhado
    (country, region),        -- Por região
    (country),                -- Por país
    ()                        -- Total geral
)
ORDER BY
    COALESCE(country, 'TOTAL'),
    COALESCE(region, 'TOTAL'),
    COALESCE(city, 'TOTAL');
```

### Q12: HAVING com Subquery
**Dificuldade:** Médio | **Empresa:** PayPal, Visa

```sql
-- Encontre merchants com transações acima da média e alta taxa de chargeback

SELECT
    merchant_id,
    COUNT(*) as transaction_count,
    SUM(amount) as total_volume,
    SUM(CASE WHEN status = 'chargeback' THEN 1 ELSE 0 END)::FLOAT / COUNT(*) * 100 as chargeback_rate,
    AVG(amount) as avg_transaction
FROM transactions
WHERE transaction_date >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY merchant_id
HAVING COUNT(*) >= 100  -- Volume mínimo
   AND SUM(amount) > (
       SELECT AVG(total_volume)
       FROM (
           SELECT merchant_id, SUM(amount) as total_volume
           FROM transactions
           WHERE transaction_date >= CURRENT_DATE - INTERVAL '30 days'
           GROUP BY merchant_id
       ) merchant_volumes
   )
   AND SUM(CASE WHEN status = 'chargeback' THEN 1 ELSE 0 END)::FLOAT / COUNT(*) > 0.02  -- > 2%
ORDER BY chargeback_rate DESC;
```

### Q13: PIVOT usando CASE
**Dificuldade:** Médio | **Empresa:** Salesforce, Oracle

```sql
-- Transforme linhas em colunas: vendas mensais por categoria

SELECT
    product_category,
    SUM(CASE WHEN EXTRACT(MONTH FROM sale_date) = 1 THEN amount ELSE 0 END) as jan,
    SUM(CASE WHEN EXTRACT(MONTH FROM sale_date) = 2 THEN amount ELSE 0 END) as feb,
    SUM(CASE WHEN EXTRACT(MONTH FROM sale_date) = 3 THEN amount ELSE 0 END) as mar,
    SUM(CASE WHEN EXTRACT(MONTH FROM sale_date) = 4 THEN amount ELSE 0 END) as apr,
    SUM(CASE WHEN EXTRACT(MONTH FROM sale_date) = 5 THEN amount ELSE 0 END) as may,
    SUM(CASE WHEN EXTRACT(MONTH FROM sale_date) = 6 THEN amount ELSE 0 END) as jun,
    SUM(CASE WHEN EXTRACT(MONTH FROM sale_date) = 7 THEN amount ELSE 0 END) as jul,
    SUM(CASE WHEN EXTRACT(MONTH FROM sale_date) = 8 THEN amount ELSE 0 END) as aug,
    SUM(CASE WHEN EXTRACT(MONTH FROM sale_date) = 9 THEN amount ELSE 0 END) as sep,
    SUM(CASE WHEN EXTRACT(MONTH FROM sale_date) = 10 THEN amount ELSE 0 END) as oct,
    SUM(CASE WHEN EXTRACT(MONTH FROM sale_date) = 11 THEN amount ELSE 0 END) as nov,
    SUM(CASE WHEN EXTRACT(MONTH FROM sale_date) = 12 THEN amount ELSE 0 END) as dec,
    SUM(amount) as total_year
FROM sales
WHERE EXTRACT(YEAR FROM sale_date) = 2024
GROUP BY product_category
ORDER BY total_year DESC;
```

---

## 9. Real Interview Questions

### Q90: Spotify - User Listening Sessions
**Dificuldade:** Difícil

```sql
-- Defina sessões de escuta: gap > 30 minutos = nova sessão
-- Calcule duração média de sessão por usuário

WITH song_plays_with_gaps AS (
    SELECT
        user_id,
        song_id,
        play_timestamp,
        LAG(play_timestamp) OVER (PARTITION BY user_id ORDER BY play_timestamp) as prev_play,
        CASE
            WHEN play_timestamp - LAG(play_timestamp) OVER (PARTITION BY user_id ORDER BY play_timestamp) > INTERVAL '30 minutes'
            OR LAG(play_timestamp) OVER (PARTITION BY user_id ORDER BY play_timestamp) IS NULL
            THEN 1
            ELSE 0
        END as is_new_session
    FROM song_plays
),
sessions AS (
    SELECT
        user_id,
        song_id,
        play_timestamp,
        SUM(is_new_session) OVER (PARTITION BY user_id ORDER BY play_timestamp) as session_id
    FROM song_plays_with_gaps
),
session_stats AS (
    SELECT
        user_id,
        session_id,
        MIN(play_timestamp) as session_start,
        MAX(play_timestamp) as session_end,
        COUNT(*) as songs_played,
        EXTRACT(EPOCH FROM (MAX(play_timestamp) - MIN(play_timestamp))) / 60 as session_duration_minutes
    FROM sessions
    GROUP BY user_id, session_id
)
SELECT
    user_id,
    COUNT(*) as total_sessions,
    AVG(session_duration_minutes) as avg_session_duration_minutes,
    AVG(songs_played) as avg_songs_per_session,
    MAX(session_duration_minutes) as longest_session_minutes
FROM session_stats
GROUP BY user_id
HAVING COUNT(*) >= 5  -- Usuários ativos
ORDER BY avg_session_duration_minutes DESC;
```

### Q91: Netflix - Content Recommendation Overlap
**Dificuldade:** Difícil

```sql
-- Encontre pares de filmes frequentemente assistidos juntos (dentro de 7 dias)

WITH user_views AS (
    SELECT
        user_id,
        content_id,
        view_date,
        ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY view_date) as view_number
    FROM content_views
    WHERE view_date >= CURRENT_DATE - INTERVAL '90 days'
),
view_pairs AS (
    SELECT
        v1.user_id,
        v1.content_id as content_a,
        v2.content_id as content_b,
        v1.view_date as view_date_a,
        v2.view_date as view_date_b
    FROM user_views v1
    INNER JOIN user_views v2
        ON v1.user_id = v2.user_id
        AND v1.content_id < v2.content_id  -- Evitar duplicatas
        AND v2.view_date BETWEEN v1.view_date AND v1.view_date + INTERVAL '7 days'
)
SELECT
    content_a,
    c1.title as title_a,
    content_b,
    c2.title as title_b,
    COUNT(DISTINCT user_id) as users_viewed_both,
    AVG(view_date_b - view_date_a) as avg_days_between,
    -- Confidence metric
    COUNT(DISTINCT user_id)::FLOAT / (
        SELECT COUNT(DISTINCT user_id)
        FROM user_views
        WHERE content_id = content_a
    ) * 100 as confidence_pct
FROM view_pairs
INNER JOIN content c1 ON content_a = c1.content_id
INNER JOIN content c2 ON content_b = c2.content_id
GROUP BY content_a, c1.title, content_b, c2.title
HAVING COUNT(DISTINCT user_id) >= 50  -- Mínimo de usuários
ORDER BY users_viewed_both DESC, confidence_pct DESC
LIMIT 100;
```

### Q92: Uber - Surge Pricing Calculation
**Dificuldade:** Avançado

```sql
-- Calcule surge multiplier baseado em oferta/demanda por área e horário

WITH demand_supply AS (
    SELECT
        zone_id,
        time_bucket,
        COUNT(DISTINCT ride_request_id) as ride_requests,
        COUNT(DISTINCT CASE WHEN driver_available THEN driver_id END) as available_drivers,
        AVG(wait_time_minutes) as avg_wait_time
    FROM (
        SELECT
            zone_id,
            DATE_TRUNC('minute', request_time) -
            INTERVAL '1 minute' * (EXTRACT(MINUTE FROM request_time)::INT % 5) as time_bucket,
            ride_request_id,
            driver_id,
            driver_available,
            wait_time_minutes
        FROM ride_requests
        WHERE request_time >= CURRENT_TIMESTAMP - INTERVAL '2 hours'
    ) bucketed
    GROUP BY zone_id, time_bucket
)
SELECT
    zone_id,
    z.zone_name,
    time_bucket,
    ride_requests,
    available_drivers,
    CASE
        WHEN available_drivers = 0 THEN ride_requests * 3.0  -- Max surge
        ELSE ride_requests::FLOAT / NULLIF(available_drivers, 0)
    END as demand_supply_ratio,
    -- Surge multiplier calculation
    CASE
        WHEN available_drivers = 0 THEN 3.0
        WHEN ride_requests::FLOAT / NULLIF(available_drivers, 0) >= 5.0 THEN 2.5
        WHEN ride_requests::FLOAT / NULLIF(available_drivers, 0) >= 3.0 THEN 2.0
        WHEN ride_requests::FLOAT / NULLIF(available_drivers, 0) >= 2.0 THEN 1.5
        WHEN ride_requests::FLOAT / NULLIF(available_drivers, 0) >= 1.5 THEN 1.2
        ELSE 1.0
    END as surge_multiplier,
    avg_wait_time
FROM demand_supply ds
INNER JOIN zones z ON ds.zone_id = z.zone_id
WHERE time_bucket >= CURRENT_TIMESTAMP - INTERVAL '30 minutes'
ORDER BY zone_id, time_bucket DESC;
```

---

## =Ê Score System

Para cada questão resolvida corretamente:

- **Fácil:** 1 ponto
- **Médio:** 3 pontos
- **Difícil:** 5 pontos
- **Avançado:** 8 pontos

**Targets:**
- **Junior:** 30+ pontos
- **Mid-Level:** 60+ pontos
- **Senior:** 90+ pontos
- **Staff/Principal:** 120+ pontos

---

## =¡ Dicas para Entrevistas SQL

1. **Sempre pergunte sobre:**
   - Tamanho dos dados
   - Performance requirements
   - Se há índices
   - Frequência da query

2. **Comece simples:**
   - Solução básica primeiro
   - Depois otimize
   - Explique trade-offs

3. **Verbalize raciocínio:**
   - Explique cada passo
   - Justifique decisões
   - Mencione alternativas

4. **Teste mentalmente:**
   - Edge cases
   - Nulls
   - Duplicatas
   - Empty results

5. **Otimização:**
   - Window functions vs self-joins
   - CTEs vs subqueries
   - Índices sugeridos
   - Particionamento

---

**Pratique todas essas questões até conseguir resolver em < 15 minutos cada!**
