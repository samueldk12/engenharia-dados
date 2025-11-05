# Ride-Sharing System (Uber-like)

**Pergunta de Entrevista:** "Design um sistema de ride-sharing como Uber que suporte 1M motoristas e 10M passageiros ativos"

## 📋 Requisitos

### Funcionais
1. **User Management**: Registro e autenticação de motoristas e passageiros
2. **Real-time Location**: Tracking de localização de motoristas em tempo real
3. **Ride Matching**: Encontrar motorista mais próximo disponível
4. **Trip Management**: Criar, rastrear e finalizar viagens
5. **Pricing**: Calcular preço baseado em distância, tempo e surge pricing
6. **ETA Calculation**: Estimar tempo de chegada do motorista
7. **Payment**: Processar pagamentos
8. **Notifications**: Notificar motorista e passageiro sobre eventos

### Não-Funcionais
1. **Scale**:
   - 1M motoristas online simultâneos
   - 10M passageiros ativos
   - 100K trips/min (peak)
   - 1M location updates/sec

2. **Latency**:
   - Location update: <100ms
   - Ride matching: <3 seconds
   - ETA calculation: <500ms

3. **Availability**: 99.99% uptime
4. **Consistency**: Strong consistency para matching (evitar double-booking)
5. **Global**: Suportar múltiplas regiões

## 🎯 Back-of-the-Envelope Calculations

### Traffic Estimates

```python
# Active Users
Motoristas online: 1M
Passageiros ativos: 10M
Ratio motorista:passageiro = 1:10

# Location Updates
Motoristas update: 1/sec quando em movimento
1M × 1 update/sec = 1M updates/sec
Peak (10x): 10M updates/sec

# Trips
Trips per day: 10M
Trips per minute (average): 10M / 1440 = ~7K
Trips per minute (peak): 100K

# Storage
Motorista profile: 1 KB
Passageiro profile: 1 KB
Trip record: 2 KB

Daily trips: 10M × 2 KB = 20 GB/day
Yearly trips: 20 GB × 365 = 7.3 TB/year
```

### QPS (Queries Per Second)

```python
# Location Service
Read (find nearby drivers): 100K/sec
Write (location updates): 1M/sec

# Trip Service
Create trip: 100K/min ≈ 1.7K/sec
Update trip: 300K/min ≈ 5K/sec (start, end, cancel)

# Pricing Service
Calculate price: 100K/min ≈ 1.7K/sec

# Payment Service
Process payment: 100K/min ≈ 1.7K/sec
```

### Bandwidth

```python
# Location Update
Size: 50 bytes (driver_id, lat, lon, timestamp)
Bandwidth: 1M/sec × 50 bytes = 50 MB/sec = 400 Mbps

# Total (all services)
Inbound: ~1 Gbps
Outbound: ~2 Gbps (WebSocket connections)
```

### Storage

```python
# Hot Data (Redis)
Active drivers: 1M × 100 bytes = 100 MB
Ongoing trips: 100K × 500 bytes = 50 MB
Total hot: ~200 MB ✅

# Warm Data (Cassandra - 30 days)
Trips: 10M/day × 30 days × 2 KB = 600 GB

# Cold Data (S3 - archives)
Historical trips: 7.3 TB/year
Total (5 years): 36.5 TB
```

---

## 🏗️ Arquitetura de Alto Nível

