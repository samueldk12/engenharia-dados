# Rate Limiter

**Pergunta de Entrevista:** "Implemente um rate limiter distribuído que suporte 1000 requests/min por usuário com <1ms de overhead"

## 📋 Requisitos

### Funcionais
1. **Limit Requests**: Limitar N requests por janela de tempo
2. **Per-User**: Limites por usuário/IP/API key
3. **Multiple Windows**: Suportar múltiplas janelas (1min, 1hour, 1day)
4. **Reject or Queue**: Rejeitar ou colocar em fila requests excedentes
5. **Distributed**: Funcionar em múltiplos servidores

### Não-Funcionais
1. **Latência**: <1ms overhead (p99)
2. **Throughput**: 100K requests/sec
3. **Precisão**: ±1% de erro aceitável
4. **Memory**: O(U) onde U = número de usuários ativos
5. **Availability**: 99.99% uptime

## 🎯 Back-of-the-Envelope Calculations

```
# Assumptions
Users ativos: 1M
Requests por user: 1000/min = ~17 req/sec
Total: 1M × 17 = 17M req/sec

# Memory (Redis)
Por user: user_id (8 bytes) + counter (8 bytes) + timestamp (8 bytes) = 24 bytes
Total: 1M × 24 bytes = 24 MB ✅

# Latência
Redis GET/INCR: ~0.1ms
Network RTT: ~0.5ms
Processing: ~0.1ms
Total: ~0.7ms ✅ (<1ms)

# Redis throughput
Single instance: ~100K ops/sec
Para 17M req/sec: precisa ~170 Redis instances
Com clustering: 10 instances × 100K = 1M ops/sec ✅
```

## 🏗️ Algoritmos de Rate Limiting

### 1. Token Bucket ⭐⭐⭐⭐⭐

**Mais usado na indústria (AWS, Stripe, Cloudflare)**

```
┌──────────────────┐
│   Token Bucket   │  Capacity: 100 tokens
│                  │  Refill: 10 tokens/sec
│  ████████░░░░░   │  Current: 60 tokens
└──────────────────┘

Request → Consume 1 token
If tokens ≥ 1: ALLOW, tokens--
Else: REJECT

Refill: tokens = min(capacity, tokens + rate × elapsed)
```

**Vantagens**:
- ✅ Permite bursts (até capacity)
- ✅ Smooth rate limiting
- ✅ Memory efficient: O(1) per user

**Desvantagens**:
- ❌ Requer lock para updates (distributed)
- ❌ Clock synchronization issues

**Implementação**:
```python
class TokenBucket:
    def __init__(self, capacity: int, refill_rate: float):
        self.capacity = capacity
        self.tokens = capacity
        self.refill_rate = refill_rate  # tokens per second
        self.last_refill = time.time()

    def allow_request(self) -> bool:
        # Refill tokens
        now = time.time()
        elapsed = now - self.last_refill
        self.tokens = min(
            self.capacity,
            self.tokens + self.refill_rate * elapsed
        )
        self.last_refill = now

        # Consume token
        if self.tokens >= 1:
            self.tokens -= 1
            return True
        return False
```

**Complexidade**:
- Time: O(1)
- Space: O(1)

---

### 2. Sliding Window Log ⭐⭐⭐⭐

**Usado quando precisão é crítica**

```
Window: Last 60 seconds
Log: [t1, t2, t3, ..., tn]  (timestamps of requests)

Request at time T:
1. Remove timestamps < (T - 60)
2. If len(log) < limit: ALLOW, append T
3. Else: REJECT
```

**Vantagens**:
- ✅ Precisão perfeita
- ✅ Sem edge effects

**Desvantagens**:
- ❌ Memory intensive: O(N) per user onde N = requests na janela
- ❌ Slow: O(N) para cleanup

**Implementação**:
```python
from collections import deque

class SlidingWindowLog:
    def __init__(self, limit: int, window_sec: int):
        self.limit = limit
        self.window_sec = window_sec
        self.log = deque()  # timestamps

    def allow_request(self) -> bool:
        now = time.time()

        # Remove old timestamps - O(k)
        cutoff = now - self.window_sec
        while self.log and self.log[0] < cutoff:
            self.log.popleft()

        # Check limit
        if len(self.log) < self.limit:
            self.log.append(now)
            return True
        return False
```

