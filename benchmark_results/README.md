# Benchmark Results

This directory contains organized benchmark test results for all variants and campaigns.

## Directory Structure

```
benchmark_results/
├── README.md              # This file
└── campaigns/             # Results organized by test campaign
    ├── 20260102_fixed_sweep/
    │   ├── README.md      # Campaign summary and findings
    │   ├── raw/           # Raw CSV data files
    │   ├── reports/       # Generated analysis reports
    │   └── visualizations/ # Charts and graphs
    │
    └── [YYYYMMDD]_[campaign_name]/
        ├── README.md
        ├── raw/
        ├── reports/
        └── visualizations/
```

## Campaign Organization

Each benchmark campaign follows this structure:

### Campaign Directory Template
```
20260102_my_campaign/
├── README.md                           # Campaign summary
│   ├── Objective                       # Why this test was run
│   ├── Test Configuration              # Strategy, endpoints, concurrency
│   ├── Results Summary                 # Peak performance tables
│   ├── Key Findings                    # Analysis and insights
│   ├── Comparison to Goals             # Gap analysis
│   └── Reproduction Instructions       # How to recreate
│
├── raw/                                # Raw benchmark data
│   ├── full_data.csv                   # Complete results
│   ├── health_summary.csv              # Health endpoint summary
│   ├── order_summary.csv               # Order endpoint summary
│   ├── peak_performance.csv            # Peak performance by service
│   └── [service]_[endpoint].csv        # Individual test results
│
├── reports/                            # Generated reports
│   ├── summary.md                      # Detailed analysis
│   ├── performance_summary.md          # Formatted tables
│   └── comparison_[variants].md        # Cross-variant comparison
│
└── visualizations/                     # Charts and graphs
    ├── throughput_vs_concurrency.png
    ├── latency_distribution.png
    └── service_comparison.png
```

## Available Campaigns

### 20260102_fixed_sweep
**Variant:** Y (No Redis, MariaDB-only)
**Strategy:** Fixed concurrency sweep
**Services:** Python, Java, C#, Nginx

**Key Results:**
- C# peak: 1,802 orders/s (c=10), 338,356 health/s (c=400)
- Java peak: 427 orders/s (c=50), 130,623 health/s (c=100)
- Python issues: 866 timeouts at high concurrency
- Nginx: 753 orders/s (c=25), 9,164 health/s (c=25)

**Files:** See `campaigns/20260102_fixed_sweep/README.md`

## CSV File Schemas

### full_data.csv (Complete Results)
```csv
timestamp,variant,service,endpoint,test_type,threads,concurrency,duration_s,
req_per_sec,avg_latency_ms,p50_latency_ms,p90_latency_ms,p99_latency_ms,
max_latency_ms,stdev_latency_ms,total_requests,total_errors,error_rate_pct,
non_2xx_3xx,socket_errors_connect,socket_errors_read,socket_errors_write,
socket_errors_timeout,transfer_mb,throughput_mb_s,test_sequence,
throughput_increase_pct,decision
```

### health_summary.csv / order_summary.csv
```csv
service,concurrency,throughput_req_s,avg_latency_ms,p50_latency_ms,
p90_latency_ms,p99_latency_ms,timeouts
```

### peak_performance.csv
```csv
service,endpoint,peak_throughput_req_s,optimal_concurrency,total_timeouts
```

## How to Interpret Results

### Key Metrics

**Throughput (req/s):**
- Higher is better
- Indicates maximum request processing capacity
- Example: 1,802 orders/s means the service can handle 1,802 order requests per second

**Latency (ms):**
- Lower is better
- p50: Median latency (50% of requests faster than this)
- p90: 90th percentile (90% of requests faster than this)
- p99: 99th percentile (99% of requests faster than this)
- Example: p99=3.1ms means 99% of requests complete within 3.1 milliseconds

**Timeouts:**
- Zero is ideal
- Indicates requests that exceeded timeout threshold
- High timeouts = system overload or bottlenecks
- Example: 866 timeouts = critical performance issue

**Error Rate (%):**
- Should be 0% for production systems
- Non-zero indicates failures, bugs, or capacity issues

### Performance Benchmarks

**Health Endpoints (Lightweight):**
- Good: >10,000 req/s
- Excellent: >100,000 req/s
- World-class: >300,000 req/s

**Order Endpoints (Database-heavy):**
- Good: >500 req/s
- Excellent: >1,000 req/s
- Flash sale goal: 100,000 req/s (not yet achieved)

### Optimal Concurrency

- **Too low:** Underutilized resources, lower throughput
- **Optimal:** Maximum throughput, acceptable latency, zero timeouts
- **Too high:** System overload, increased latency, timeouts

Example:
- C# orders: Optimal at c=10 (1,802 req/s, 0 timeouts)
- C# health: Optimal at c=400 (338,356 req/s, 0 timeouts)

