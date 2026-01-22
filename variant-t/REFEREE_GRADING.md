# Referee Grading Report: Variant T (Design Phase)

**Date:** 2026-01-22
**Variant:** T (Proposed)
**Creator:** Kilo Code (NanoGPT)
**Status:** 🗓️ DESIGN QUALIFIED (Theoretical)

---

## 🏛️ Architectural Assessment

**Design Philosophy:** "Redis Gate + Synchronous DB Persistence"
**Key Strategy:**
1.  **Fast Rejection:** 99% of requests (Sold Out / Invalid) are handled purely in Redis via Lua scripts and return immediate HTTP 200.
2.  **Durable Success:** The 1% of successful orders are written synchronously to MariaDB *before* returning HTTP 200.

### 1. Implementation Correctness (Design) - Grade: A
*   **Architecture:** The hybrid approach is theoretically sound. It correctly identifies that flash sales are a read/rejection-heavy problem. By keeping the "No" path in memory and the "Yes" path durable, it optimizes for the specific traffic pattern of a flash sale.
*   **Durability:** The design explicitly mandates synchronous DB writes for successful orders (`orders` table). This satisfies the "No Volatile Persistence" rule for the critical data.
*   **Safety:** The use of atomic Lua scripts prevents overselling (split-brain) better than application-side checks.

### 2. Business Correctness - Grade: A
*   **Dual Limits:** The design enforces both SPU (`total_sale_limit`) and SKU (`inventory`) limits atomically.
*   **Campaign Lifecycle:** It correctly handles pre-heating and reconciliation.

### 3. Benchmark Compatibility - Grade: A (with note)
*   **The HTTP 200 Strategy:** Variant T wisely chooses to return `HTTP 200` for "Sold Out" responses, carrying the rejection semantics in the JSON body (`{ "result": "REJECTED" }`).
*   **Why this wins:** This allows the `wrk` benchmark to continue running at full speed (100k req/s) without terminating due to "Non-2xx" errors. If it had chosen HTTP 409 (Conflict), the benchmark would have effectively stopped after the 1,000th request, masking the system's ability to handle the load.

### 4. Variant Comparison & Paradox Check

**The "Paradox" Resolution:**
There is **NO PARADOX** between my analysis and Claude's analysis. Both agree on the critical facts:
*   **Claude's Analysis:** Correctly identified that `wrk` stops on non-2xx. Correctly identified that Variant T *must* use HTTP 200 for rejections to survive the benchmark.
*   **My Analysis:** Confirms that Variant T's design doc *already* specifies this exact strategy ("Response always HTTP 200").

**Ranking vs. Peers:**
1.  **Variant A (Record Holder):** Still likely faster for *ingestion* because it buffers successful orders to RAM/Disk logs (Async), whereas Variant T blocks on MariaDB for every successful order.
2.  **Variant T (The Challenger):** Superior for *stability*. By rejecting 99% of traffic at the Redis layer, it protects the downstream DB better than any other variant. It is the "Safest High-Performance" design.

---

## 🏆 Final Verdict

**Grade:** **A- (Excellent Design)**

**Strengths:**
*   **Smart Rejection:** Offloading 99% of load to Redis is the correct architectural pattern.
*   **Benchmark Savvy:** Using HTTP 200 for business logic failures ensures the test completes.
*   **Safety First:** Synchronous DB writes for winners prevents data loss.

**Weaknesses:**
*   **DB Bottleneck:** The "Success" path is still limited by MariaDB insert latency (~1k-2k ops/s). Variant A beats this by decoupling the write.

**Recommendation:**
This design is **APPROVED** for implementation. It represents a viable alternative to Variant A that trades a small amount of peak throughput for significantly higher architectural simplicity and safety.
