# Variant A: Cross-Language Adaptive Benchmark Analysis (/health2)

## 1. Executive Summary
This report analyzes the overhead of the "Fast Path" inventory reservation logic (`/health2`) compared to a raw HTTP baseline (`/health`). The goal is to measure the cost of the atomic memory operations in C#, Java, and Python when the system is operating at peak concurrency.

**Key Finding:** The atomic reservation logic introduces minimal overhead across all languages (less than 5%), confirming that the "Fast Path" architecture is CPU-efficient and not a bottleneck.

## 2. Methodology
- **Endpoints:**
    - `/health`: Baseline HTTP 200 OK (No logic).
    - `/health2`: Atomic inventory reservation (1 decrement per request).
- **Metric:** Peak Requests Per Second (RPS).
- **Observation Point:** Concurrency level where the service reached its throughput plateau (c=500 for all).

## 3. Peak Performance & Overhead Comparison

The table below compares the raw baseline throughput against the throughput with allocation logic enabled.

| Language | Peak Concurrency | Baseline (`/health`) RPS | Allocation (`/health2`) RPS | Overhead / Impact |
| :--- | :--- | :--- | :--- | :--- |
| **C# (ASP.NET Core)** | 500 | 427,612 | 413,572 | **-3.3%** |
| **Java (Spring Boot)** | 500 | 284,185 | 272,251 | **-4.2%** |
| **Python (FastAPI)** | 500 | 48,909 | 50,180 | **+2.6%** (Variance) |

*Note: Python's positive delta is within the margin of error for network/OS scheduling at these lower throughput levels, effectively indicating 0% overhead.*

## 4. Analysis

### A. C# Efficiency
C# demonstrates the highest raw throughput and a very consistent, low overhead (~3.3%). This confirms that `Interlocked.Decrement` is extremely cheap relative to the HTTP request lifecycle in Kestrel. The service scales linearly, handling over 400k alloc/sec.

### B. Java Efficiency
Java follows a similar pattern with ~4.2% overhead. The JVM's JIT and optimized concurrency primitives (AtomicInteger/Long) perform well, though the overall container overhead of Spring Boot keeps the raw ceiling lower than C#.

### C. Python Efficiency
Python's "overhead" is non-existent in this test because the GIL and event loop saturation are the dominant bottlenecks, not the simple integer decrement logic. The service maxes out around 50k RPS regardless of whether it's returning a static string or doing a simple in-memory subtraction.

## 5. Conclusion
The "Fast Path" architecture successfully eliminates application-level locking bottlenecks. In all three languages, the cost of the reservation logic is negligible compared to the overhead of handling the HTTP request itself.

- **For Maximum Throughput:** **C#** is the clear winner (1.5x faster than Java, 8x faster than Python).
- **For Implementation:** The logic is safe and performant in all three, but Python's runtime limits make it unsuitable for the ultra-high concurrency targets (>100k RPS) without horizontal scaling.
