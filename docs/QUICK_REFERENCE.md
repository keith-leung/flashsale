# Variant Y - Quick Reference Card

**Last Updated:** 2026-01-02

---

## 🚀 Quick Start

```bash
cd /home/syracuse/flashsale

# Start all services
docker compose up -d

# Run full verification (adaptive testing, default 10s/test)
bash SACRED_VERIFICATION.sh

# Run with longer duration (e.g., 30s/test for validation)
bash SACRED_VERIFICATION.sh 30
```

---

## 📊 Testing Methodology

### Adaptive Plateau Detection (NO Quick Mode)

**Starting Point:** t=4, c=10, duration=10s (default)

**Decision Logic:**
- **>5% growth** → SIGNIFICANT_GROWTH → Aggressive increase (t × 1.5, c × 2)
- **2-5% growth** → MODERATE_GROWTH → Moderate increase (t × 1.2, c × 1.5)
- **0-2% growth** → MARGINAL_GROWTH → Small increase (t × 1.1, c × 1.2)
- **<2% variance (3 tests)** → PLATEAU_CONFIRMED → STOP ✓
- **Any 503 error** → SYSTEM_LIMIT → STOP 🛑
- **t=24, c=2000** → MAX_CAPS_REACHED → STOP 🔝

---

## 📁 Output Files

```
./benchmark_results/
├── variant_Y_raw_YYYYMMDD_HHMMSS.csv    # Raw test data (28 fields)
└── summary_YYYYMMDD_HHMMSS.md           # Pivot summary (markdown)
```

---

## 🔍 View Results

```bash
# View CSV (formatted)
cat ./benchmark_results/variant_Y_raw_TIMESTAMP.csv | column -t -s,

# View summary
cat ./benchmark_results/summary_TIMESTAMP.md

# Find plateaus
grep "PLATEAU_CONFIRMED" ./benchmark_results/variant_Y_raw_TIMESTAMP.csv

# Count tests per service
grep "python" ./benchmark_results/variant_Y_raw_TIMESTAMP.csv | wc -l
```

---

## 🛠️ Service Management

```bash
# Start services
docker compose up -d

# Check status
docker ps | grep flash

# View logs
docker logs flash-python-y
docker logs flash-java-y
docker logs flash-csharp-y
docker logs flash-nginx-y

# Restart service
docker restart flash-python-y

# Stop all
docker compose down
```

---

## 🗄️ Database Access

**DataGrip Connection:**
- **Host:** localhost
- **Port:** 3307
- **Database:** orange315
- **User:** syracuse
- **Password:** Orange_315_Forever!

**CLI Access:**
```bash
docker exec flash-mariadb-y mysql -usyracuse -pOrange_315_Forever! orange315
```

---

## 🧪 Unit Tests

```bash
# Run all tests
docker exec flash-python-y python -m pytest

# Verbose output
docker exec flash-python-y python -m pytest -v

# Specific test file
docker exec flash-python-y python -m pytest tests/test_order_service.py
```

---

## 📏 Service Endpoints

| Service | Port | Health | Orders |
|---------|------|--------|--------|
| Python  | 8000 | http://localhost:8000/health | http://localhost:8000/api/v1/orders |
| Java    | 8081 | http://localhost:8081/health | http://localhost:8081/api/v1/orders |
| C#      | 8082 | http://localhost:8082/health | http://localhost:8082/api/v1/orders |
| Nginx   | 8443 | https://localhost:8443/health | https://localhost:8443/api/v1/orders |

---

## 🏗️ Architecture Components

```
/home/syracuse/flashsale/
├── SACRED_VERIFICATION.sh       # Main entry point (always full mode)
├── lib/
│   ├── plateau_detector.sh     # Adaptive algorithm
│   └── wrk_parser.sh            # WRK output parser
├── generate_pivot_summary.py    # CSV → Markdown summary
├── docker-compose.yml           # Service definitions
├── nginx/nginx.conf             # Load balancer config
└── benchmark_results/           # Test outputs
```

---

## 📋 CSV Schema (28 Fields)

```
timestamp, variant, service, endpoint, test_type, threads, concurrency,
duration_s, req_per_sec, avg_latency_ms, p50_latency_ms, p90_latency_ms,
p99_latency_ms, max_latency_ms, stdev_latency_ms, total_requests,
total_errors, error_rate_pct, non_2xx_3xx, socket_errors_connect,
socket_errors_read, socket_errors_write, socket_errors_timeout,
transfer_mb, throughput_mb_s, test_sequence, throughput_increase_pct,
decision
```

---

## 🎯 Decision Types

