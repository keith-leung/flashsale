# Tools Directory

Analysis and reporting utilities for benchmark results.

## Available Tools

### generate_summary_reports.sh
**Purpose:** Generate comprehensive summary reports from raw CSV benchmark data

**Usage:**
```bash
bash tools/generate_summary_reports.sh <input_csv> [output_dir]
```

**Examples:**
```bash
# Generate report to stdout
bash tools/generate_summary_reports.sh /tmp/test_sacred.csv

# Generate report to file
bash tools/generate_summary_reports.sh \
  benchmark_results/campaigns/20260102_fixed_sweep/raw/full_data.csv \
  > benchmark_results/campaigns/20260102_fixed_sweep/reports/summary.md

# Process multiple CSVs
bash tools/generate_summary_reports.sh \
  benchmark_results/campaigns/my_campaign/raw/*.csv \
  benchmark_results/campaigns/my_campaign/reports/
```

**What it generates:**
1. `health_summary.csv` - Health endpoint metrics by service/concurrency
2. `order_summary.csv` - Order endpoint metrics by service/concurrency
3. `peak_performance.csv` - Peak performance summary for all endpoints
4. `README.md` - Formatted markdown tables with visualization guidance

**Output schema:**
```csv
service,concurrency,throughput_req_s,avg_latency_ms,p99_latency_ms,timeouts
PYTHON,10,15728.45,0.63,1.2,0
JAVA,100,130623.12,0.76,2.3,109
CSHARP,400,338356.89,1.18,3.1,0
```

### generate_pivot_summary.py
**Purpose:** Create pivot table summaries from benchmark results (Python)

**Usage:**
```bash
python3 tools/generate_pivot_summary.py <input_csv> <output_csv>
```

**Example:**
```bash
python3 tools/generate_pivot_summary.py \
  benchmark_results/campaigns/my_campaign/raw/full_data.csv \
  benchmark_results/campaigns/my_campaign/reports/pivot_summary.csv
```

**Requirements:** Python 3, pandas
**Note:** May not be available in all environments (use generate_summary_reports.sh as alternative)

### generate_performance_table.py
**Purpose:** Generate formatted performance comparison tables (Python)

**Usage:**
```bash
python3 tools/generate_performance_table.py <input_csv>
```

**Example:**
```bash
python3 tools/generate_performance_table.py \
  benchmark_results/campaigns/my_campaign/raw/full_data.csv \
  > benchmark_results/campaigns/my_campaign/reports/performance_table.md
```

**Requirements:** Python 3, pandas
**Note:** May not be available in all environments (use generate_summary_reports.sh as alternative)

### visualize_results.py
**Purpose:** Create charts and visualizations from benchmark data (Python)

**Usage:**
```bash
python3 tools/visualize_results.py <input_csv> <output_dir>
```

**Example:**
```bash
python3 tools/visualize_results.py \
  benchmark_results/campaigns/my_campaign/raw/full_data.csv \
  benchmark_results/campaigns/my_campaign/visualizations/
```

**What it generates:**
- Throughput vs concurrency charts
- Latency distribution charts
- Service comparison charts
- Error rate visualizations

**Requirements:** Python 3, pandas, matplotlib
**Note:** May not be available in all environments

## Common Workflows

### 1. Generate Complete Campaign Report
```bash
CAMPAIGN="benchmark_results/campaigns/20260102_my_campaign"

# Generate summary reports (works everywhere)
bash tools/generate_summary_reports.sh \
  "$CAMPAIGN/raw/full_data.csv" \
  "$CAMPAIGN/reports/"

# If Python available, generate visualizations
if command -v python3 &> /dev/null; then
  python3 tools/visualize_results.py \
    "$CAMPAIGN/raw/full_data.csv" \
    "$CAMPAIGN/visualizations/"
fi
```

### 2. Compare Two Campaigns
```bash
# Extract peak performance from each campaign
echo "Campaign 1:"
bash tools/generate_summary_reports.sh \
  benchmark_results/campaigns/campaign1/raw/full_data.csv | grep "Peak"

echo "Campaign 2:"
bash tools/generate_summary_reports.sh \
  benchmark_results/campaigns/campaign2/raw/full_data.csv | grep "Peak"
```

### 3. Quick Performance Check
```bash
# Get peak performance for all services
bash tools/generate_summary_reports.sh /tmp/test_results.csv | grep -A 20 "Peak Performance"
```

### 4. Export for Excel Analysis
```bash
# Generate CSV summaries
bash tools/generate_summary_reports.sh \
  benchmark_results/campaigns/my_campaign/raw/full_data.csv \
  benchmark_results/campaigns/my_campaign/reports/

# Import these files to Excel:
# - reports/health_summary.csv
# - reports/order_summary.csv
# - reports/peak_performance.csv
```

