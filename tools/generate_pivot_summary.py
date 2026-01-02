#!/usr/bin/env python3
"""
Pivot Summary Generator - Variant Y

Parses CSV raw data from adaptive plateau detection and generates
comprehensive markdown performance summaries.

Usage:
    python3 generate_pivot_summary.py <csv_file>

Example:
    python3 generate_pivot_summary.py ./benchmark_results/variant_Y_raw_20260102_123456.csv
"""

import csv
import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict


def parse_csv_file(csv_path):
    """Parse CSV file and group results by service/endpoint."""
    results = defaultdict(list)

    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            key = (row['service'], row['endpoint'], row['test_type'])
            results[key].append(row)

    return results


def analyze_service_endpoint(tests):
    """Analyze test progression for a service/endpoint combination."""
    if not tests:
        return None

    # Find the result that represents the best performance
    # Priority: PLATEAU_CONFIRMED > MAX_CAPS_REACHED > SYSTEM_LIMIT > last test
    plateau_test = None
    max_caps_test = None
    system_limit_test = None

    for test in tests:
        if test['decision'] == 'PLATEAU_CONFIRMED':
            plateau_test = test
            break
        elif test['decision'] == 'MAX_CAPS_REACHED':
            max_caps_test = test
        elif test['decision'] == 'SYSTEM_LIMIT':
            system_limit_test = test

    # Determine best result
    best_test = plateau_test or max_caps_test or system_limit_test or tests[-1]

    return {
        'variant': best_test['variant'],
        'service': best_test['service'],
        'endpoint': best_test['endpoint'],
        'test_type': best_test['test_type'],
        'optimal_threads': int(best_test['threads']),
        'optimal_concurrency': int(best_test['concurrency']),
        'max_throughput': float(best_test['req_per_sec']),
        'avg_latency': float(best_test['avg_latency_ms']),
        'p50_latency': float(best_test['p50_latency_ms']),
        'p90_latency': float(best_test['p90_latency_ms']),
        'p99_latency': float(best_test['p99_latency_ms']),
        'total_tests': len(tests),
        'decision': best_test['decision'],
        'error_rate': float(best_test['error_rate_pct']),
        'all_tests': tests
    }


def generate_executive_summary(analyses):
    """Generate executive summary table."""
    lines = []

    lines.append("# Variant Y Performance Summary")
    lines.append("")
    lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    lines.append("## Executive Summary")
    lines.append("")
    lines.append("| Service | Endpoint | Type | Max Throughput | Optimal Config | Avg Latency | P90 Latency | P99 Latency | Result |")
    lines.append("|---------|----------|------|----------------|----------------|-------------|-------------|-------------|--------|")

    # Sort by service, then endpoint
    sorted_analyses = sorted(analyses, key=lambda x: (x['service'], x['endpoint']))

    for analysis in sorted_analyses:
        service = analysis['service']
        endpoint = analysis['endpoint']
        test_type = analysis['test_type']
        throughput = f"{analysis['max_throughput']:,.0f} req/s"
        config = f"t={analysis['optimal_threads']} c={analysis['optimal_concurrency']}"
        avg_lat = f"{analysis['avg_latency']:.2f}ms"
        p90_lat = f"{analysis['p90_latency']:.2f}ms"
        p99_lat = f"{analysis['p99_latency']:.2f}ms"

        # Decision icon
        decision = analysis['decision']
        if decision == 'PLATEAU_CONFIRMED':
            result = "✓ Plateau"
        elif decision == 'MAX_CAPS_REACHED':
            result = "🔝 Max Caps"
        elif decision == 'SYSTEM_LIMIT':
            result = "🛑 Limit"
        else:
            result = "⚠ Incomplete"

        lines.append(
            f"| {service} | {endpoint} | {test_type} | {throughput} | {config} | "
            f"{avg_lat} | {p90_lat} | {p99_lat} | {result} |"
        )

    lines.append("")
    return "\n".join(lines)


def generate_detailed_progression(analysis):
    """Generate detailed test progression for a service/endpoint."""
    lines = []

    service = analysis['service']
    endpoint = analysis['endpoint']
    test_type = analysis['test_type']

    lines.append(f"### {service} - {endpoint} ({test_type})")
    lines.append("")

    # Summary
    lines.append(f"**Result:** {analysis['decision']}")
    lines.append(f"**Tests Performed:** {analysis['total_tests']}")
    lines.append(f"**Optimal Configuration:** t={analysis['optimal_threads']}, c={analysis['optimal_concurrency']}")
    lines.append(f"**Peak Throughput:** {analysis['max_throughput']:,.0f} req/s")
    lines.append("")

    # Progression table
    lines.append("| Test | Threads | Concurrency | Duration | Throughput | Avg Lat | P90 Lat | P99 Lat | Increase | Decision |")
    lines.append("|------|---------|-------------|----------|------------|---------|---------|---------|----------|----------|")

    for test in analysis['all_tests']:
        seq = test['test_sequence']
        threads = test['threads']
        concurrency = test['concurrency']
        duration = test['duration_s']
        throughput = f"{float(test['req_per_sec']):,.0f}"
        avg_lat = f"{float(test['avg_latency_ms']):.1f}"
        p90_lat = f"{float(test['p90_latency_ms']):.1f}"
        p99_lat = f"{float(test['p99_latency_ms']):.1f}"
        increase = test['throughput_increase_pct']
        if increase != 'N/A':
            increase = f"{float(increase):+.1f}%"
        decision = test['decision']

        lines.append(
            f"| {seq} | {threads} | {concurrency} | {duration}s | {throughput} | "
            f"{avg_lat}ms | {p90_lat}ms | {p99_lat}ms | {increase} | {decision} |"
        )

    lines.append("")
    return "\n".join(lines)


