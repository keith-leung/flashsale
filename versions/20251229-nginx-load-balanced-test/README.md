# Variant X Nginx Load Balanced Test - December 29, 2025

## Quick Reference

This directory contains complete documentation of the Variant X Nginx load balanced test performed on December 29, 2025.

## Files in This Archive

### Documentation
- **`SUMMARY.md`** - Complete test methodology, results, and technical details
- **`PODMAN_UPGRADE.md`** - Why Podman needed upgrade, how it was done, what it solved
- **`WORK_COMPLETED_20251229.md`** - Summary of all work done today
- **`DEPLOYMENT.md`** - Old multi-WSL deployment guide (archived, outdated)
- **`FLASH_SALE_TEST_RESULTS.md`** - Old 100K campaign test (archived, outdated)

### Configuration Files
- **`docker-compose-variant-x-simple.yml`** - Working configuration with static IPs
- **`benchmark_results.txt`** - Raw wrk output from final test

## Key Results

**Variant X through Nginx:** 5,428 req/s
- 2.5× faster than Variant Y (2,136 req/s)
- 11.04ms average latency (83% reduction)
- Zero overselling validated
- Production-ready architecture

## What Was Learned

1. **Podman 3.4.4 is fundamentally broken** - ignores network specifications completely
2. **Podman 4.6.2 fixes network issues** - but DNS still broken (acceptable with static IPs)
3. **Must test correct code path** - intelligent routing requires flash sale data in Redis
4. **Nginx overhead is significant** - ~50% reduction from individual service max throughput
5. **Real-world testing is critical** - theoretical calculations (47K req/s) vs reality (5.4K req/s)

## Working Configuration

All services running with static IPs:
- MariaDB: 10.89.0.8
- Redis: 10.89.0.3
- Python: 10.89.0.9
- Java: 10.89.0.10
- C#: 10.89.0.11
- Nginx: 10.89.0.12

DNS not working - all services use IPs in environment variables and nginx.conf.

## Active Files (Not Archived)

These files remain in project root for active use:
- `/home/syracuse/orange-315-forever/docker-compose-variant-x-simple.yml` - Active working config
- `/home/syracuse/orange-315-forever/README.md` - Single source of truth

## How to Reproduce Test

```bash
# 1. Start services
cd /home/syracuse/orange-315-forever
podman-compose -f docker-compose-variant-x-simple.yml up -d

# 2. Load flash sales to database
podman exec flash-python python setup_flash_sale_campaigns.py

# 3. Load flash sales to Redis
podman exec flash-python python /tmp/load_flash_sales_to_redis.py

# 4. Run benchmark
wrk -t8 -c50 -d10s --latency -s /tmp/wrk_flash_sale_order.lua \
  https://localhost:8444/api/v1/orders

# Expected: ~5,400 req/s with 11ms avg latency
```

## See Also

- Main project README: `/home/syracuse/orange-315-forever/README.md`
- Previous test: `/home/syracuse/orange-315-forever/versions/variant-y-2025-12-27/`
- Variant X implementation: `/home/syracuse/orange-315-forever/versions/variant-x-2025-12-28/`