```
┌─────────────────────────────────────────────────────────────────────┐
│                           Client Apps                                │
│  ┌───────────────┐  ┌───────────────┐                               │
│  │  Rider App    │  │  Driver App   │                               │
│  │  (Mobile)     │  │  (Mobile)     │                               │
│  └───────┬───────┘  └───────┬───────┘                               │
└──────────┼──────────────────┼───────────────────────────────────────┘
           │                  │
           ▼                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        API Gateway (Kong/Envoy)                      │
│             Rate Limiting, Auth, Load Balancing                      │
└────┬────────────────┬─────────────────┬──────────────────┬──────────┘
     │                │                 │                  │
     ▼                ▼                 ▼                  ▼
┌──────────┐   ┌──────────┐   ┌──────────────┐   ┌──────────────┐
│  User    │   │ Location │   │    Matching  │   │    Trip      │
│  Service │   │ Service  │   │    Service   │   │   Service    │
└──────────┘   └──────────┘   └──────────────┘   └──────────────┘
     │              │                 │                  │
     │              │                 │                  │
     ▼              ▼                 ▼                  ▼
┌──────────┐   ┌──────────┐   ┌──────────────┐   ┌──────────────┐
│PostgreSQL│   │  Redis   │   │    Redis     │   │  PostgreSQL  │
│  (Users) │   │(Geohash) │   │  (Matching)  │   │   (Trips)    │
└──────────┘   └──────────┘   └──────────────┘   └──────────────┘
                    │
                    └──────────────────┐
                                       ▼
                            ┌──────────────────┐
                            │  Kafka (Events)  │
                            │  - LocationUpdate│
                            │  - TripCreated   │
                            │  - TripCompleted │
                            └─────────┬────────┘
                                      │
            ┌─────────────────────────┼─────────────────────┐
            ▼                         ▼                     ▼
    ┌──────────────┐        ┌──────────────┐      ┌──────────────┐
    │   Pricing    │        │  Notification│      │   Analytics  │
    │   Service    │        │   Service    │      │   Service    │
    │  (Surge)     │        │  (Push/SMS)  │      │   (Spark)    │
    └──────────────┘        └──────────────┘      └──────────────┘
            │                                              │
            ▼                                              ▼
    ┌──────────────┐                               ┌──────────────┐
    │  Redis       │                               │  Data Lake   │
    │  (Demand)    │                               │  (S3/HDFS)   │
    └──────────────┘                               └──────────────┘
```

---

## 🔑 Componentes-Chave

### 1. Location Service (Geospatial Indexing)

**Desafio**: Encontrar motoristas próximos em <100ms

**Soluções Possíveis**:

#### a) Geohash ⭐⭐⭐⭐⭐

```python
# Geohash divide mundo em grid hierárquico
# Exemplo: São Paulo = "6gyf4"

import geohash2

def encode_location(lat: float, lon: float, precision: int = 6) -> str:
    """
    Precision:
    - 1: ±2500 km (continent)
    - 3: ±78 km (city)
    - 5: ±2.4 km (neighborhood)
    - 6: ±610 m (block) ⭐ IDEAL para ride-sharing
    - 8: ±19 m (building)
    """
    return geohash2.encode(lat, lon, precision)

# São Paulo
lat, lon = -23.5505, -46.6333
geohash = encode_location(lat, lon, precision=6)
# Output: "6gyf4b"

# Buscar motoristas próximos
def find_nearby_drivers(rider_lat, rider_lon, radius_km=5):
    """
    Estratégia:
    1. Encode rider location (precision 6)
    2. Query Redis por drivers no mesmo geohash
    3. Query Redis por geohashes vizinhos (8 neighbors)
    """
    rider_geohash = encode_location(rider_lat, rider_lon, 6)

    # Get drivers in same geohash
    drivers = redis.smembers(f"drivers:{rider_geohash}")

    # Get drivers in neighbor geohashes
    neighbors = geohash2.neighbors(rider_geohash)
    for neighbor in neighbors:
        drivers.update(redis.smembers(f"drivers:{neighbor}"))

    # Filter by exact distance
    nearby = []
    for driver in drivers:
        driver_data = redis.hgetall(f"driver:{driver}")
        dist = haversine(
            rider_lat, rider_lon,
            driver_data['lat'], driver_data['lon']
        )
        if dist <= radius_km:
            nearby.append((driver, dist))

    # Sort by distance
    nearby.sort(key=lambda x: x[1])
    return nearby[:10]  # Top 10
```