**Complexidade**:
- Time: O(k) onde k = expired requests
- Space: O(N) onde N = requests na janela

---

### 3. Fixed Window Counter ⭐⭐⭐

**Mais simples, usado para casos não-críticos**

```
Window: 1 minute chunks

Minute 1: [████████] 100 requests → ALLOW
Minute 2: [████████] 100 requests → ALLOW
Edge: 99 req at 00:59 + 100 req at 01:01 = 199 req in 2 seconds! ❌
```

**Vantagens**:
- ✅ Muito simples
- ✅ Memory efficient: O(1)
- ✅ Fast: O(1)

**Desvantagens**:
- ❌ Edge effect: pode permitir 2× limit em window boundaries
- ❌ Não permite bursts

**Implementação**:
```python
class FixedWindowCounter:
    def __init__(self, limit: int, window_sec: int):
        self.limit = limit
        self.window_sec = window_sec
        self.counter = 0
        self.window_start = time.time()

    def allow_request(self) -> bool:
        now = time.time()

        # Reset counter if new window
        if now - self.window_start >= self.window_sec:
            self.counter = 0
            self.window_start = now

        # Check limit
        if self.counter < self.limit:
            self.counter += 1
            return True
        return False
```

---

### 4. Sliding Window Counter ⭐⭐⭐⭐

**Hybrid: precisão melhor que Fixed, mais eficiente que Log**

```
Current Window: 60% into minute 2

Minute 1: 80 requests
Minute 2: 60 requests (até agora)

Estimated count = 80 × (1 - 0.6) + 60 = 32 + 60 = 92
If 92 < 100: ALLOW
```

**Vantagens**:
- ✅ Boa precisão (±5%)
- ✅ Memory efficient: O(1)
- ✅ Fast: O(1)

**Desvantagens**:
- ❌ Aproximação (não exata)

**Implementação**:
```python
class SlidingWindowCounter:
    def __init__(self, limit: int, window_sec: int):
        self.limit = limit
        self.window_sec = window_sec
        self.current_window = {'start': time.time(), 'count': 0}
        self.previous_count = 0

    def allow_request(self) -> bool:
        now = time.time()

        # Check if need new window
        if now - self.current_window['start'] >= self.window_sec:
            self.previous_count = self.current_window['count']
            self.current_window = {'start': now, 'count': 0}

        # Calculate weighted count
        elapsed = now - self.current_window['start']
        weight = 1 - (elapsed / self.window_sec)
        estimated_count = (
            self.previous_count * weight +
            self.current_window['count']
        )

        # Check limit
        if estimated_count < self.limit:
            self.current_window['count'] += 1
            return True
        return False
```

---

## 🔴 Redis-Based Distributed Rate Limiter

**Problema**: Rate limiter local não funciona com múltiplos servidores

**Solução**: Usar Redis como shared counter

### Token Bucket com Redis

```python
import redis
import time

class DistributedTokenBucket:
    def __init__(
        self,
        redis_client: redis.Redis,
        capacity: int,
        refill_rate: float
    ):
        self.redis = redis_client
        self.capacity = capacity
        self.refill_rate = refill_rate

    def allow_request(self, user_id: str) -> bool:
        key = f"rate_limit:{user_id}"

        # Lua script para atomicidade (ACID)
        lua_script = """
        local key = KEYS[1]
        local capacity = tonumber(ARGV[1])
        local refill_rate = tonumber(ARGV[2])
        local now = tonumber(ARGV[3])

        -- Get current state
        local state = redis.call('HMGET', key, 'tokens', 'last_refill')
        local tokens = tonumber(state[1]) or capacity
        local last_refill = tonumber(state[2]) or now

        -- Refill tokens
        local elapsed = now - last_refill
        tokens = math.min(capacity, tokens + refill_rate * elapsed)

        -- Try to consume token
        if tokens >= 1 then
            tokens = tokens - 1
            redis.call('HMSET', key, 'tokens', tokens, 'last_refill', now)
            redis.call('EXPIRE', key, 3600)  -- TTL 1 hour
            return 1  -- ALLOW
        else
            return 0  -- REJECT
        end
        """

        result = self.redis.eval(
            lua_script,
            1,  # num keys
            key,
            self.capacity,
            self.refill_rate,
            time.time()
        )

        return bool(result)
```

