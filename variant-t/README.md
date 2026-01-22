# Variant T - Flash Sale Architecture (100k purchase attempts / 1s, zero 503s)

## Clean Room Declaration
> "I certify that this architecture was designed based solely on the Business Requirements and the Variant Y Baseline. I have not read, copied, or reverse-engineered the implementation code of Variant X or Variant A."

## 0) What “100k order requests” means in Variant T

• We must successfully handle 100,000 purchase attempts in the first second of a campaign (HTTP must stay 2xx; no 500/503).
• Only up to 1,000 attempts can become successful orders (SPU-level `total_sale_limit = 1000`).
• Durability rule applies only to successful orders: we never return a “success purchase” response unless the order is durable in MariaDB.
Rejections (sold out / invalid) still return HTTP 200 (benchmark-safe) but do not need an order row.

## 1) High-level architecture

Goal: make the hot path O(1), single network hop, no DB calls for the 99k+ rejected attempts.

### Components (deployed behind Nginx 10.93.0.0/24)

• Nginx (8448): TLS termination, keep-alive, routing, rate shaping, connection reuse.
• FlashSale API (Java, 8020): the only service on the critical path for purchase attempts.
• Redis (10.93.0.3): atomic gate for (a) campaign SPU-limit and (b) SKU stock, using a single Lua script.
• MariaDB (10.93.0.2:3316, user `syracuse`): durable storage for successful orders; also the source-of-truth for campaign config + starting inventory.
• Async writers (Python 30019 / C# 30020): non-critical-path consumers for post-order tasks (payment workflow, notifications, analytics). These must never block order acceptance.

### Core idea

1. Redis decides whether an attempt can succeed (atomic check of both constraints).
2. If rejected → return HTTP 200 immediately (no DB).
3. If accepted → synchronously insert the order into MariaDB (durable) and only then return HTTP 200 with success.
4. DB side-effects (updating `sold_quantity`, inventory quantities, etc.) can be async as long as no oversell is possible (Redis gate prevents oversell).

This design makes throughput depend on Redis for 100k/s (rejections are cheap) and on MariaDB only for ~1k/s (successes), which is realistic.

## 2) Invariants and consistency model

### Hard correctness invariants

A purchase attempt is “success” iff BOTH are true:

1. SPU-level sale limit not exceeded: campaign-wide remaining > 0
2. SKU persistent stock > 0: sku remaining > 0

### How Variant T enforces both simultaneously

• Maintain two counters in Redis for each active campaign:
  • `fs:camp:{campaignId}:remain` (integer, starts at `total_sale_limit`)
  • `fs:camp:{campaignId}:sku:{skuId}:remain` (integer, starts at initial available for that SKU)
• A single Redis Lua script atomically:
  • checks both counters
  • decrements both on accept
  • records a reservation marker keyed by `order_id` to enable reconciliation
• Because Lua executes atomically on Redis, all app instances share a perfectly consistent gate.

### Why this preserves “absolute integrity”

• Overselling is prevented by the Redis atomic gate (global SPU + per-SKU stock).
• MariaDB is the durable system-of-record for successful orders.
• Any mismatch that can happen due to partial failures is fail-safe (can only undersell, never oversell), and is repaired by a reconciliation job.

## 3) Data flow (Request → Response → Final persistence)

### 3.1 Request contract (benchmark-safe)

POST /v1/flashsale/{campaignId}/attempt  Body (example):

```json
  {
    "request_id": "uuid-or-ulid",
    "user_id": "uuid",
    "sku_id": "uuid"
  }
```

Response always HTTP 200, body contains outcome:

• Success:

```json
  { "result": "SUCCESS", "order_id": "uuid", "status": "CREATED" }
```

• Rejected (sold out / ended / invalid sku):

```json
  { "result": "REJECTED", "reason": "SOLD_OUT" }
```

Benchmark rule satisfied: no non-2xx responses; business semantics carried in JSON.

### 3.2 Hot path steps (Java service)

1. Validate campaign active window (cached in-process; refreshed from DB/Redis).
If not active → return `{result: REJECTED, reason: NOT_ACTIVE}` (HTTP 200).
2. Idempotency check (fast):
  • `SET fs:req:{request_id} 1 NX EX 300`
  • If already exists, return the previously computed result (see §6).
3. Atomic gate in Redis (Lua):
  • Inputs: campaignId, skuId, orderId, requestId, userId
  • Outputs: `ACCEPT` or `REJECT(reason)`
4. If `REJECT` → return immediately (HTTP 200).
5. If `ACCEPT` → durably insert order into MariaDB (single transaction, minimal writes).
6. On DB insert success:
  • Mark reservation “committed” in Redis (best-effort; not required for correctness).
  • Return `{result: SUCCESS, order_id: ...}` (HTTP 200).
7. On DB insert failure:
  • Release the Redis reservation via a second Lua script (compensating increment).
  • Return `{result: REJECTED, reason: TEMPORARY_FAILURE}` (still HTTP 200 to protect benchmark).


### 3.3 Final DB persistence model

Two layers of persistence:

• Layer A (synchronous, required for success response): insert into `orders` (+ `order_items`) so the order is recoverable after app crash 1ms after response.
• Layer B (async, eventual): update aggregate counters (`flash_sale_campaigns.sold_quantity`, `inventory.quantity/reserved_quantity`) and downstream workflows.

## 4) Redis data model and scripts

### Keys

• Campaign remaining (SPU-level):
  • `fs:camp:{campaignId}:remain` → integer
• SKU remaining (per campaign):
  • `fs:camp:{campaignId}:sku:{skuId}:remain` → integer
• Reservation marker (for reconciliation):
  • `fs:resv:{campaignId}:{orderId}` → hash: `{sku_id, user_id, ts, state}`
• Idempotency:
  • `fs:req:{request_id}` → string/json result blob (store final response)


### Lua script (conceptual)

Inputs: campaignRemainKey, skuRemainKey, reservationKey, requestKey Logic:

1. If requestKey already has stored result → return that result.
2. Read both counters.
3. If either <= 0 → store REJECT result in requestKey; return REJECT.
4. Decrement both.
5. Create reservation marker with state=PENDING.
6. Store ACCEPT result (with order_id) in requestKey; return ACCEPT.

This ensures:

• Simultaneous SPU + SKU constraint check
• Consistent result for retries
• Minimal per-request work (integer ops + small hashes)

## 5) MariaDB schema (Variant Y compatible extensions)

### Baseline tables (unchanged)

• `flash_sale_campaigns`
• `skus`
• `inventory`
• `orders`

### Extensions (additive only)

#### 5.1 Orders: add idempotency and indexing

```sql
  ALTER TABLE orders
    ADD COLUMN request_id CHAR(36) NULL,
    ADD COLUMN user_id CHAR(36) NULL,
    ADD COLUMN created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ADD UNIQUE KEY uq_orders_request_id (request_id),
    ADD KEY idx_orders_campaign_status (flash_sale_campaign_id, status);
```

#### 5.2 Order items (SKU binding for the order)

```sql
  CREATE TABLE order_items (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    order_id CHAR(36) NOT NULL,
    sku_id CHAR(36) NOT NULL,
    quantity INT NOT NULL DEFAULT 1,
    KEY idx_order_items_order (order_id),
    KEY idx_order_items_sku (sku_id)
  );
```

#### 5.3 Durable event/outbox for async processing (optional but recommended)

```sql
  CREATE TABLE order_outbox (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    order_id CHAR(36) NOT NULL,
    event_type VARCHAR(64) NOT NULL,
    payload_json TEXT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    processed_at DATETIME NULL,
    KEY idx_outbox_processed (processed_at, id)
  );
```

Note: We do not need to update `flash_sale_campaigns.sold_quantity` synchronously to remain correct; Redis gate prevents oversell. We update it async for reporting.

## 6) Idempotency and retries (required at 100k/s)

Client retries, Nginx retries, and timeouts will happen under load. Variant T guarantees:

• Same `request_id` → same response body (success with same order_id, or same rejection reason).
• MariaDB uniqueness on `orders.request_id` prevents duplicate durable orders.
• Redis `fs:req:{request_id}` caches the final result for ultra-fast repeat handling.

## 7) Campaign preparation (pre-heating) — critical for 1-second spike

Before campaign start (T-5 to T-1 minutes):

1. Read campaign row from MariaDB.
2. Compute:
  • `remain = total_sale_limit`
  • Per SKU `remain` from `inventory.quantity - reserved_quantity` (or a defined “flash-sale allocatable quantity”).
3. Write all counters to Redis in bulk (pipeline).
4. Lock down stock mutation pathways:
  • All inventory changes during campaign must go through the same system (no manual DB edits).
5. Warm JVM, connection pools, Redis scripts loaded.

At campaign end:

• Freeze Redis keys (or set TTL to `end_time + grace`).
• Run reconciliation to ensure DB aggregates match accepted orders.

## 8) Failure modes and how Variant T stays correct (and benchmark-safe)

### App instance crash after responding SUCCESS

• Order is already in MariaDB (durable) before responding → recoverable.

### Crash between Redis ACCEPT and DB insert

• Reservation exists in Redis (PENDING) but no DB order.
• Reconciliation job releases PENDING reservations older than a short TTL (e.g., 2–5s).
• This can cause temporary undersell, never oversell.

### DB transient issue

• Successful orders are only 1,000 max, so we can:
  • retry inserts (short bounded retry)
  • if still failing, compensate Redis reservation and return HTTP 200 with `REJECTED/TEMPORARY_FAILURE` (benchmark continues)


### Redis issue

• Redis is on the critical path; deploy with:
  • primary + replica + Sentinel (or cluster) on the 10.93.0.0/24 network
  • preloaded scripts
  • aggressive connection pooling
• If Redis is unavailable, return HTTP 200 with `REJECTED/SYSTEM_BUSY` (never 503).

## 9) Performance notes (why this hits 100k attempts/s)

• 99k rejections are handled entirely by Redis atomic counters + cached idempotency results.
• Only ~1k successes touch MariaDB.
• Nginx + keep-alive + small payloads reduce per-request overhead.
• Java service avoids per-request allocations (reuse buffers), uses async I/O, and maintains hot Redis connections.

## 10) Operational checklist (Variant T runbook)

• Nginx:
  • keep-alive upstream enabled
  • high worker connections
  • request body size minimal
• Java:
  • fixed-size thread pools, avoid blocking calls on event loops
  • Redis client with pipelining for non-critical operations
  • MariaDB pool sized for ~1k inserts/sec burst
• MariaDB:
  • dedicated index for `orders.request_id`
  • order insert transaction only (avoid extra joins on success path)
• Redis:
  • scripts loaded at startup
  • key naming conventions fixed; TTLs set after campaign end


## 11) Summary

Variant T achieves “100k purchase attempts in 1 second without 503” by:

• making Redis the single atomic gate for SPU-limit + SKU stock
• returning HTTP 200 for all outcomes
• writing to MariaDB only for the ≤1000 successful orders, ensuring durability before success response
• using idempotency to neutralize retries and prevent duplicates