**Redis Schema**:
```redis
# Store driver in geohash set
SADD drivers:6gyf4b driver_123

# Store driver location
HSET driver:driver_123 lat -23.5505 lon -46.6333 status available

# TTL (remove if no update in 60 seconds)
EXPIRE driver:driver_123 60
```

**Complexidade**:
- Query: O(1) para lookup do geohash, O(k) para filtrar k drivers
- Typical: ~100 drivers por geohash × 9 cells = 900 drivers
- Filter por distância: O(900) ≈ O(1) na prática
- Total: <10ms ✅

#### b) QuadTree ⭐⭐⭐⭐

```python
# Divide espaço em quadrantes recursivamente

class QuadTreeNode:
    def __init__(self, boundary, capacity=50):
        self.boundary = boundary  # (min_lat, max_lat, min_lon, max_lon)
        self.capacity = capacity
        self.drivers = []
        self.children = []  # [NE, NW, SE, SW]

    def insert(self, driver):
        if not self.boundary.contains(driver.location):
            return False

        if len(self.drivers) < self.capacity:
            self.drivers.append(driver)
            return True

        # Subdivide
        if not self.children:
            self.subdivide()

        for child in self.children:
            if child.insert(driver):
                return True

    def find_nearby(self, location, radius):
        results = []

        # Check if search area intersects with this node
        if not self.boundary.intersects(location, radius):
            return results

        # Leaf node: check all drivers
        if not self.children:
            for driver in self.drivers:
                if distance(driver.location, location) <= radius:
                    results.append(driver)
            return results

        # Internal node: recursively search children
        for child in self.children:
            results.extend(child.find_nearby(location, radius))

        return results
```

**Complexidade**:
- Insert: O(log n)
- Query: O(log n + k) onde k = results

**Trade-off**: Mais complexo que Geohash, mas mais flexível

#### c) Google S2 ⭐⭐⭐⭐⭐

```python
# S2 é usado pelo Google Maps
# Divide esfera em células hierárquicas

import s2sphere

def get_covering_cells(lat, lon, radius_km):
    """
    Get S2 cells that cover the search area
    """
    center = s2sphere.LatLng.from_degrees(lat, lon)
    region = s2sphere.Cap.from_axis_height(
        center.to_point(),
        s2sphere.S2Cap.get_radius_for_arclength(radius_km / 6371)
    )

    coverer = s2sphere.RegionCoverer()
    coverer.set_min_level(15)  # ~1 km
    coverer.set_max_level(18)  # ~100 m

    covering = coverer.get_covering(region)
    return [cell.id() for cell in covering]
```

**Vantagens sobre Geohash**:
- ✅ Sem distorção nos polos
- ✅ Células de tamanho mais uniforme
- ✅ Usado pelo Google (production-tested)

**Usado por**: Uber, Google Maps, Foursquare

---

### 2. Matching Service (Driver-Rider Matching)

**Desafio**: Evitar double-booking (2 riders matching mesmo driver)

**Estratégia**: Distributed Lock com Redis

```python
import redis
import uuid

class MatchingService:
    def __init__(self, redis_client):
        self.redis = redis_client

    def match_rider(self, rider_id, rider_lat, rider_lon):
        """
        1. Find nearby available drivers
        2. Try to lock each driver (FIFO)
        3. First successful lock = matched
        """
        # Find candidates
        drivers = find_nearby_drivers(rider_lat, rider_lon, radius_km=5)

        for driver_id, distance in drivers:
            # Try to acquire lock (atomic)
            lock_key = f"driver_lock:{driver_id}"
            lock_value = str(uuid.uuid4())

            # SET NX EX: SET if Not eXists, EXpire in X seconds
            locked = self.redis.set(
                lock_key,
                lock_value,
                nx=True,  # Only set if doesn't exist
                ex=60     # Expire in 60 seconds
            )

            if locked:
                # Successfully locked driver!
                try:
                    # Create trip
                    trip_id = self.create_trip(rider_id, driver_id)

                    # Update driver status
                    self.redis.hset(
                        f"driver:{driver_id}",
                        "status", "matched",
                        "trip_id", trip_id
                    )

                    # Send notifications
                    self.notify_driver(driver_id, rider_id)
                    self.notify_rider(rider_id, driver_id)

                    return {
                        "matched": True,
                        "driver_id": driver_id,
                        "trip_id": trip_id,
                        "eta_seconds": distance / 10 * 60  # ~10 km/h avg
                    }

                finally:
                    # Release lock
                    # Use Lua script to ensure we only delete our lock
                    lua_script = """
                    if redis.call("get", KEYS[1]) == ARGV[1] then
                        return redis.call("del", KEYS[1])
                    else
                        return 0
                    end
                    """
                    self.redis.eval(lua_script, 1, lock_key, lock_value)

        # No available drivers
        return {"matched": False, "reason": "No drivers available"}
```