**Por que Lua Script?**
- ✅ **Atomic**: Toda operação é atômica (read + update)
- ✅ **Fast**: Executa no servidor Redis (sem round-trips)
- ✅ **Consistent**: Não há race conditions

---

### Fixed Window com Redis (Mais Simples)

```python
class DistributedFixedWindow:
    def __init__(self, redis_client: redis.Redis, limit: int, window_sec: int):
        self.redis = redis_client
        self.limit = limit
        self.window_sec = window_sec

    def allow_request(self, user_id: str) -> bool:
        # Key format: rate_limit:user:123:window:1609459200
        window_start = int(time.time() // self.window_sec) * self.window_sec
        key = f"rate_limit:{user_id}:{window_start}"

        # Atomic increment
        current = self.redis.incr(key)

        # Set TTL on first request
        if current == 1:
            self.redis.expire(key, self.window_sec * 2)

        return current <= self.limit
```

**Vantagens**:
- ✅ Muito simples (2 Redis commands)
- ✅ Fast: ~0.5ms latency
- ✅ Memory efficient

---

## 📊 Comparação de Algoritmos

| Algoritmo | Precisão | Memory | Latency | Bursts | Distribuído |
|-----------|----------|--------|---------|--------|-------------|
| **Token Bucket** | ⭐⭐⭐⭐ | O(1) | O(1) | ✅ | ✅ (Redis) |
| **Sliding Window Log** | ⭐⭐⭐⭐⭐ | O(N) | O(N) | ✅ | ⚠️ (Difícil) |
| **Fixed Window** | ⭐⭐ | O(1) | O(1) | ❌ | ✅ (Redis) |
| **Sliding Counter** | ⭐⭐⭐⭐ | O(1) | O(1) | ⭐ | ✅ (Redis) |

**Recomendação**:
- **APIs públicas**: Token Bucket (permite bursts legítimos)
- **Proteção contra abuse**: Fixed Window (mais simples)
- **Billing/Quotas**: Sliding Window Log (precisão perfeita)

---

## 🚀 Otimizações

### 1. Local Cache + Redis (Hybrid)

```python
class HybridRateLimiter:
    """
    - Local cache para requests recentes (<1 second)
    - Redis para state compartilhado

    Reduz Redis calls em ~90%
    """
    def __init__(self, redis_client, capacity, refill_rate):
        self.redis_limiter = DistributedTokenBucket(...)
        self.local_cache = {}  # user_id -> (tokens, timestamp)
        self.cache_ttl = 1  # 1 second

    def allow_request(self, user_id: str) -> bool:
        # Try local cache first
        if user_id in self.local_cache:
            tokens, ts = self.local_cache[user_id]
            if time.time() - ts < self.cache_ttl:
                if tokens >= 1:
                    self.local_cache[user_id] = (tokens - 1, ts)
                    return True
                return False

        # Fallback to Redis
        allowed = self.redis_limiter.allow_request(user_id)

        # Update local cache
        if allowed:
            self.local_cache[user_id] = (self.capacity - 1, time.time())

        return allowed
```

**Ganho**: 90% redução em Redis calls, <0.1ms latency (cached)

---

### 2. Bloom Filter para Blocked Users

```python
from pybloom_live import BloomFilter

class OptimizedRateLimiter:
    """
    Se user está definitivamente bloqueado (hit limit),
    não precisa consultar Redis
    """
    def __init__(self, capacity=10000, error_rate=0.001):
        self.bloom = BloomFilter(capacity, error_rate)
        self.limiter = DistributedTokenBucket(...)

    def allow_request(self, user_id: str) -> bool:
        # Fast path: definitivamente bloqueado
        if user_id in self.bloom:
            return False

        # Slow path: consultar Redis
        allowed = self.limiter.allow_request(user_id)

        if not allowed:
            self.bloom.add(user_id)

        return allowed
```

