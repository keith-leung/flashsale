#!/usr/bin/env python3
"""
Benchmark Results Visualization
Generates comprehensive charts for fixed concurrency sweep testing
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
import seaborn as sns

# Set style
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (16, 10)
plt.rcParams['font.size'] = 10

# Read CSV data
csv_file = "/tmp/test_sacred.csv"
df = pd.read_csv(csv_file)

# Filter out failed tests
df = df[df['decision'] != 'TEST_FAILED']

print(f"Loaded {len(df)} test records")
print(f"Services: {df['service'].unique()}")
print(f"Test types: {df['test_type'].unique()}")

# Create output directory
output_dir = Path("/tmp/benchmark_charts")
output_dir.mkdir(exist_ok=True)

# ============================================================================
# 1. HEALTH ENDPOINTS - THROUGHPUT BY CONCURRENCY
# ============================================================================
print("\n[1/8] Generating health endpoint throughput chart...")

health_df = df[df['test_type'] == 'health'].copy()
health_df = health_df[health_df['service'].isin(['python', 'java', 'csharp'])]

fig, ax = plt.subplots(figsize=(14, 8))

for service in ['python', 'java', 'csharp']:
    service_data = health_df[health_df['service'] == service].sort_values('concurrency')
    ax.plot(service_data['concurrency'], service_data['req_per_sec'],
            marker='o', linewidth=2.5, markersize=8, label=service.upper())

ax.set_xlabel('Concurrency Level', fontsize=13, fontweight='bold')
ax.set_ylabel('Throughput (req/s)', fontsize=13, fontweight='bold')
ax.set_title('Health Endpoints: Throughput vs Concurrency\nVariant Y - Fixed Sweep Testing',
             fontsize=15, fontweight='bold', pad=20)
ax.legend(fontsize=12, loc='best')
ax.grid(True, alpha=0.3)
ax.set_xscale('log')
ax.set_yscale('log')

# Add peak annotations
for service in ['python', 'java', 'csharp']:
    service_data = health_df[health_df['service'] == service]
    max_row = service_data.loc[service_data['req_per_sec'].idxmax()]
    ax.annotate(f"{max_row['req_per_sec']:,.0f} req/s\n(c={max_row['concurrency']:.0f})",
                xy=(max_row['concurrency'], max_row['req_per_sec']),
                xytext=(10, 10), textcoords='offset points',
                fontsize=9, fontweight='bold',
                bbox=dict(boxstyle='round,pad=0.5', facecolor='yellow', alpha=0.7),
                arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0'))

plt.tight_layout()
plt.savefig(output_dir / "01_health_throughput_vs_concurrency.png", dpi=150, bbox_inches='tight')
print(f"✓ Saved: {output_dir / '01_health_throughput_vs_concurrency.png'}")
plt.close()

# ============================================================================
# 2. ORDER ENDPOINTS - THROUGHPUT BY CONCURRENCY
# ============================================================================
print("[2/8] Generating order endpoint throughput chart...")

order_df = df[df['test_type'] == 'order'].copy()

fig, ax = plt.subplots(figsize=(14, 8))

for service in ['python', 'java', 'csharp']:
    service_data = order_df[order_df['service'] == service].sort_values('concurrency')
    ax.plot(service_data['concurrency'], service_data['req_per_sec'],
            marker='s', linewidth=2.5, markersize=8, label=service.upper())

ax.set_xlabel('Concurrency Level', fontsize=13, fontweight='bold')
ax.set_ylabel('Throughput (req/s)', fontsize=13, fontweight='bold')
ax.set_title('Order Endpoints: Throughput vs Concurrency (Database-Bound)\nVariant Y - Fixed Sweep Testing',
             fontsize=15, fontweight='bold', pad=20)
ax.legend(fontsize=12, loc='best')
ax.grid(True, alpha=0.3)

# Add peak annotations
for service in ['python', 'java', 'csharp']:
    service_data = order_df[order_df['service'] == service]
    max_row = service_data.loc[service_data['req_per_sec'].idxmax()]
    ax.annotate(f"{max_row['req_per_sec']:,.1f} req/s\n(c={max_row['concurrency']:.0f})",
                xy=(max_row['concurrency'], max_row['req_per_sec']),
                xytext=(10, 10), textcoords='offset points',
                fontsize=9, fontweight='bold',
                bbox=dict(boxstyle='round,pad=0.5', facecolor='lightgreen', alpha=0.7),
                arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0'))

plt.tight_layout()
plt.savefig(output_dir / "02_order_throughput_vs_concurrency.png", dpi=150, bbox_inches='tight')
print(f"✓ Saved: {output_dir / '02_order_throughput_vs_concurrency.png'}")
plt.close()

# ============================================================================
# 3. PEAK PERFORMANCE COMPARISON - BAR CHART
# ============================================================================
print("[3/8] Generating peak performance comparison chart...")

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7))

# Health peaks
health_peaks = []
for service in ['python', 'java', 'csharp']:
    service_data = health_df[health_df['service'] == service]
    max_throughput = service_data['req_per_sec'].max()
    health_peaks.append({'service': service.upper(), 'throughput': max_throughput})

health_peaks_df = pd.DataFrame(health_peaks)
bars1 = ax1.bar(health_peaks_df['service'], health_peaks_df['throughput'],
                color=['#ff6b6b', '#4ecdc4', '#95e1d3'], edgecolor='black', linewidth=1.5)
ax1.set_ylabel('Peak Throughput (req/s)', fontsize=12, fontweight='bold')
ax1.set_title('Health Endpoints - Peak Performance', fontsize=13, fontweight='bold')
ax1.grid(True, axis='y', alpha=0.3)

# Add value labels on bars
for bar in bars1:
    height = bar.get_height()
    ax1.text(bar.get_x() + bar.get_width()/2., height,
            f'{height:,.0f}',
            ha='center', va='bottom', fontsize=11, fontweight='bold')

# Order peaks
order_peaks = []
for service in ['python', 'java', 'csharp']:
    service_data = order_df[order_df['service'] == service]
    max_throughput = service_data['req_per_sec'].max()
    order_peaks.append({'service': service.upper(), 'throughput': max_throughput})

order_peaks_df = pd.DataFrame(order_peaks)
bars2 = ax2.bar(order_peaks_df['service'], order_peaks_df['throughput'],
                color=['#ff6b6b', '#4ecdc4', '#95e1d3'], edgecolor='black', linewidth=1.5)
ax2.set_ylabel('Peak Throughput (req/s)', fontsize=12, fontweight='bold')
ax2.set_title('Order Endpoints - Peak Performance', fontsize=13, fontweight='bold')
ax2.grid(True, axis='y', alpha=0.3)

# Add value labels on bars
for bar in bars2:
    height = bar.get_height()
    ax2.text(bar.get_x() + bar.get_width()/2., height,
            f'{height:,.1f}',
            ha='center', va='bottom', fontsize=11, fontweight='bold')

plt.suptitle('Peak Performance Comparison - Variant Y', fontsize=16, fontweight='bold', y=1.02)
plt.tight_layout()
plt.savefig(output_dir / "03_peak_performance_comparison.png", dpi=150, bbox_inches='tight')
print(f"✓ Saved: {output_dir / '03_peak_performance_comparison.png'}")
plt.close()

# ============================================================================
# 4. LATENCY ANALYSIS - P50, P90, P99
# ============================================================================
print("[4/8] Generating latency analysis chart...")

fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))

# Health - P50 Latency
for service in ['python', 'java', 'csharp']:
    service_data = health_df[health_df['service'] == service].sort_values('concurrency')
    ax1.plot(service_data['concurrency'], service_data['p50_latency_ms'],
            marker='o', linewidth=2, label=service.upper())
ax1.set_xlabel('Concurrency', fontsize=11, fontweight='bold')
ax1.set_ylabel('P50 Latency (ms)', fontsize=11, fontweight='bold')
ax1.set_title('Health Endpoints - Median Latency (P50)', fontsize=12, fontweight='bold')
ax1.legend()
ax1.grid(True, alpha=0.3)
ax1.set_xscale('log')

# Health - P99 Latency
for service in ['python', 'java', 'csharp']:
    service_data = health_df[health_df['service'] == service].sort_values('concurrency')
    ax2.plot(service_data['concurrency'], service_data['p99_latency_ms'],
            marker='o', linewidth=2, label=service.upper())
ax2.set_xlabel('Concurrency', fontsize=11, fontweight='bold')
ax2.set_ylabel('P99 Latency (ms)', fontsize=11, fontweight='bold')
ax2.set_title('Health Endpoints - 99th Percentile Latency (P99)', fontsize=12, fontweight='bold')
ax2.legend()
ax2.grid(True, alpha=0.3)
ax2.set_xscale('log')

# Order - P50 Latency
for service in ['python', 'java', 'csharp']:
    service_data = order_df[order_df['service'] == service].sort_values('concurrency')
    ax3.plot(service_data['concurrency'], service_data['p50_latency_ms'],
            marker='s', linewidth=2, label=service.upper())
ax3.set_xlabel('Concurrency', fontsize=11, fontweight='bold')
ax3.set_ylabel('P50 Latency (ms)', fontsize=11, fontweight='bold')
ax3.set_title('Order Endpoints - Median Latency (P50)', fontsize=12, fontweight='bold')
ax3.legend()
ax3.grid(True, alpha=0.3)

# Order - P99 Latency
for service in ['python', 'java', 'csharp']:
    service_data = order_df[order_df['service'] == service].sort_values('concurrency')
    ax4.plot(service_data['concurrency'], service_data['p99_latency_ms'],
            marker='s', linewidth=2, label=service.upper())
ax4.set_xlabel('Concurrency', fontsize=11, fontweight='bold')
ax4.set_ylabel('P99 Latency (ms)', fontsize=11, fontweight='bold')
ax4.set_title('Order Endpoints - 99th Percentile Latency (P99)', fontsize=12, fontweight='bold')
ax4.legend()
ax4.grid(True, alpha=0.3)

plt.suptitle('Latency Analysis - Variant Y', fontsize=16, fontweight='bold', y=1.00)
plt.tight_layout()
plt.savefig(output_dir / "04_latency_analysis.png", dpi=150, bbox_inches='tight')
print(f"✓ Saved: {output_dir / '04_latency_analysis.png'}")
plt.close()

# ============================================================================
# 5. ERROR RATES AND TIMEOUTS
# ============================================================================
print("[5/8] Generating error rate analysis chart...")

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7))

# Health errors
for service in ['python', 'java', 'csharp']:
    service_data = health_df[health_df['service'] == service].sort_values('concurrency')
    ax1.plot(service_data['concurrency'], service_data['socket_errors_timeout'],
            marker='o', linewidth=2.5, markersize=8, label=service.upper())
ax1.set_xlabel('Concurrency Level', fontsize=12, fontweight='bold')
ax1.set_ylabel('Timeout Errors', fontsize=12, fontweight='bold')
ax1.set_title('Health Endpoints - Timeout Errors by Concurrency', fontsize=13, fontweight='bold')
ax1.legend(fontsize=11)
ax1.grid(True, alpha=0.3)
ax1.set_xscale('log')

# Order errors
for service in ['python', 'java', 'csharp']:
    service_data = order_df[order_df['service'] == service].sort_values('concurrency')
    ax2.plot(service_data['concurrency'], service_data['socket_errors_timeout'],
            marker='s', linewidth=2.5, markersize=8, label=service.upper())
ax2.set_xlabel('Concurrency Level', fontsize=12, fontweight='bold')
ax2.set_ylabel('Timeout Errors', fontsize=12, fontweight='bold')
ax2.set_title('Order Endpoints - Timeout Errors by Concurrency', fontsize=13, fontweight='bold')
ax2.legend(fontsize=11)
ax2.grid(True, alpha=0.3)

plt.suptitle('Error Rate Analysis - Variant Y', fontsize=16, fontweight='bold', y=1.00)
plt.tight_layout()
plt.savefig(output_dir / "05_error_rate_analysis.png", dpi=150, bbox_inches='tight')
print(f"✓ Saved: {output_dir / '05_error_rate_analysis.png'}")
plt.close()

# ============================================================================
# 6. NGINX GATEWAY COMPARISON
# ============================================================================
print("[6/8] Generating Nginx gateway comparison chart...")

nginx_health = df[df['test_type'] == 'nginx_health']
nginx_order = df[df['test_type'] == 'nginx_order']

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7))

# Nginx health vs direct services
if len(nginx_health) > 0:
    nginx_health_sorted = nginx_health.sort_values('concurrency')
    ax1.plot(nginx_health_sorted['concurrency'], nginx_health_sorted['req_per_sec'],
            marker='D', linewidth=3, markersize=10, label='NGINX Gateway', color='red')

    # Add Python for comparison
    python_health = health_df[health_df['service'] == 'python'].sort_values('concurrency')
    # Filter to matching concurrency levels
    matching_c = nginx_health_sorted['concurrency'].values
    python_matching = python_health[python_health['concurrency'].isin(matching_c)]
    ax1.plot(python_matching['concurrency'], python_matching['req_per_sec'],
            marker='o', linewidth=2, markersize=8, label='Python Direct', color='blue', alpha=0.6)

ax1.set_xlabel('Concurrency Level', fontsize=12, fontweight='bold')
ax1.set_ylabel('Throughput (req/s)', fontsize=12, fontweight='bold')
ax1.set_title('Health Endpoint: Nginx Gateway vs Direct Access', fontsize=13, fontweight='bold')
ax1.legend(fontsize=11)
ax1.grid(True, alpha=0.3)

# Nginx order vs direct services
if len(nginx_order) > 0:
    nginx_order_sorted = nginx_order.sort_values('concurrency')
    ax2.plot(nginx_order_sorted['concurrency'], nginx_order_sorted['req_per_sec'],
            marker='D', linewidth=3, markersize=10, label='NGINX Gateway (Load Balanced)', color='red')

    # Add all services for comparison
    for service, color in [('python', 'blue'), ('java', 'green'), ('csharp', 'purple')]:
        service_data = order_df[order_df['service'] == service].sort_values('concurrency')
        matching_c = nginx_order_sorted['concurrency'].values
        service_matching = service_data[service_data['concurrency'].isin(matching_c)]
        ax2.plot(service_matching['concurrency'], service_matching['req_per_sec'],
                marker='o', linewidth=2, markersize=6, label=f'{service.upper()} Direct',
                color=color, alpha=0.6)

ax2.set_xlabel('Concurrency Level', fontsize=12, fontweight='bold')
ax2.set_ylabel('Throughput (req/s)', fontsize=12, fontweight='bold')
ax2.set_title('Order Endpoint: Nginx Gateway vs Direct Access', fontsize=13, fontweight='bold')
ax2.legend(fontsize=10)
ax2.grid(True, alpha=0.3)

plt.suptitle('Nginx Gateway Performance - Variant Y', fontsize=16, fontweight='bold', y=1.00)
plt.tight_layout()
plt.savefig(output_dir / "06_nginx_gateway_comparison.png", dpi=150, bbox_inches='tight')
print(f"✓ Saved: {output_dir / '06_nginx_gateway_comparison.png'}")
plt.close()

# ============================================================================
# 7. THROUGHPUT HEATMAP
# ============================================================================
print("[7/8] Generating throughput heatmap...")

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7))

# Health heatmap
health_pivot = health_df.pivot_table(
    values='req_per_sec',
    index='service',
    columns='concurrency',
    aggfunc='first'
)
sns.heatmap(health_pivot, annot=True, fmt='.0f', cmap='YlOrRd', ax=ax1,
            cbar_kws={'label': 'Throughput (req/s)'})
ax1.set_title('Health Endpoints - Throughput Heatmap', fontsize=13, fontweight='bold')
ax1.set_xlabel('Concurrency Level', fontsize=11, fontweight='bold')
ax1.set_ylabel('Service', fontsize=11, fontweight='bold')

# Order heatmap
order_pivot = order_df.pivot_table(
    values='req_per_sec',
    index='service',
    columns='concurrency',
    aggfunc='first'
)
sns.heatmap(order_pivot, annot=True, fmt='.1f', cmap='YlGnBu', ax=ax2,
            cbar_kws={'label': 'Throughput (req/s)'})
ax2.set_title('Order Endpoints - Throughput Heatmap', fontsize=13, fontweight='bold')
ax2.set_xlabel('Concurrency Level', fontsize=11, fontweight='bold')
ax2.set_ylabel('Service', fontsize=11, fontweight='bold')

plt.suptitle('Throughput Heatmaps - Variant Y', fontsize=16, fontweight='bold', y=1.00)
plt.tight_layout()
plt.savefig(output_dir / "07_throughput_heatmap.png", dpi=150, bbox_inches='tight')
print(f"✓ Saved: {output_dir / '07_throughput_heatmap.png'}")
plt.close()

# ============================================================================
# 8. EFFICIENCY METRICS - THROUGHPUT PER THREAD
# ============================================================================
print("[8/8] Generating efficiency metrics chart...")

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7))

# Calculate throughput per thread
health_df['efficiency'] = health_df['req_per_sec'] / health_df['threads']
order_df['efficiency'] = order_df['req_per_sec'] / order_df['threads']

# Health efficiency
for service in ['python', 'java', 'csharp']:
    service_data = health_df[health_df['service'] == service].sort_values('concurrency')
    ax1.plot(service_data['concurrency'], service_data['efficiency'],
            marker='o', linewidth=2.5, markersize=8, label=service.upper())
ax1.set_xlabel('Concurrency Level', fontsize=12, fontweight='bold')
ax1.set_ylabel('Throughput per Thread (req/s)', fontsize=12, fontweight='bold')
ax1.set_title('Health Endpoints - Thread Efficiency', fontsize=13, fontweight='bold')
ax1.legend(fontsize=11)
ax1.grid(True, alpha=0.3)
ax1.set_xscale('log')
ax1.set_yscale('log')

# Order efficiency
for service in ['python', 'java', 'csharp']:
    service_data = order_df[order_df['service'] == service].sort_values('concurrency')
    ax2.plot(service_data['concurrency'], service_data['efficiency'],
            marker='s', linewidth=2.5, markersize=8, label=service.upper())
ax2.set_xlabel('Concurrency Level', fontsize=12, fontweight='bold')
ax2.set_ylabel('Throughput per Thread (req/s)', fontsize=12, fontweight='bold')
ax2.set_title('Order Endpoints - Thread Efficiency', fontsize=13, fontweight='bold')
ax2.legend(fontsize=11)
ax2.grid(True, alpha=0.3)

plt.suptitle('Thread Efficiency Analysis - Variant Y', fontsize=16, fontweight='bold', y=1.00)
plt.tight_layout()
plt.savefig(output_dir / "08_thread_efficiency.png", dpi=150, bbox_inches='tight')
print(f"✓ Saved: {output_dir / '08_thread_efficiency.png'}")
plt.close()

# ============================================================================
# SUMMARY REPORT
# ============================================================================
print("\n" + "="*70)
print("VISUALIZATION COMPLETE!")
print("="*70)
print(f"\nGenerated 8 comprehensive charts in: {output_dir}")
print("\nChart List:")
print("  01. Health Endpoints - Throughput vs Concurrency")
print("  02. Order Endpoints - Throughput vs Concurrency")
print("  03. Peak Performance Comparison")
print("  04. Latency Analysis (P50, P90, P99)")
print("  05. Error Rate Analysis")
print("  06. Nginx Gateway Comparison")
print("  07. Throughput Heatmaps")
print("  08. Thread Efficiency Analysis")
print("\n" + "="*70)

# Print summary statistics
print("\nSUMMARY STATISTICS:")
print("-" * 70)
print("\nHEALTH ENDPOINTS - Peak Performance:")
for service in ['python', 'java', 'csharp']:
    service_data = health_df[health_df['service'] == service]
    max_row = service_data.loc[service_data['req_per_sec'].idxmax()]
    print(f"  {service.upper():8s}: {max_row['req_per_sec']:>10,.0f} req/s at c={max_row['concurrency']:.0f}")

print("\nORDER ENDPOINTS - Peak Performance:")
for service in ['python', 'java', 'csharp']:
    service_data = order_df[order_df['service'] == service]
    max_row = service_data.loc[service_data['req_per_sec'].idxmax()]
    print(f"  {service.upper():8s}: {max_row['req_per_sec']:>10,.1f} req/s at c={max_row['concurrency']:.0f}")

print("\nORDER ENDPOINTS - Total Timeouts:")
for service in ['python', 'java', 'csharp']:
    service_data = order_df[order_df['service'] == service]
    total_timeouts = service_data['socket_errors_timeout'].sum()
    print(f"  {service.upper():8s}: {total_timeouts:>10,} timeouts")

print("\n" + "="*70)