def generate_methodology_section():
    """Generate methodology explanation."""
    lines = []

    lines.append("## Methodology")
    lines.append("")
    lines.append("### Adaptive Plateau Detection")
    lines.append("")
    lines.append("Tests use intelligent adaptive testing to find true performance plateaus:")
    lines.append("")
    lines.append("1. **Start Small:** Begin with low concurrency (t=4, c=10)")
    lines.append("2. **Analyze Growth:** Calculate throughput increase percentage")
    lines.append("3. **Adaptive Adjustment:**")
    lines.append("   - **Significant Growth (>5%):** Increase aggressively (threads × 1.5, concurrency × 2)")
    lines.append("   - **Moderate Growth (2-5%):** Increase moderately (threads × 1.2, concurrency × 1.5)")
    lines.append("   - **Marginal Growth (0-2%):** Increase slightly to confirm plateau (threads × 1.1, concurrency × 1.2)")
    lines.append("4. **Plateau Detection:** <2% variance across 3 consecutive tests → PLATEAU CONFIRMED")
    lines.append("5. **Error Policy:** Stop immediately on ANY 503 error → SYSTEM_LIMIT")
    lines.append("6. **Caps:** Maximum threads=24, concurrency=2000")
    lines.append("")
    lines.append("### Decision Types")
    lines.append("")
    lines.append("- **✓ PLATEAU_CONFIRMED:** True performance plateau detected (<2% variance)")
    lines.append("- **🔝 MAX_CAPS_REACHED:** Hit maximum thread/concurrency caps")
    lines.append("- **🛑 SYSTEM_LIMIT:** Errors detected (503s), safe limit found")
    lines.append("- **⚠ INCOMPLETE:** Testing stopped before plateau detection")
    lines.append("")

    return "\n".join(lines)


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 generate_pivot_summary.py <csv_file>")
        sys.exit(1)

    csv_path = sys.argv[1]

    if not Path(csv_path).exists():
        print(f"Error: CSV file not found: {csv_path}")
        sys.exit(1)

    print(f"Parsing CSV file: {csv_path}")

    # Parse CSV
    results = parse_csv_file(csv_path)

    if not results:
        print("Error: No data found in CSV file")
        sys.exit(1)

    print(f"Found {len(results)} service/endpoint combinations")

    # Analyze each service/endpoint
    analyses = []
    for key, tests in results.items():
        service, endpoint, test_type = key
        print(f"  Analyzing: {service} {endpoint} ({test_type}) - {len(tests)} tests")
        analysis = analyze_service_endpoint(tests)
        if analysis:
            analyses.append(analysis)

    # Generate markdown output
    markdown_lines = []

    # Executive summary
    markdown_lines.append(generate_executive_summary(analyses))

    # Detailed progressions
    markdown_lines.append("## Detailed Test Progressions")
    markdown_lines.append("")

    for analysis in sorted(analyses, key=lambda x: (x['service'], x['endpoint'])):
        markdown_lines.append(generate_detailed_progression(analysis))

    # Methodology
    markdown_lines.append(generate_methodology_section())

    # Notes
    markdown_lines.append("## Notes")
    markdown_lines.append("")
    markdown_lines.append("- All tests use adaptive concurrency/thread adjustment")
    markdown_lines.append("- Test duration dynamically adjusts based on concurrency (base + additional time for high loads)")
    markdown_lines.append("- Throughput values represent requests per second achieved at each test level")
    markdown_lines.append("- Latency values are in milliseconds (avg, P50, P90, P99)")
    markdown_lines.append("")

    markdown_output = "\n".join(markdown_lines)

    # Write to file
    output_path = Path(csv_path).parent / f"summary_{Path(csv_path).stem.replace('variant_Y_raw_', '')}.md"
    with open(output_path, 'w') as f:
        f.write(markdown_output)

    print(f"\nPivot summary written to: {output_path}")
    print("")
    print("=" * 80)
    print(markdown_output)
    print("=" * 80)


if __name__ == "__main__":
    main()