**Ganho**: Evita Redis lookup para usuários bloqueados

---

## 🧪 Benchmarks

```python
# Single-threaded
Token Bucket (local):     1,000,000 req/sec
Fixed Window (local):     1,200,000 req/sec
Sliding Log (local):        100,000 req/sec

# Redis-based
Token Bucket (Redis):       50,000 req/sec  (limited by Redis)
Fixed Window (Redis):       80,000 req/sec
With local cache:          500,000 req/sec  (10x improvement)

# Latency (p99)
Local:                      0.01 ms
Redis:                      0.8 ms
Redis + local cache:        0.05 ms
```

---

## 📝 Perguntas de Follow-up

### Q1: Como escalar para 100M requests/sec?

**Resposta**:
```
1. Redis Cluster (sharding por user_id hash)
   - 100 shards × 1M req/sec = 100M req/sec

2. Local cache agressivo (5-10 seconds)
   - Reduz Redis load em 95%

3. Rate limit por tier
   - Free users: strict limit
   - Paid users: lenient limit
   - Distribuir load

4. CDN edge rate limiting
   - Cloudflare/Fastly rate limit
   - Antes de chegar ao seu servidor
```

### Q2: Como garantir fairness entre usuários?

**Resposta**:
```python
# Problema: Burst traffic de poucos usuários pode impactar outros

# Solução: Global rate limit + per-user limit

class FairRateLimiter:
    def __init__(self):
        self.per_user_limit = 1000  # per minute
        self.global_limit = 100000  # per minute
        self.user_limiters = {}
        self.global_counter = 0

    def allow_request(self, user_id):
        # Check global limit first
        if self.global_counter >= self.global_limit:
            return False

        # Check per-user limit
        if user_id not in self.user_limiters:
            self.user_limiters[user_id] = TokenBucket(...)

        if self.user_limiters[user_id].allow_request():
            self.global_counter += 1
            return True

        return False
```

### Q3: Como lidar com clock skew em distributed systems?

**Resposta**:
```
1. NTP Sync: Sincronizar clocks (<1ms drift)

2. Logical Clocks: Usar sequence numbers em vez de timestamps
   counter = Redis INCR
   Não depende de timestamps precisos

3. Relaxar requisitos: ±5% error é aceitável para rate limiting

4. Usar Redis como single source of truth
   Redis timestamps são consistentes
```

---

## 🎓 Conceitos-Chave

1. **Atomicidade**: Lua scripts no Redis
2. **CAP Theorem**: Escolher entre consistency e availability
3. **Caching**: Local cache para reduzir latência
4. **Sharding**: Distribuir load entre múltiplos Redis
5. **Trade-offs**: Precisão vs Performance

---

## ⚠️ Red Flags na Entrevista

❌ **Não mencionar atomicidade** (race conditions)
❌ **Esquecer de TTL no Redis** (memory leak)
❌ **Não discutir distributed challenges**
❌ **Ignorar edge effects** (Fixed Window)
❌ **Não otimizar latência** (local cache)

✅ **Bom candidato fala sobre**:
- Múltiplos algoritmos e trade-offs
- Atomicidade com Lua scripts
- Local cache para otimização
- Sharding para scale
- Clock synchronization issues

---

## 🏆 Solução Completa

Ver arquivos:
- `strategies/token_bucket.py` - Token Bucket
- `strategies/sliding_window.py` - Sliding Window Log
- `strategies/fixed_window.py` - Fixed Window Counter
- `distributed_limiter.py` - Redis-based distribuído
- `decorator.py` - Python decorator para APIs
- `benchmarks/compare.py` - Benchmark de todas estratégias

**Tempo de implementação**: 60 minutos
**Dificuldade**: ⭐⭐⭐ (Medium-Hard)
**Empresas**: Stripe, Shopify, Cloudflare, Twitter, Reddit
