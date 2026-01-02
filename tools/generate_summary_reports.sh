#!/bin/bash
#############################################################################
# Generate Summary Reports and CSV files for Visualization
#############################################################################

set -euo pipefail

CSV_FILE="/tmp/test_sacred.csv"
OUTPUT_DIR="/tmp/benchmark_charts"
mkdir -p "$OUTPUT_DIR"

echo "Generating benchmark summary reports..."
echo ""

# ============================================================================
# 1. HEALTH ENDPOINTS SUMMARY
# ============================================================================

echo "Creating health endpoints summary..."

cat > "${OUTPUT_DIR}/health_summary.csv" << 'HEADER'
service,concurrency,throughput_req_s,p50_latency_ms,p99_latency_ms,timeouts
HEADER

awk -F',' '
NR>1 && $5=="health" && ($3=="python" || $3=="java" || $3=="csharp") {
    printf "%s,%s,%.2f,%.2f,%.2f,%s\n", $3, $7, $9, $11, $13, $23
}' "$CSV_FILE" >> "${OUTPUT_DIR}/health_summary.csv"

echo "✓ Created: ${OUTPUT_DIR}/health_summary.csv"

# ============================================================================
# 2. ORDER ENDPOINTS SUMMARY
# ============================================================================

echo "Creating order endpoints summary..."

cat > "${OUTPUT_DIR}/order_summary.csv" << 'HEADER'
service,concurrency,throughput_req_s,p50_latency_ms,p99_latency_ms,timeouts
HEADER

awk -F',' '
NR>1 && $5=="order" {
    printf "%s,%s,%.2f,%.2f,%.2f,%s\n", $3, $7, $9, $11, $13, $23
}' "$CSV_FILE" >> "${OUTPUT_DIR}/order_summary.csv"

echo "✓ Created: ${OUTPUT_DIR}/order_summary.csv"

# ============================================================================
# 3. PEAK PERFORMANCE SUMMARY
# ============================================================================

echo "Creating peak performance summary..."

cat > "${OUTPUT_DIR}/peak_performance.csv" << 'EOF'
endpoint_type,service,peak_throughput_req_s,optimal_concurrency,total_timeouts
EOF