## Running New Campaigns

### 1. Create Campaign Directory
```bash
CAMPAIGN="benchmark_results/campaigns/$(date +%Y%m%d)_my_campaign"
mkdir -p "$CAMPAIGN"/{raw,reports,visualizations}
```

### 2. Run Benchmarks
```bash
# Fixed sweep strategy
source lib/fixed_sweep.sh
run_fixed_sweep "variant_y" "csharp" "8082" "/api/v1/orders" "order" \
  "$CAMPAIGN/raw/csharp_orders.csv"

# Adaptive plateau strategy
source lib/plateau_detector.sh
run_adaptive_test "variant_y" "csharp" "8082" "/health" "health" 10 \
  "$CAMPAIGN/raw/csharp_health_adaptive.csv"
```

### 3. Generate Reports
```bash
bash tools/generate_summary_reports.sh \
  "$CAMPAIGN/raw/*.csv" \
  "$CAMPAIGN/reports/"
```

### 4. Create Campaign README
```bash
cat > "$CAMPAIGN/README.md" << 'EOF'
# Campaign: [Name]
Date: $(date +%Y-%m-%d)
Variant: Y

## Objective
[Why this test was run]

## Test Configuration
- Strategy: Fixed sweep / Adaptive plateau
- Endpoints: /health, /api/v1/orders
- Services: Python, Java, C#, Nginx

## Results Summary
[Tables from reports/performance_summary.md]

## Key Findings
[Analysis and insights]

## Comparison to Previous
[How does this compare?]
EOF
```

## Comparing Campaigns

### Compare Peak Performance
```bash
# Extract peak from each campaign
for campaign in benchmark_results/campaigns/*/; do
  echo "=== $(basename $campaign) ==="
  awk -F',' 'NR>1 {print $1,$3,$4}' "$campaign/raw/peak_performance.csv"
done
```

### Compare Specific Concurrency Level
```bash
# Compare c=50 across campaigns
grep ",50," benchmark_results/campaigns/*/raw/health_summary.csv
```

### Compare Variants
```bash
# Create comparison report
bash tools/generate_summary_reports.sh \
  benchmark_results/campaigns/variant_x_*/raw/full_data.csv \
  > /tmp/variant_x.txt

bash tools/generate_summary_reports.sh \
  benchmark_results/campaigns/variant_y_*/raw/full_data.csv \
  > /tmp/variant_y.txt

diff /tmp/variant_x.txt /tmp/variant_y.txt
```

## Analyzing Results

### Find Best Performing Service
```bash
# Health endpoints
awk -F',' 'NR>1 {print $3, $1}' \
  benchmark_results/campaigns/20260102_fixed_sweep/raw/peak_performance.csv | \
  grep health | sort -rn | head -1
```

### Identify Timeout Issues
```bash
# Services with timeouts
awk -F',' 'NR>1 && $5>0 {print $1, $5 " timeouts"}' \
  benchmark_results/campaigns/20260102_fixed_sweep/raw/peak_performance.csv
```

### Calculate Performance Gap to Goal
```bash
# Goal: 100,000 orders/s
GOAL=100000
CURRENT=$(awk -F',' '$1=="CSHARP" && $2=="order" {print $3}' \
  benchmark_results/campaigns/20260102_fixed_sweep/raw/peak_performance.csv)
GAP=$(echo "scale=1; $GOAL / $CURRENT" | bc)
echo "Current: $CURRENT orders/s"
echo "Goal: $GOAL orders/s"
echo "Need ${GAP}x improvement"
```

## Best Practices

1. **Always create campaign README:** Document why you ran the test
2. **Include reproduction steps:** Future agents should be able to recreate
3. **Compare to previous:** Show improvement or regression
4. **Analyze failures:** Investigate timeouts and errors
5. **Archive old campaigns:** Move campaigns >30 days to `archive/`

## Troubleshooting

### Missing CSV files
```bash
# Check if benchmarks actually ran
ls -la benchmark_results/campaigns/my_campaign/raw/
```

### Empty or corrupted CSV
```bash
# Verify CSV format
head -5 benchmark_results/campaigns/my_campaign/raw/full_data.csv

# Check line count
wc -l benchmark_results/campaigns/my_campaign/raw/full_data.csv
```

### Can't find peak performance
```bash
# Regenerate reports
bash tools/generate_summary_reports.sh \
  benchmark_results/campaigns/my_campaign/raw/full_data.csv \
  benchmark_results/campaigns/my_campaign/reports/
```

## See Also

- **Main README:** `/README.md` - System overview and getting started
- **Scripts:** `/scripts/README.md` - How to run benchmarks
- **Tools:** `/tools/README.md` - Report generation utilities
- **Test Libraries:** `/lib/` - Fixed sweep and adaptive plateau functions

---

**Last Updated:** 2026-01-02
**Maintained By:** Syracuse