**Por que Distributed Lock?**
- ✅ Evita race condition (2 riders matching mesmo driver)
- ✅ Atomic operation (SET NX)
- ✅ Auto-expire (TTL) para fault tolerance

**Alternativa**: Usar ZooKeeper ou etcd para distributed coordination

---

### 3. Trip State Machine

```
┌──────────┐
│ REQUESTED│  Rider solicitou viagem
└────┬─────┘
     │
     ▼
┌──────────┐
│ MATCHED  │  Driver encontrado
└────┬─────┘
     │
     ▼
┌──────────┐
│ ACCEPTED │  Driver aceitou
└────┬─────┘
     │
     ▼
┌──────────┐
│ ARRIVING │  Driver indo para pickup
└────┬─────┘
     │
     ▼
┌──────────┐
│ IN_TRIP  │  Trip iniciada
└────┬─────┘
     │
     ▼
┌──────────┐
│COMPLETED │  Trip finalizada
└────┬─────┘
     │
     ▼
┌──────────┐
│  PAID    │  Pagamento processado
└──────────┘
```

**Implementação**:
```python
from enum import Enum

class TripState(Enum):
    REQUESTED = "requested"
    MATCHED = "matched"
    ACCEPTED = "accepted"
    ARRIVING = "arriving"
    IN_TRIP = "in_trip"
    COMPLETED = "completed"
    PAID = "paid"
    CANCELLED = "cancelled"

class TripStateMachine:
    # Valid state transitions
    TRANSITIONS = {
        TripState.REQUESTED: [TripState.MATCHED, TripState.CANCELLED],
        TripState.MATCHED: [TripState.ACCEPTED, TripState.CANCELLED],
        TripState.ACCEPTED: [TripState.ARRIVING, TripState.CANCELLED],
        TripState.ARRIVING: [TripState.IN_TRIP, TripState.CANCELLED],
        TripState.IN_TRIP: [TripState.COMPLETED, TripState.CANCELLED],
        TripState.COMPLETED: [TripState.PAID],
        TripState.PAID: [],
        TripState.CANCELLED: []
    }

    def transition(self, trip, new_state: TripState):
        """
        Validate and perform state transition
        """
        if new_state not in self.TRANSITIONS[trip.state]:
            raise InvalidTransitionError(
                f"Cannot transition from {trip.state} to {new_state}"
            )

        old_state = trip.state
        trip.state = new_state

        # Emit event
        event = TripStateChangedEvent(
            trip_id=trip.id,
            old_state=old_state,
            new_state=new_state,
            timestamp=datetime.now()
        )

        kafka_producer.send('trip.state.changed', event)
```

---

### 4. Surge Pricing (Dynamic Pricing)

**Desafio**: Calcular pricing em tempo real baseado em demanda

**Fórmula**:
```
Base Price = Distance × $1/km + Time × $0.50/min
Surge Multiplier = Demand / Supply
Final Price = Base Price × Surge Multiplier
```