## CSV Output Schemas

### Health/Order Summary CSV
```csv
service,concurrency,throughput_req_s,avg_latency_ms,p50_latency_ms,p90_latency_ms,p99_latency_ms,timeouts
PYTHON,10,15728.45,0.63,0.50,0.85,1.20,0
PYTHON,25,15234.12,1.64,1.20,2.10,3.50,0
JAVA,100,130623.12,0.76,0.65,1.15,2.30,109
CSHARP,400,338356.89,1.18,0.95,1.80,3.10,0
```

### Peak Performance CSV
```csv
service,endpoint,peak_throughput_req_s,optimal_concurrency,total_timeouts
PYTHON,health,15728.45,10,0
PYTHON,order,360.68,10,866
JAVA,health,130623.12,100,109
JAVA,order,427.41,50,45
CSHARP,health,338356.89,400,0
CSHARP,order,1802.04,10,0
NGINX,health,9164.23,25,0
NGINX,order,753.45,25,142
```

### Full Data CSV (Input)
```csv
timestamp,variant,service,endpoint,test_type,threads,concurrency,duration_s,
req_per_sec,avg_latency_ms,p50_latency_ms,p90_latency_ms,p99_latency_ms,
max_latency_ms,stdev_latency_ms,total_requests,total_errors,error_rate_pct,
non_2xx_3xx,socket_errors_connect,socket_errors_read,socket_errors_write,
socket_errors_timeout,transfer_mb,throughput_mb_s,test_sequence,
throughput_increase_pct,decision
```

## Visualization Options

### Option 1: Bash Tool (Always Available)
```bash
bash tools/generate_summary_reports.sh input.csv reports/
# Creates formatted markdown tables + CSV files
```

### Option 2: Python Tools (If Available)
```bash
# Check if Python is available
if command -v python3 &> /dev/null; then
  python3 tools/visualize_results.py input.csv visualizations/
fi
```

### Option 3: Excel/Google Sheets (Manual)
1. Generate CSV summaries: `bash tools/generate_summary_reports.sh`
2. Import `health_summary.csv` or `order_summary.csv`
3. Create pivot charts:
   - X-axis: concurrency
   - Y-axis: throughput_req_s
   - Series: service

### Option 4: Online Tools (Manual)
- Upload CSV files to https://www.csvplot.com/
- Upload to Google Sheets and create charts
- Use https://plotly.com/chart-studio/ for interactive charts

## Troubleshooting

### Tool not found
```bash
# For bash scripts
ls -la tools/generate_summary_reports.sh
chmod +x tools/generate_summary_reports.sh

# For Python scripts
which python3
pip3 install pandas matplotlib  # If needed
```

### CSV parsing errors
```bash
# Check CSV format
head -5 your_data.csv

# Verify column headers match expected schema
head -1 your_data.csv | tr ',' '\n'
```

### Empty output
```bash
# Check if input file has data
wc -l your_data.csv

# Verify CSV has correct columns
awk -F',' 'NR==1 {print NF " columns"}' your_data.csv
```

### Python import errors
```bash
# Check Python version
python3 --version

# Install missing packages (if pip available)
pip3 install pandas matplotlib

# Fallback: Use bash tools instead
bash tools/generate_summary_reports.sh input.csv
```

## Creating Custom Analysis Tools

### Template for New Tool
```bash
#!/bin/bash
# tools/my_custom_analysis.sh

# Input validation
if [ $# -lt 1 ]; then
    echo "Usage: $0 <input_csv> [output_file]"
    exit 1
fi

INPUT_CSV="$1"
OUTPUT_FILE="${2:-/dev/stdout}"

# Check file exists
if [ ! -f "$INPUT_CSV" ]; then
    echo "Error: File not found: $INPUT_CSV"
    exit 1
fi

# Your analysis logic here
awk -F',' 'NR>1 {
    # Process CSV data
    print $1, $2, $3
}' "$INPUT_CSV" > "$OUTPUT_FILE"

echo "Analysis complete!"
```

### Make it executable
```bash
chmod +x tools/my_custom_analysis.sh
```

## See Also

- **Main README:** `/README.md` - Complete system documentation
- **Scripts:** `/scripts/README.md` - Benchmarking and verification scripts
- **Test Libraries:** `/lib/` - Reusable test functions (wrk_parser.sh, etc.)
- **Results:** `/benchmark_results/campaigns/` - Campaign results

---

**Last Updated:** 2026-01-02
**Maintained By:** Syracuse
