# Quick Start Guide - Variant Y

**This guide is designed for COMPLETE REPRODUCIBILITY.** Any agent (human or LLM) can follow these steps to verify the system works.

## Prerequisites

- Podman 3.4.4+ or Docker 20.10+
- wrk (HTTP benchmarking tool)
- curl, netstat

## Instant Verification (Zero Context Required)

```bash
# Step 1: Check if Variant Y is ready
bash check_variant_y.sh
```

**Expected Output:**
```
✓ Variant Y is READY
```

If services are not running, they will be started automatically. If you see "Variant Y has issues", run:

```bash
podman-compose up -d
sleep 30
bash check_variant_y.sh
```

## Run Full 4-Step Benchmark

```bash
# Quick mode (10s per test - for fast verification)
bash run_4step_benchmark.sh quick

# Full mode (30s per test - for accurate metrics)
bash run_4step_benchmark.sh full
```

The script is **completely idempotent**:
- Checks if services are running, starts them if not
- Waits for services to be healthy
- Generates test data if missing
- Runs all 4 benchmark steps
- Never fails due to environment issues

## Run Unit Tests

```bash
podman exec flash-python python -m pytest
```

**Expected Output:**
```
===== 29 passed in X.Xs =====
```

## Connect DataGrip (Always-On Database)

MariaDB is **always running** with restart=always policy:

```
Host: localhost
Port: 3307
Database: orange315
User: syracuse
Password: Orange_315_Forever!
```

Test connection:
```bash
mysql -h localhost -P 3307 -usyracuse -pOrange_315_Forever! orange315 -e "SHOW TABLES;"
```

## Architecture Overview

**Variant Y (Baseline) - THIS WSL INSTANCE:**
- Network: 10.88.0.0/24 (static IPs)
- MariaDB: 10.88.0.2 → localhost:3307
- Redis: 10.88.0.3 (internal)
- Python: 10.88.0.5 → localhost:8000
- Java: 10.88.0.6 → localhost:8081
- C#: 10.88.0.7 → localhost:8082
- Nginx: 10.88.0.4 → localhost:8443

All services have `restart: always` - they survive:
- WSL restarts
- System reboots
- Container crashes

## File Organization

```
/home/syracuse/orange-315-forever/
├── docker-compose.yml           # Variant Y only (conflicts removed)
├── check_variant_y.sh           # Quick health check
├── run_4step_benchmark.sh       # Full benchmark suite
├── README.md                    # Main documentation
├── versions/CONVENTIONS.md      # All policies and conventions
├── archived-variant-x/          # Old conflicting files (archived)
├── python-service/              # FastAPI implementation
├── java-service/                # Spring Boot implementation
├── csharp-service/              # ASP.NET Core implementation
└── nginx/                       # Load balancer config
```

## Making Code Changes

**CRITICAL: Follow this sequence to preserve functionality:**

1. **Before making changes:**
   ```bash
   podman exec flash-python python -m pytest
   # Must show: 29 passed
   ```

2. **Make your modifications**

3. **After making changes:**
   ```bash
   # Run unit tests
   podman exec flash-python python -m pytest
   # Must still show: 29 passed

   # Run full benchmark
   bash run_4step_benchmark.sh full
   # Compare results with README.md baseline
   ```

4. **If tests fail:**
   - Revert your changes immediately
   - Fix the issue
   - Re-test before committing

## Expected Performance Baseline

**Health Endpoints (Direct Access):**
- Python: ~41,000 req/s (-c100)
- Java: ~184,000 req/s (-c200)
- C#: ~470,000 req/s (-c600)

**Order Processing (Direct Access):**
- Python: ~694 req/s (-c50)
- Java: ~2,630 req/s (-c75)
- C#: ~2,227 req/s (-c25)

**Nginx (Round-Robin):**
- Health: ~10,106 req/s (-c25)
- Orders: ~1,113 req/s (-t4 -c50)

Variance: ±10% is acceptable

## Troubleshooting

### Services not starting
```bash
podman-compose down
podman-compose up -d
sleep 30
bash check_variant_y.sh
```

### Port conflicts
```bash
# Check what's using the ports
netstat -tuln | grep -E ":(3307|8000|8081|8082|8443)"

# Stop conflicting services
podman stop $(podman ps -aq)
podman-compose up -d
```

### Database connection issues
```bash
# Check MariaDB is running
podman exec flash-mariadb mysqladmin ping -usyracuse -pOrange_315_Forever!

# Restart MariaDB
podman restart flash-mariadb
sleep 10
```

## Sacred Policies (NEVER VIOLATE)

1. **Variant Y is SACRED** - Never break its functionality
2. **Syracuse Credentials are IMMUTABLE** - Never change them
3. **Middleware Always Running** - All services have `restart: always`
4. **Test Before Commit** - Unit tests + 4-step benchmark required
5. **No Shared Infrastructure** - Each variant gets dedicated middleware

Read `/versions/CONVENTIONS.md` for complete policy details.