# Health peaks
for service in python java csharp; do
    peak=$(awk -F',' -v svc="$service" '
        NR>1 && $5=="health" && $3==svc {
            if ($9 > max) {
                max = $9
                conc = $7
                timeouts_sum = 0
            }
        }
        END { printf "%.2f,%s", max, conc }
    ' "$CSV_FILE")

    total_timeouts=$(awk -F',' -v svc="$service" '
        NR>1 && $5=="health" && $3==svc {
            sum += $23
        }
        END { print sum+0 }
    ' "$CSV_FILE")

    echo "health,$service,$peak,$total_timeouts" >> "${OUTPUT_DIR}/peak_performance.csv"
done

# Order peaks
for service in python java csharp; do
    peak=$(awk -F',' -v svc="$service" '
        NR>1 && $5=="order" && $3==svc {
            if ($9 > max) {
                max = $9
                conc = $7
            }
        }
        END { printf "%.2f,%s", max, conc }
    ' "$CSV_FILE")

    total_timeouts=$(awk -F',' -v svc="$service" '
        NR>1 && $5=="order" && $3==svc {
            sum += $23
        }
        END { print sum+0 }
    ' "$CSV_FILE")

    echo "order,$service,$peak,$total_timeouts" >> "${OUTPUT_DIR}/peak_performance.csv"
done

echo "✓ Created: ${OUTPUT_DIR}/peak_performance.csv"

# ============================================================================
# 4. TEXT-BASED VISUALIZATION - HEALTH THROUGHPUT
# ============================================================================

echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo "HEALTH ENDPOINTS - THROUGHPUT BY CONCURRENCY"
echo "═══════════════════════════════════════════════════════════════════"
echo ""
printf "%-12s" "Concurrency"
echo "PYTHON      JAVA        C#"
echo "───────────────────────────────────────────────────────────────────"

for conc in 10 25 50 100 200 400 800; do
    printf "c=%-10s" "$conc"

    python_val=$(awk -F',' -v c="$conc" 'NR>1 && $5=="health" && $3=="python" && $7==c {print $9}' "$CSV_FILE")
    java_val=$(awk -F',' -v c="$conc" 'NR>1 && $5=="health" && $3=="java" && $7==c {print $9}' "$CSV_FILE")
    csharp_val=$(awk -F',' -v c="$conc" 'NR>1 && $5=="health" && $3=="csharp" && $7==c {print $9}' "$CSV_FILE")

    printf "%10s  " "${python_val:-N/A}"
    printf "%10s  " "${java_val:-N/A}"
    printf "%10s\n" "${csharp_val:-N/A}"
done

echo ""

# ============================================================================
# 5. TEXT-BASED VISUALIZATION - ORDER THROUGHPUT
# ============================================================================

echo "═══════════════════════════════════════════════════════════════════"
echo "ORDER ENDPOINTS - THROUGHPUT BY CONCURRENCY"
echo "═══════════════════════════════════════════════════════════════════"
echo ""
printf "%-12s" "Concurrency"
echo "PYTHON      JAVA        C#"
echo "───────────────────────────────────────────────────────────────────"

for conc in 10 25 50 100 150 200 300; do
    printf "c=%-10s" "$conc"

    python_val=$(awk -F',' -v c="$conc" 'NR>1 && $5=="order" && $3=="python" && $7==c {printf "%.1f", $9}' "$CSV_FILE")
    java_val=$(awk -F',' -v c="$conc" 'NR>1 && $5=="order" && $3=="java" && $7==c {printf "%.1f", $9}' "$CSV_FILE")
    csharp_val=$(awk -F',' -v c="$conc" 'NR>1 && $5=="order" && $3=="csharp" && $7==c {printf "%.1f", $9}' "$CSV_FILE")

    printf "%10s  " "${python_val:-N/A}"
    printf "%10s  " "${java_val:-N/A}"
    printf "%10s\n" "${csharp_val:-N/A}"
done

echo ""

# ============================================================================
# 6. MARKDOWN TABLE - PEAK PERFORMANCE
# ============================================================================

cat > "${OUTPUT_DIR}/README.md" << 'EOF'
# Benchmark Results - Variant Y

## Peak Performance Summary

### Health Endpoints

| Service | Peak Throughput | Optimal Concurrency | Total Timeouts |
|---------|-----------------|---------------------|----------------|
EOF

for service in python java csharp; do
    peak_throughput=$(awk -F',' -v svc="$service" '
        NR>1 && $5=="health" && $3==svc {
            if ($9 > max) {max = $9; conc = $7}
        }
        END {printf "%.0f req/s", max}
    ' "$CSV_FILE")

    optimal_c=$(awk -F',' -v svc="$service" '
        NR>1 && $5=="health" && $3==svc {
            if ($9 > max) {max = $9; conc = $7}
        }
        END {print conc}
    ' "$CSV_FILE")

    total_timeouts=$(awk -F',' -v svc="$service" '
        NR>1 && $5=="health" && $3==svc {sum += $23}
        END {print sum+0}
    ' "$CSV_FILE")

    service_upper=$(echo "$service" | tr '[:lower:]' '[:upper:]')
    echo "| $service_upper | $peak_throughput | c=$optimal_c | $total_timeouts |" >> "${OUTPUT_DIR}/README.md"
done

cat >> "${OUTPUT_DIR}/README.md" << 'EOF'

### Order Endpoints

| Service | Peak Throughput | Optimal Concurrency | Total Timeouts |
|---------|-----------------|---------------------|----------------|
EOF

for service in python java csharp; do
    peak_throughput=$(awk -F',' -v svc="$service" '
        NR>1 && $5=="order" && $3==svc {
            if ($9 > max) {max = $9; conc = $7}
        }
        END {printf "%.1f req/s", max}
    ' "$CSV_FILE")

    optimal_c=$(awk -F',' -v svc="$service" '
        NR>1 && $5=="order" && $3==svc {
            if ($9 > max) {max = $9; conc = $7}
        }
        END {print conc}
    ' "$CSV_FILE")

    total_timeouts=$(awk -F',' -v svc="$service" '
        NR>1 && $5=="order" && $3==svc {sum += $23}
        END {print sum+0}
    ' "$CSV_FILE")

    service_upper=$(echo "$service" | tr '[:lower:]' '[:upper:]')
    echo "| $service_upper | $peak_throughput | c=$optimal_c | $total_timeouts |" >> "${OUTPUT_DIR}/README.md"
done

cat >> "${OUTPUT_DIR}/README.md" << 'EOF'

## Files Available for Visualization

- `health_summary.csv` - Health endpoint metrics for each service/concurrency combination
- `order_summary.csv` - Order endpoint metrics for each service/concurrency combination
- `peak_performance.csv` - Peak performance summary for all endpoints
- `/tmp/test_sacred.csv` - Full raw data with all metrics

## How to Visualize

### Option 1: Excel/Google Sheets
1. Import `health_summary.csv` or `order_summary.csv`
2. Create pivot charts:
   - X-axis: concurrency
   - Y-axis: throughput_req_s
   - Series: service

### Option 2: Python/Pandas (if available)
```python
import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv('health_summary.csv')
for service in df['service'].unique():
    data = df[df['service'] == service]
    plt.plot(data['concurrency'], data['throughput_req_s'], label=service)
plt.legend()
plt.show()
```

### Option 3: Online Tools
- Upload CSV files to https://www.csvplot.com/
- Upload to Google Sheets and create charts
- Use https://plotly.com/chart-studio/ for interactive charts
EOF

echo "✓ Created: ${OUTPUT_DIR}/README.md"

echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo "SUMMARY REPORTS GENERATED"
echo "═══════════════════════════════════════════════════════════════════"
echo ""
echo "Output directory: $OUTPUT_DIR"
echo ""
echo "Files created:"
echo "  • health_summary.csv     - Health endpoint data"
echo "  • order_summary.csv      - Order endpoint data"
echo "  • peak_performance.csv   - Peak performance summary"
echo "  • README.md              - Markdown report with tables"
echo ""
echo "You can:"
echo "  1. Import CSV files into Excel/Google Sheets"
echo "  2. Use online visualization tools (csvplot.com, plotly)"
echo "  3. View README.md for formatted tables"
echo ""
echo "═══════════════════════════════════════════════════════════════════"
