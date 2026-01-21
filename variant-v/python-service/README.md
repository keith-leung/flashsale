# Variant V - Python Service

## Overview
Campaign-Aware Distributed Locking + Write-Ahead Audit flash sale service.

## Structure
```
variant-v/python-service/
├── app/
│   ├── main.py              # FastAPI entry with /health endpoint
│   ├── __init__.py
│   ├── api/                 # API routes (will add orders later)
│   ├── core/                # Core configuration
│   ├── models/              # Database models
│   ├── services/            # Distributed locking, audit services
│   └── workers/             # Batch processing workers
├── tests/                   # Test suite
├── migrations/              # Database migrations
├── logs/                    # Log files
├── requirements.txt         # Python dependencies
├── pyproject.toml          # Poetry configuration
├── Dockerfile              # Container image
├── START_SERVER.sh         # Local development startup
├── benchmark_health.sh     # Basic health benchmark
├── benchmark_adaptive.sh   # Adaptive throughput test
└── run_adaptive_benchmark.sh # Complete setup + benchmark flow

```

## Quick Start

### Option 1: Docker (Recommended)
```bash
cd variant-v/python-service
./run_adaptive_benchmark.sh
```

### Option 2: Local Environment
```bash
cd variant-v/python-service
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m app.main
```

Then in another terminal:
```bash
./benchmark_adaptive.sh
```

## Health Endpoint
- **URL**: `GET /health`
- **Response**: `200 OK` (plain text)
- **Purpose**: Load balancer health check

## Benchmarking

### Basic Health Check
```bash
./benchmark_health.sh [URL] [THREADS] [CONNECTIONS] [DURATION]
```

### Adaptive Benchmark (Recommended)
```bash
./benchmark_adaptive.sh
```

The adaptive benchmark:
1. Runs baseline test (12 threads, 400 connections)
2. Automatically adjusts based on throughput
3. Targets >10,000 req/s minimum
4. Provides appropriate stress tests based on performance

## Current Status

✅ **Implemented**
- Basic FastAPI application structure
- `/health` endpoint returning 200 OK
- Adaptive benchmark script
- Docker containerization
- Development scripts

🔄 **Next Steps**
- Audit-first order API
- Distributed locking service
- Redis connection management
- MariaDB audit log table
- Batch processing worker
- Order creation endpoint with write-ahead audit
- Campaign-SKU allocation matrix
- Verification script integration

## Performance Targets

- **Variant Y Baseline**: 1,390 req/s (Python)
- **Variant V Target**: 8,000+ req/s (5.8x improvement)

## Architecture Notes

This implementation follows the Variant V design:
- Campaign-aware distributed locking
- Write-ahead audit pattern
- SKU-range partitioning across Redis nodes
- Async batch processing
- Zero oversale guarantee

For detailed design documentation, see `variant-v/README.md`.