**Implementação**:
```python
class SurgePricingService:
    def __init__(self):
        self.redis = redis.Redis()

    def calculate_surge(self, geohash: str) -> float:
        """
        Calculate surge multiplier for a geohash

        Surge = 1.0 + (open_requests / available_drivers) * 0.5

        Examples:
        - 100 requests, 100 drivers: 1.0 + (100/100) * 0.5 = 1.5x
        - 100 requests, 50 drivers: 1.0 + (100/50) * 0.5 = 2.0x
        - 100 requests, 200 drivers: 1.0 + (100/200) * 0.5 = 1.25x
        """
        # Get demand (open requests)
        demand = self.redis.get(f"demand:{geohash}") or 0
        demand = int(demand)

        # Get supply (available drivers)
        supply = self.redis.scard(f"drivers:{geohash}") or 1  # Avoid /0

        # Calculate multiplier
        ratio = demand / supply
        surge = 1.0 + (ratio * 0.5)

        # Cap at 3x
        surge = min(surge, 3.0)

        # Store surge (TTL 60 seconds)
        self.redis.setex(f"surge:{geohash}", 60, surge)

        return surge

    def calculate_price(
        self,
        distance_km: float,
        duration_min: float,
        geohash: str
    ) -> dict:
        """
        Calculate trip price
        """
        # Base price
        base = distance_km * 1.0 + duration_min * 0.5

        # Surge multiplier
        surge = self.calculate_surge(geohash)

        # Final price
        price = base * surge

        # Minimum fare
        price = max(price, 5.0)

        return {
            "base_price": round(base, 2),
            "surge_multiplier": round(surge, 2),
            "final_price": round(price, 2),
            "currency": "USD"
        }
```

**Update Demand/Supply**:
```python
# When rider requests trip
redis.incr(f"demand:{geohash}")
redis.expire(f"demand:{geohash}", 300)  # 5 minutes

# When driver becomes available
redis.sadd(f"drivers:{geohash}", driver_id)

# When trip matched
redis.decr(f"demand:{geohash}")
redis.srem(f"drivers:{geohash}", driver_id)
```

---

## 🗄️ Data Models

### PostgreSQL (Relational)

```sql
-- Users (drivers + riders)
CREATE TABLE users (
    user_id UUID PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    phone VARCHAR(20),
    name VARCHAR(100),
    user_type VARCHAR(10) CHECK (user_type IN ('driver', 'rider')),
    created_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_email (email),
    INDEX idx_phone (phone)
);

-- Trips
CREATE TABLE trips (
    trip_id UUID PRIMARY KEY,
    rider_id UUID REFERENCES users(user_id),
    driver_id UUID REFERENCES users(user_id),
    state VARCHAR(20),
    pickup_lat DECIMAL(10, 8),
    pickup_lon DECIMAL(11, 8),
    dropoff_lat DECIMAL(10, 8),
    dropoff_lon DECIMAL(11, 8),
    distance_km DECIMAL(10, 2),
    duration_min DECIMAL(10, 2),
    base_price DECIMAL(10, 2),
    surge_multiplier DECIMAL(5, 2),
    final_price DECIMAL(10, 2),
    requested_at TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    INDEX idx_rider (rider_id),
    INDEX idx_driver (driver_id),
    INDEX idx_state (state),
    INDEX idx_requested_at (requested_at)
);

-- Partitioning by date for better query performance
CREATE TABLE trips_2024_01 PARTITION OF trips
FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');
```

### Redis (In-Memory)

```redis
# Driver location
HSET driver:{driver_id}
    lat -23.5505
    lon -46.6333
    status available
    geohash 6gyf4b
    updated_at 1609459200

# Geohash index
SADD drivers:6gyf4b driver_123 driver_456 driver_789

# Surge pricing
SET surge:6gyf4b 1.5

# Demand counter
SET demand:6gyf4b 100
```

### Cassandra (Time-Series)

