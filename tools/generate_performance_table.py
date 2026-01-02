#!/usr/bin/env python3
"""
Performance Table Generator - Variant Y

Parses benchmark CSV files and generates markdown performance tables.

Usage:
    python3 generate_performance_table.py [results_dir]

Example:
    python3 generate_performance_table.py ./benchmark_results
"""

import csv
import glob
import os
import sys
from datetime import datetime
from pathlib import Path

def parse_csv_file(csv_path):
    """Parse a benchmark CSV file and extract key metrics."""
    max_throughput = 0
    max_throughput_row = None

    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                throughput = float(row['requests_per_sec'])
                if throughput > max_throughput:
                    max_throughput = throughput
                    max_throughput_row = row
            except (ValueError, KeyError):
                continue

    # If no data, return None
    if not max_throughput_row:
        return None

    return {
        'max_throughput': float(max_throughput_row['requests_per_sec']),
        'concurrency': int(max_throughput_row['concurrency']),
        'avg_latency': float(max_throughput_row['avg_latency_ms']),
        'p50_latency': float(max_throughput_row['p50_latency_ms']),
        'p90_latency': float(max_throughput_row['p90_latency_ms']),
        'p99_latency': float(max_throughput_row['p99_latency_ms']),
        'plateau_detected': max_throughput_row['plateau_detected'] == 'yes'
    }

def extract_service_endpoint(filename):
    """Extract service and endpoint from filename."""
    # Format: plateau_SERVICE_TIMESTAMP.csv
    parts = filename.replace('.csv', '').split('_')
    if len(parts) >= 2:
        service = parts[1]
        return service
    return "Unknown"

def generate_markdown_table(results_data):
    """Generate markdown table from parsed results."""
    markdown = []

    # Header
    markdown.append("# Variant Y Performance Results")
    markdown.append("")
    markdown.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    markdown.append("")
    markdown.append("## Summary Table")
    markdown.append("")

    # Table header
    markdown.append("| Service/Endpoint | Max Throughput (req/s) | Concurrency | Avg Latency (ms) | P90 Latency (ms) | P99 Latency (ms) | Plateau Detected |")
    markdown.append("|------------------|------------------------|-------------|------------------|------------------|------------------|------------------|")

    # Table rows - sort by service name
    for service in sorted(results_data.keys()):
        data = results_data[service]
        plateau_icon = "✓" if data['plateau_detected'] else "✗"

        markdown.append(
            f"| {service} | "
            f"{data['max_throughput']:,.0f} | "
            f"{data['concurrency']:,} | "
            f"{data['avg_latency']:.2f} | "
            f"{data['p90_latency']:.2f} | "
            f"{data['p99_latency']:.2f} | "
            f"{plateau_icon} |"
        )

    markdown.append("")
    markdown.append("## Notes")
    markdown.append("")
    markdown.append("- **Max Throughput**: Highest requests/second achieved during testing")
    markdown.append("- **Concurrency**: Number of concurrent connections at max throughput")
    markdown.append("- **Plateau Detected**: Whether performance plateau was detected (✓ = yes, ✗ = no)")
    markdown.append("- **Test Duration**: 30 seconds per concurrency level")
    markdown.append("")
    markdown.append("## Methodology")
    markdown.append("")
    markdown.append("Tests use automated plateau detection:")
    markdown.append("- Start with low concurrency (10 connections)")
    markdown.append("- Incrementally increase concurrency")
    markdown.append("- Plateau detected when throughput increase <5% with 50%+ more connections")
    markdown.append("- Each test runs for 30 seconds")
    markdown.append("")

    return "\n".join(markdown)

def main():
    # Parse arguments
    results_dir = sys.argv[1] if len(sys.argv) > 1 else "./benchmark_results"

    if not os.path.exists(results_dir):
        print(f"Error: Results directory not found: {results_dir}")
        sys.exit(1)

    # Find all CSV files
    csv_pattern = os.path.join(results_dir, "plateau_*.csv")
    csv_files = glob.glob(csv_pattern)

    if not csv_files:
        print(f"Error: No benchmark CSV files found in {results_dir}")
        print(f"Pattern: {csv_pattern}")
        sys.exit(1)

    print(f"Found {len(csv_files)} benchmark files")
    print("")

    # Parse all CSV files
    results_data = {}
    for csv_file in csv_files:
        filename = os.path.basename(csv_file)
        print(f"Processing: {filename}")

        service = extract_service_endpoint(filename)
        data = parse_csv_file(csv_file)

        if data:
            results_data[service] = data
            print(f"  → Max throughput: {data['max_throughput']:,.0f} req/s @ {data['concurrency']} connections")
        else:
            print(f"  → No data found")

    print("")

    if not results_data:
        print("Error: No valid data found in CSV files")
        sys.exit(1)

    # Generate markdown table
    markdown_output = generate_markdown_table(results_data)

    # Write to file
    output_file = os.path.join(results_dir, f"performance_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md")
    with open(output_file, 'w') as f:
        f.write(markdown_output)

    print(f"Performance table written to: {output_file}")
    print("")
    print("=" * 80)
    print(markdown_output)
    print("=" * 80)

if __name__ == "__main__":
    main()
