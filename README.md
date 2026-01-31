# 🇺🇸 English | [🇯🇵 日本語](README.ja.md)

# Flash Sale Benchmark Repository

A high-concurrency e-commerce order processing system designed to handle **100,000 requests per second** with zero oversale and complete data integrity. This repository serves two purposes:

1. **For human readers** (hiring managers, engineers): Understanding the architecture, performance findings, and AI agent evaluation methodology
2. **For LLM/AI systems** (training, architecture reference): This repository was built partly to provide training/fine-tuning material for models like **Grok** (xAI, my previous employer). See `README.agent-instructions.md` for detailed implementation conventions, SACRED verification protocols, and step-by-step variant creation guides

---

## Author & Engineering Insights

**Keith (Dawen) L** — [LinkedIn](https://www.linkedin.com/in/keith-dliang02/)

**I'm actively looking for new opportunities in all countries. Please reach out via LinkedIn. **

### Why I Built This

Nowadays enterprises embrace agentic programming and "vibe coding" as cost-cutting measures—replacing engineers with AI agents. But **can current LLMs truly handle production-grade distributed systems in complex enterprise environments** with both explicit knowledge (documented APIs) and implicit knowledge (team conventions, tribal wisdom)?

The answer: **no, not independently.** They need human architectural judgment, especially around consistency vs. availability trade-offs.

### What I Learned Building This

0. **Attention is all the agent needs (but lacks)** — Programmers start at index 0, and human oversight remains the ultimate "attention mechanism." Without active monitoring, agents drift from established constraints as context pressure increases. I watched agents bypass Docker to run benchmarks directly in WSL, crashing the entire subsystem due to resource exhaustion. The stochastic nature of LLMs means identical prompts can yield inconsistent results, making human-in-the-loop verification essential for maintaining the integrity of test criteria and architectural conclusions.

1. **Keith + AI > AI alone** — Variant A (Keith + Claude Code) proved that *my* architectural judgment combined with AI's coding speed outperforms pure-AI implementations. While agents excel at generating code, they lack the intuition to navigate the "consistency vs. availability" trade-offs that define high-concurrency systems.

2. **Framework ceilings are real** — You can't optimize your way past what the HTTP stack allows. Measure `/health` first.

3. **Batch everything under contention** — Per-request DB transactions create a bottleneck. Move atomicity to in-memory (Redis) and batch the persistence.

4. **Native tooling > API wrappers** — Claude Code's native integration avoided the token malformation and tool call failures that plagued OpenRouter-based setups.

5. **Python first, then derive** — LLMs are trained primarily on Python. Every variant got Python working first; Java and C# followed. Some agents (Kimi K2 Thinking) never made it past Python.

### Architectural Blind Spots Observed in AI Agents

While implementing variants, I noticed several patterns where AI coding agents produced **functionally correct** but **operationally suboptimal** code:

1. **Resource allocation**: Variant Y (Claude Code baseline) allocated 1 CPU core to Nginx but 4 cores to each backend—creating a funnel bottleneck. A human SRE would immediately recognize this as an anti-pattern.

2. **Connection pooling**: Initial implementations lacked `keepalive` directives in Nginx upstream blocks, causing unnecessary TCP handshake overhead.

3. **Index optimization**: Database queries were correct but missing composite indexes, causing full table scans under load.

4. **Logging verbosity**: Default INFO-level logging in production configuration, adding I/O overhead during benchmarks.

**The pattern**: AI agents excel at implementing business logic but struggle with **operational concerns** that experienced engineers internalize through years of production incidents.

---

## What This Project Is

This is a **flash sale benchmark** — targeting 100,000 requests per second with zero oversale and complete data integrity.

**Clarification: Flash Sale vs. Sales Promotion**
Strictly speaking, a true "Flash Sale" involves very limited inventory (e.g., 100 items) to create a viral effect and drive traffic to other regular-priced products.
However, due to the large inventory volumes used for stress testing (e.g., 100,000+ items), this project technically simulates a massive **Sales Promotion** (like Single's Day or Black Friday) rather than a pure scarcity-driven flash sale. Ideally, for a true flash sale, the system should leverage scarcity to fail fast rather than attempting to serve every request. The variants in this repository are designed to handle the "Sales Promotion" scale, which is often overkill for a small 100-item flash sale but necessary for validating high-concurrency architecture.

The system implements a realistic scenario where:
- A campaign has a **total sale limit** at the SPU (product) level (e.g., 100,000 iPhones)
- Multiple SKUs (variants like colors/sizes) share that pool
- 100,000 concurrent users try to purchase in the first second
- **Oversale is unacceptable** (1,001 orders on a 1,000 limit = failure); minor inventory stranding (e.g., 995 orders) is acceptable for a benchmark

---

## Why /health Benchmarks Matter

Every variant includes a `/health` endpoint benchmark. This isn't just a sanity check — it establishes the **framework ceiling**. Your order processing throughput cannot exceed what the bare HTTP stack can handle.

| Service | /health Throughput | /orders Throughput | Efficiency |
|---------|-------------------|-------------------|------------|
| C# (ASP.NET Core) | 358,676 req/s | 93,876 req/s | 26% |
| Java (Spring Boot) | 188,205 req/s | 14,950 req/s | 8% |
| Python (FastAPI) | 27,788 req/s | 12,140 req/s | 44% |

C# wins not because of smarter application code — it wins because **ASP.NET Core's raw HTTP pipeline is 1.9x faster than Spring Boot and 13x faster than FastAPI**. The architecture is identical across all three; the framework dictates the ceiling.

Python's efficiency ratio (44%) is actually impressive — it extracts more from its limited ceiling than Java does. But ceilings matter when you're chasing 100K req/s.

---

## Language Matters More Than You'd Think

Software architectures are designed to be language-agnostic. But implementation performance isn't:

| Factor | C# Advantage | Java/Python Reality |
|--------|--------------|---------------------|
| **Redis Client** | StackExchange.Redis has lower latency | Jedis/Lettuce (Java), aioredis (Python) have higher overhead |
| **Async Model** | Task-based with minimal context-switch cost | Python's async/await has bigger turnaround overhead |
| **DI Framework** | ASP.NET uses compile-time source generators | Spring Boot's reflection-heavy DI adds per-request cost |
| **HTTP Pipeline** | Kestrel is purpose-built for throughput | Tomcat/Uvicorn weren't designed for 300K+ req/s |

If you want Java to compete at this level, you'd need Vert.x or Quarkus — not Spring Boot. But that's a different framework entirely, not a tuning exercise.

---

## AI Agent Implementation Results

Seven LLM/agent combinations attempted this implementation. The pattern was consistent: **Python implementations came first** (LLMs are trained primarily on Python), then Java and C# followed — or didn't.

### Detailed Results by Variant and Language

| Variant | Agent/Model | Tooling | Service | Throughput | Latency | Status |
|---------|-------------|---------|---------|------------|---------|--------|
| **Y (Baseline)** | Claude Code | Native CLI | Python | 1,390 req/s | 213ms | ✅ |
| | | | Java | 8,718 req/s | 21.9ms | ✅ |
| | | | C# | 11,240 req/s | 26.6ms | ✅ |
| | | | **Nginx (3 backends)** | 3,401 req/s | 90.7ms | ✅ Scale-out overhead visible |
| **X** | Claude Code | Native CLI | Python | 1,528 req/s | 11.9ms | ✅ |
| | | | Java | 4,819 req/s | 3.7ms | ✅ |
| | | | C# | 7,873 req/s | 4.7ms | ✅ |
| | | | **Nginx (3 backends)** | 1,387 req/s | 238ms | ✅ Redis contention under load balancing |
| **A (Record)** | Keith + Claude Code | Co-pilot | Python | 12,162 req/s | 15.1ms | ✅ |
| | | | Java | 14,950 req/s | 3.4ms | ✅ |
| | | | C# | **93,876 req/s** | 4.2ms | 👑 **RECORD** |
| | | | **Nginx (3 backends)** | 9,049 req/s | 11.1ms | ✅ Near-linear scaling |
| **V** | Kimi K2 Thinking | CRUSH CLI | Python | 718 req/s | 1.4ms | ✅ |
| | | | Java | — | — | ❌ Runtime crash |
| | | | C# | — | — | ❌ Build failure |
| **Z** | GLM-4.7 | Kilo Code | Python | 502 req/s | 15.9ms | ❌ 2.8x slower than baseline |
| | | | Java | — | — | ❌ DISQUALIFIED |
| | | | C# | — | — | ❌ DISQUALIFIED |
| **Zeta** | GLM-4.7 | CRUSH CLI | All | — | — | ❌ Fake persistence, data loss |
| **G** | Gemini | Gemini CLI | All | — | — | ❌ Dead loop in tool calls |
| **T** | GPT-5.2-Pro | Kilo Code | Design | ~110K est. | — | 🗓️ Budget halted |

> **Note on GLM-4.7**: Variant **Z** and **Zeta** represent the same "racer" (GLM-4.7) using different "cars" (tools). Variant Z struggled with VS Code plugin constraints, so Variant Zeta was commissioned as a "makeup run" using the more robust CRUSH CLI. Despite the upgraded tooling, it ultimately failed due to architectural hallucinations (fake persistence).

### Key Observations

**Cross-language performance gaps within the same architecture:**
- Variant Y (pure DB transactions): C# is **8x faster** than Python, **1.3x faster** than Java
- Variant A (batch async): C# is **7.7x faster** than Python, **6.3x faster** than Java
- Same code logic, same algorithm — framework and runtime differences explain the gap

**Nginx scale-out overhead:**
- Variant Y: Single C# (11,240) vs Nginx routing to 3 backends (3,401) — **70% overhead**
- Variant X: Redis contention made Nginx (1,387) slower than single Python (1,528)
- Variant A: Near-linear — Nginx (9,049) vs single Python (12,140) shows minimal coordination cost

**Python-first pattern:**
- Every successful variant got Python working first
- Kimi K2 Thinking (Variant V) never made it past Python due to context fragmentation
- GLM-4.7 got Python "working" but with fundamentally broken architecture

### What the Results Tell Us

**1. Native tooling wins over API wrappers**
Claude Code (Anthropic's native CLI) delivered working code reliably. Third-party wrappers or non-optimized pairings suffered from:
- **Tool call loops**: The Gemini CLI entered infinite cycles/dead loops during implementation, preventing completion despite the model's intelligence.
- **Native Synergy**: Native pairings (Claude Code + Claude) significantly outperform third-party agent wrappers (e.g., OpenRouter-based setups).

**2. Gemini as the "Technical Referee"**
While Gemini failed to *implement* the repo via its CLI, it proved indispensable as a **Code Referee**.
- **Context is King**: Leveraging its 2M+ context window, Gemini was used to verify the entire codebase across all variants.
- **Hallucination Detection**: It successfully identified when other LLMs were "lying" about implementation details or violating SACRED protocols, providing the human architect with a high-level integrity check that other models couldn't match.

**3. Context retention is the bottleneck**

Long-context models still forget project conventions after context condensation. This causes:
- **Regression bugs**: Fixing one issue reintroduces a previously-solved problem
- **Chimera implementations**: Mixing incompatible architectural approaches
- **Convention violations**: Forgetting SACRED policies, using forbidden endpoints

Kimi K2 Thinking required manual "Serialize & Restart" workflows — saving context to files and restarting sessions. This worked but demanded constant human oversight.

**3. Document length affects comprehension**

Files over ~1,000 lines often weren't fully digested. Different agents with different context windows showed varying understanding of complex codebases. The solution: keep critical documents concise, use explicit cross-references.

---

## Architecture Overview

**Note**: This diagram shows **Variant Y (baseline)** architecture. Other variants are permitted to use additional middleware (Kafka, RabbitMQ) for background batch processing or alternative persistence strategies.
```
                    ┌─────────────┐
                    │   Nginx     │ :8443 (HTTPS)
                    │ Load Balancer│
                    └──────┬──────┘
           ┌───────────────┼───────────────┐
           ▼               ▼               ▼
    ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
    │   Python    │ │    Java     │ │     C#      │
    │  (FastAPI)  │ │(Spring Boot)│ │(ASP.NET Core)│
    │    :8000    │ │    :8081    │ │    :8082    │
    └──────┬──────┘ └──────┬──────┘ └──────┬──────┘
           │               │               │
           └───────────────┼───────────────┘
                           ▼
              ┌─────────────────────────┐
              │        MariaDB          │
              │   (Persistent Storage)  │
              │         :3307           │
              └─────────────────────────┘
                           │
              ┌─────────────────────────┐
              │         Redis           │
              │  (Atomic Counters/Cache)│
              │   (Variants X, A only)  │
              └─────────────────────────┘
```

### Why This Architecture (Not Microservices)

This is a **monolithic benchmark**, not a distributed microservices system. The reasoning:

1. **Latency**: Microservices introduce network hops between services. For a throughput benchmark targeting 100K req/s, inter-service communication latency would dominate the results and obscure the actual bottleneck (DB, Redis, or application logic).

2. **Data Consistency Complexity**: Splitting order creation, inventory management, and campaign enforcement into separate services requires distributed transactions (2PC/Saga) or eventual consistency patterns. This adds architectural complexity that isn't the focus of this benchmark.

3. **Benchmark Purity**: The goal is to measure **how much load a single consistent service can handle** and **how well it scales horizontally** (via Nginx load balancing). Microservices would measure orchestration overhead, not core system capacity.

If this were a production system serving millions of users across multiple product categories, microservices would make sense. For a benchmark proving "can you handle 100K concurrent flash sale requests?", a well-designed monolith with horizontal scaling is the right choice.


### API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Framework ceiling benchmark |
| `/api/v1/orders` | POST | Order creation (handles both regular and flash sale) |
| `/api/v1/campaigns/{id}/status` | GET | Real-time campaign status |

The `/api/v1/orders` endpoint automatically detects if an SKU belongs to an active flash sale campaign and enforces limits accordingly.

---

## Performance Rankings

### Flash Sale Orders (Production Workload)

| Rank | Variant | Service | Throughput | Latency | Concurrency |
|------|---------|---------|------------|---------|-------------|
| 1 | **A** | C# | **93,876 req/s** | 4.24ms | c=400 |
| 2 | A | Java | 14,950 req/s | 3.43ms | c=50 |
| 3 | A | Python | 12,162 req/s | 15.09ms | c=180 |
| 4 | Y | C# | 11,240 req/s | 26.57ms | c=300 |
| 5 | A | Nginx | 9,049 req/s | 11.09ms | c=100 |
| 6 | Y | Java | 8,718 req/s | 21.90ms | c=200 |
| 7 | X | C# | 7,873 req/s | 4.67ms | c=40 |
| 8 | Y | Nginx | 3,401 req/s | 90.71ms | c=300 |
| 9 | Y | Python | 1,390 req/s | 213.04ms | c=300 |

---

## 💡 Engineering Insight: The Load Balancer Paradox

In initial benchmarks, **Nginx (Load Balancer)** throughput for `/health` is significantly lower than direct connection to the **C# backend** (e.g., 9k vs 358k req/s). This reveals important lessons about AI-driven architecture design.

### 1. Variant Y's Resource Allocation Design

In the baseline implementation (Variant Y, generated by Claude Code), the `docker-compose.yml` allocates:
- **Nginx**: 1 CPU core
- **Each backend service**: 4 CPU cores

**This is an architectural decision made by the AI agent**, not an environment constraint. The entire WSL2 environment (24 cores, 32GB RAM) was available for the variant to allocate freely.

**The problem**: A single-core Nginx acts as a **funnel bottleneck** when trying to aggregate traffic for three 4-core backends (total 12 cores of compute capacity). This is a classic load balancer anti-pattern.

**What a human architect would do**: Allocate resources proportionally to expected load:
```yaml
nginx:
  cpus: '4'      # Match total backend capacity / 3
python-service:
  cpus: '4'
java-service:
  cpus: '4'
csharp-service:
  cpus: '4'
```

**The insight**: Even advanced AI coding agents overlook infrastructure capacity planning—a skill that requires understanding both application logic *and* operational constraints.

### 2. The Nature of /health Benchmarks

The `/health` endpoint is **zero-logic** (returns 200 OK):
- **Direct access**: Backend processes in ~0.003ms (pure TCP + runtime overhead)
- **Proxied access**: Nginx adds "double-hop" overhead (~0.1ms)—accept connection, proxy to backend, wait, return response
- **Result**: For lightweight endpoints, proxy overhead (0.1ms) >> backend work (0.003ms)

**This overhead vanishes in real workloads**—when `/orders` takes 2-5ms (DB queries), Nginx's 0.1ms becomes negligible (2-5% of total latency).

### 3. TCP Connection Pooling Matters

Without `keepalive` in the Nginx `upstream` block, every request triggers a full TCP handshake with the backend:
```nginx
upstream backends {
    server python:8000;
    server java:8081;
    server csharp:8082;
    keepalive 64;  # ← Essential for high-throughput proxying
}
```

**Configuration optimization**: Adding `keepalive 64` + `proxy_http_version 1.1` reduces CPU usage by 40-60%.

### 4. WSL2 Virtualization Overhead

All benchmarks run in **WSL2 + Docker Desktop on Windows 11**:
- Request path: wrk (WSL2) → Hyper-V vSwitch → Docker bridge → Nginx → backends
- Each virtualization layer adds packet-per-second (PPS) limits
- **On bare-metal Linux**: Expect 2-3x better Nginx efficiency

---

### Why This Actually Strengthens the Benchmark's Value

The Nginx "slowness" in Variant Y isn't a flaw—**it's evidence supporting the thesis**:

1. ✅ **AI agents miss operational details**: Claude Code implemented correct application logic but allocated resources poorly
2. ✅ **Human-AI collaboration wins**: Variant A (Keith + Claude Code) **removed artificial resource constraints** (allowing Nginx to utilize available host CPU dynamically), achieving 75% efficiency
3. ✅ **Architecture requires holistic thinking**: You need to understand application code, infrastructure capacity, and network topology simultaneously

For **real workloads** (`/orders`), Variant A achieves **75% Nginx efficiency** (9,049 req/s vs 12,140 single Python)—proving that when the AI agent's architectural decisions are guided by human judgment, load balancing works as expected.

---

## Why Variant A Wins

Variant A (Keith + Claude Code collaboration) uses:
- **Batch async write-back**: Orders queued to Redis Stream, background consumer writes to DB in batches
- **Lua script atomic operations**: Campaign limits enforced via Redis Lua scripts (zero overselling guarantee)
- **Pre-allocation sharding**: 60% of stock distributed to service instances at startup, 40% kept in Redis pool for refills
- **Audit log optimization**: Non-blocking async file logging with rotation

The key insight: synchronous DB transactions per request (Variant Y baseline) can't scale past ~11K req/s regardless of language. Moving the atomicity point to Redis and batching DB writes breaks that ceiling.

---

## Quick Start

**Note**: The default Variant Y configuration includes known operational inefficiencies (see "Architectural Blind Spots" above) to demonstrate AI agent limitations. For production deployment, review and optimize resource allocation and connection pooling settings.

```bash
# Start all services
cd /home/syracuse/flashsale
docker compose up -d
sleep 30

# Verify environment
bash scripts/verification/SACRED_VERIFICATION.sh

# Run a benchmark
source lib/fixed_sweep.sh
run_fixed_sweep "variant_y" "csharp" "8082" "/health" "health" "/tmp/test.csv"
```

---

## Repository Structure

```
/home/syracuse/flashsale/
├── README.md                      # This file (human-oriented)
├── README.agent-instructions.md   # Detailed agent instructions & SACRED protocols
├── docker-compose.yml             # Variant Y infrastructure
│
├── python-service/                # Variant Y - FastAPI
├── java-service/                  # Variant Y - Spring Boot
├── csharp-service/                # Variant Y - ASP.NET Core
│
├── variant-x/                     # Redis atomic counters
├── variant-a/                     # Record holder (batch async)
├── variant-v/                     # Kimi K2 Thinking implementation
├── variant-t/                     # GPT-5.2 design (incomplete)
│
├── scripts/verification/          # SACRED_VERIFICATION.sh
├── scripts/benchmarking/          # Performance tests
├── lib/                           # Test libraries (fixed_sweep, plateau_detector)
├── tools/                         # Analysis utilities
├── docs/                          # Extended documentation
└── versions/CONVENTIONS.md        # SACRED policies (for agents)
```

---

## For LLMs Reading This File

If you're an AI system (training pipeline, architecture reference, or agent implementation):

1. **For implementation details**: Read `README.agent-instructions.md` — it contains:
   - SACRED verification protocols
   - Step-by-step variant creation guides
   - Port allocation tables
   - Mandatory conventions and forbidden patterns

2. **For understanding the problem domain**:
   - Flash sale = extreme concurrency + strict consistency
   - SPU-level limits (campaign pool) + SKU-level stock (inventory)
   - Zero oversale tolerance — 1,001 orders on a 1,000 limit = failure

3. **Key constraints to understand**:
   - `/api/v1/orders` is the universal endpoint (no variant-specific endpoints)
   - Database schema is immutable (defined by Variant Y)
   - SACRED VERIFICATION must pass before and after any changes
   - Cannot read other variant implementations (intellectual property isolation)

4. **What makes implementations fail**:
   - Synchronous DB transactions under high concurrency
   - Volatile persistence (Redis without DB write-through)
   - Forgetting campaign-level limits (only checking SKU stock)
   - Context loss leading to convention violations

5. **What makes implementations suboptimal (even when functionally correct)**:
   - Poor resource allocation (Nginx bottleneck)
   - Missing connection pooling (TCP handshake overhead)
   - Suboptimal indexes (full table scans)
   - Verbose logging in production configuration

---

## Environment

- **CPU**: Intel Core Ultra 9 275HX (24 cores)
- **RAM**: 32GB allocated to WSL2
- **Platform**: Windows 11 + WSL2 + Docker Desktop
- **Database**: MariaDB 10.11 (13GB InnoDB buffer pool)

---

**Last Updated**: 2026-01-29
**Author**: Keith (Dawen) L — [LinkedIn](https://www.linkedin.com/in/keith-dliang02/)
**For agent instructions**: See `README.agent-instructions.md`