| Symbol | Decision | Meaning |
|--------|----------|---------|
| ✓ | `PLATEAU_CONFIRMED` | True plateau detected (<2% variance) |
| 🔝 | `MAX_CAPS_REACHED` | Hit maximum caps (t=24, c=2000) |
| 🛑 | `SYSTEM_LIMIT` | System capacity reached (503 errors) |
| ⚠ | `TEST_FAILED` | Test execution failed |
| 📈 | `SIGNIFICANT_GROWTH` | Throughput increased >5% |
| 📊 | `MODERATE_GROWTH` | Throughput increased 2-5% |
| 📉 | `MARGINAL_GROWTH` | Throughput increased 0-2% |

---

## ⚡ Performance Comparison

| Metric | Old Fixed Sweep | New Adaptive |
|--------|----------------|--------------|
| Approach | Fixed 12 levels | Dynamic adjustment |
| Duration/test | 30s | 10s (default) |
| Total time | ~6 min/endpoint | ~70 sec/endpoint |
| Speed | Baseline | **4-5x faster** ✓ |
| Accuracy | May miss optimal | **Statistical confidence** ✓ |
| Error handling | None | **Zero tolerance for 503s** ✓ |

---

## 🔧 Troubleshooting

### Services won't start
```bash
# Check for port conflicts
sudo lsof -i :3307
sudo lsof -i :8000
sudo lsof -i :8081
sudo lsof -i :8082
sudo lsof -i :8443

# Check Docker status
docker ps -a | grep flash

# View startup logs
docker logs flash-python-y --tail 100
```

### Tests fail immediately
```bash
# Verify services are healthy
curl http://localhost:8000/health
curl http://localhost:8081/health
curl http://localhost:8082/health

# Check test data exists
ls -lh /tmp/stress_test_sku_ids.txt

# Regenerate test data
docker exec flash-python-y python /app/setup_test_data.py 500 5 10000
```

### Low throughput
```bash
# Check service logs for errors
docker logs flash-python-y --tail 50

# Check database connections
docker exec flash-mariadb-y mysql -usyracuse -pOrange_315_Forever! \
    -e "SHOW PROCESSLIST" orange315

# Check resource usage
docker stats --no-stream
```

---

## 📚 Documentation

| File | Purpose |
|------|---------|
| `ADAPTIVE_TESTING.md` | Comprehensive technical documentation |
| `IMPLEMENTATION_SUMMARY.md` | What was built and why |
| `VARIANT_Y_REDIS_REMOVAL.md` | Architecture changes and migration history |
| `QUICK_REFERENCE.md` | This file - quick command reference |
| `README.md` | Project overview |

---

## 🎓 Key Concepts

### Plateau vs Peak

- **Plateau:** Sustainable throughput that remains stable as concurrency increases
  - Detected via <2% variance across 3 consecutive tests
  - Indicates optimal configuration for sustained load
  - Best for production sizing

- **Peak:** Maximum throughput before system limit
  - Detected via 503 errors (SYSTEM_LIMIT)
  - Indicates absolute capacity
  - Useful for understanding headroom

### Coefficient of Variation (CV)

```
CV = (standard_deviation / mean) × 100
```

- Used for plateau detection
- Measures relative variability
- <2% CV indicates stable performance
- More reliable than absolute thresholds

### Adaptive Adjustment

- **Aggressive (>5%):** System has significant headroom, increase quickly
- **Moderate (2-5%):** Approaching limits, increase carefully
- **Marginal (0-2%):** Near plateau, increase slightly to confirm
- **Plateau (<2% variance):** Confirmed stable performance, stop testing

---

## 🚨 Important Notes

1. **Always run SACRED_VERIFICATION.sh in full mode** - no quick mode exists
2. **Default 10s duration** is sufficient for finding plateaus (faster)
3. **Use 30s+ duration** only for final validation or publication-quality data
4. **CSV files are cross-variant compatible** - same schema for Y, X, Z
5. **Pivot summaries are generated from CSV** - not inline during testing
6. **Zero 503 error tolerance** - any error stops testing immediately
7. **Services must be warmed up** before testing starts (handled automatically)

---

## 🔗 Quick Links

**Service URLs:**
- Python: http://localhost:8000
- Java: http://localhost:8081
- C#: http://localhost:8082
- Nginx: https://localhost:8443 (HTTPS, self-signed cert)

**Common Commands:**
```bash
# Full verification
bash SACRED_VERIFICATION.sh

# Check services
docker ps | grep flash

# View latest results
ls -lht ./benchmark_results/ | head -5

# Database query
docker exec flash-mariadb-y mysql -usyracuse -pOrange_315_Forever! orange315 \
    -e "SELECT COUNT(*) FROM orders"
```

---

**Version:** 1.0
**Status:** ✅ Production Ready
**Support:** See ADAPTIVE_TESTING.md for detailed documentation