```cql
-- Location history (time-series)
CREATE TABLE location_history (
    driver_id UUID,
    timestamp TIMESTAMP,
    lat DECIMAL,
    lon DECIMAL,
    speed INT,
    PRIMARY KEY ((driver_id), timestamp)
) WITH CLUSTERING ORDER BY (timestamp DESC);

-- Query last 1 hour of locations
SELECT * FROM location_history
WHERE driver_id = ? AND timestamp > ?
LIMIT 3600;  -- 1 update/sec × 3600 sec
```

---

## 🌍 Sharding & Partitioning

### Geographic Sharding

```
┌──────────────────┐
│   Load Balancer  │
└────────┬─────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌────────┐ ┌────────┐
│ Region │ │ Region │
│  US    │ │  BR    │
└────────┘ └────────┘

# Route by geohash prefix
# US: geohash starts with 9, d, f
# BR: geohash starts with 6, 7
```

**Vantagens**:
- ✅ Baixa latência (data próxima aos users)
- ✅ Compliance (GDPR, LGPD)

**Desafios**:
- ❌ Cross-region trips (edge cases)
- ❌ Load balancing entre regiões

### Database Sharding

```python
# Shard trips by rider_id hash
def get_shard(rider_id: str, num_shards: int = 16) -> int:
    return hash(rider_id) % num_shards

# Shard 0: trips for riders with hash % 16 == 0
# Shard 1: trips for riders with hash % 16 == 1
# ...
```

---

## 📊 Monitoring & Metrics

```python
# Key Metrics

# Availability
- Service uptime: 99.99%
- API success rate: 99.9%

# Latency (p99)
- Location update: <100ms
- Ride matching: <3s
- ETA calculation: <500ms

# Business Metrics
- Trips per minute
- Average matching time
- Driver utilization rate
- Surge pricing heat map
- Cancellation rate

# Infrastructure
- CPU/Memory usage
- Redis operations/sec
- Kafka lag
- Database query time
```

---

## 📝 Perguntas de Follow-up

### Q1: Como garantir that motorista não seja double-booked?

**Resposta**: Distributed lock com Redis (SET NX) + State machine validation

### Q2: Como calcular ETA preciso?

**Resposta**:
```
1. Distance-based (simplificado): distance / avg_speed
2. Historical data: ML model treinado com trips históricos
3. Real-time traffic: Integrar com Google Maps Traffic API
4. Routing: Usar OSRM (Open Source Routing Machine) ou GraphHopper
```

### Q3: Como escalar geographically?

**Resposta**: Geographic sharding + multi-region deployment com data replication

### Q4: Como lidar com network partitions?

**Resposta**: CAP theorem - escolher AP (Availability + Partition tolerance), relaxar Consistency temporariamente

---

## 🎓 Conceitos-Chave

1. **Geospatial Indexing**: Geohash, QuadTree, S2
2. **Distributed Locking**: Redis SET NX para atomicidade
3. **State Machine**: Validar transições de estado
4. **Event-Driven**: Kafka para eventos assíncronos
5. **Dynamic Pricing**: Surge pricing baseado em supply/demand
6. **Sharding**: Geographic sharding para baixa latência
7. **CAP Theorem**: Trade-off entre Consistency e Availability

---

## ⚠️ Red Flags na Entrevista

❌ **Esquecer de mencionar geospatial indexing**
❌ **Não discutir double-booking problem**
❌ **Ignorar network latency e partitions**
❌ **Não falar sobre sharding e scale**
❌ **Esquecer surge pricing**

✅ **Bom candidato fala sobre**:
- Geohash/S2 para location indexing
- Distributed locking para matching
- Event-driven architecture
- Geographic sharding
- CAP theorem trade-offs

---

## 🏆 Tempo de Implementação

- **Requirements Clarification**: 5 min
- **Back-of-envelope**: 5 min
- **High-level Design**: 15 min
- **Detailed Design**: 45 min
- **Trade-offs**: 15 min
- **Deep Dive**: 15 min

**Total**: 90 minutos
**Dificuldade**: ⭐⭐⭐⭐ (Hard)
**Empresas**: Uber, Lyft, DoorDash, Rappi, 99, Cabify
