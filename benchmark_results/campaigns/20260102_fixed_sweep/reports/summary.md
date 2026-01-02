# Benchmark Results - Variant Y

## Peak Performance Summary

### Health Endpoints

| Service | Peak Throughput | Optimal Concurrency | Total Timeouts |
|---------|-----------------|---------------------|----------------|
| PYTHON | 15728 req/s | c=10 | 0 |
| JAVA | 130623 req/s | c=100 | 109 |
| CSHARP | 338356 req/s | c=400 | 0 |

### Order Endpoints

| Service | Peak Throughput | Optimal Concurrency | Total Timeouts |
|---------|-----------------|---------------------|----------------|
| PYTHON | 360.7 req/s | c=10 | 866 |
| JAVA | 427.4 req/s | c=50 | 45 |
| CSHARP | 1802.0 req/s | c=10 | 0 |

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
