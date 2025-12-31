# Multi-WSL Deployment Guide

This guide explains how to set up multiple WSL instances to run different architectural variants in isolated environments.

## Architecture Overview

**Problem:** Podman 3.4.4 has unreliable DNS resolution and cannot consistently assign static IPs when multiple variants run in the same network namespace.

**Solution:** Run each architectural variant in a dedicated WSL instance with its own Podman network.

## Benefits

- **No IP conflicts** - Each variant uses the same IPs (10.88.0.2-7) in isolated namespaces
- **No port conflicts** - All variants use standard ports (8000, 8080, 8082)
- **Fair resource allocation** - Dedicated CPU cores and memory per variant
- **Clean isolation** - No network interference during benchmarks
- **Reproducible** - Each environment is identical except for service implementations

## WSL Instance Setup

### 1. Export This WSL Instance (Baseline Variant)

```bash
# From Windows PowerShell (not WSL)
wsl --export orange-315-baseline C:\wsl-exports\orange-315-baseline.tar
```

### 2. Import as New WSL Instance (e.g., Variant X)

```bash
# From Windows PowerShell
wsl --import orange-315-variant-x C:\wsl-distros\orange-315-variant-x C:\wsl-exports\orange-315-baseline.tar

# Launch the new instance
wsl -d orange-315-variant-x
```

### 3. Configure Default User

```bash
# Inside the new WSL instance
# Add to /etc/wsl.conf
cat << 'EOF' | sudo tee /etc/wsl.conf
[user]
default=syracuse
EOF

# Exit and restart WSL instance from PowerShell
wsl --terminate orange-315-variant-x
wsl -d orange-315-variant-x
```

### 4. Clean Up Old Variant Data

```bash
# Inside the new WSL instance
cd /home/syracuse/orange-315-forever

# Stop all containers
podman-compose down

# Clean volumes and data
podman volume prune -f
podman system prune -af

# Update README to reflect new variant
# Modify service implementations for variant-specific behavior
```

## Managing Multiple WSL Instances

### List All WSL Instances

```bash
# From Windows PowerShell
wsl --list --verbose
```

### Switch Between Instances

```bash
# Launch specific instance
wsl -d orange-315-baseline
wsl -d orange-315-variant-x

# Set default instance
wsl --set-default orange-315-baseline
```

### Start Services in Each Instance

```bash
# Instance 1: Baseline variant
wsl -d orange-315-baseline
cd /home/syracuse/orange-315-forever
podman-compose up -d

# Instance 2: Variant X
wsl -d orange-315-variant-x
cd /home/syracuse/orange-315-forever
podman-compose up -d
```

### Run Benchmarks Across Variants

```bash
# Baseline variant (WSL Instance 1)
wsl -d orange-315-baseline
wrk -t12 -c100 -d30s -s python-service/wrk_order_script.lua http://localhost:8000/api/v1/orders

# Variant X (WSL Instance 2)
wsl -d orange-315-variant-x
wrk -t12 -c100 -d30s -s python-service/wrk_order_script.lua http://localhost:8000/api/v1/orders
```

## Network Configuration

Each WSL instance gets its own:
- Podman network (10.88.0.0/16)
- Static IP allocations (10.88.0.2-7)
- Host port mappings (8000, 8080, 8082, 3306, 6379)

**No conflicts** because WSL instances have separate network namespaces.

## Resource Allocation Per Instance

Each WSL instance should be configured with:

```bash
# .wslconfig in Windows user directory (C:\Users\<username>\.wslconfig)
[orange-315-baseline]
memory=32GB
processors=24
swap=8GB

[orange-315-variant-x]
memory=32GB
processors=24
swap=8GB
```

## Variant Implementation Workflow

### Creating a New Variant

1. **Export baseline WSL instance** (one-time setup)
2. **Import as new WSL instance** with variant name
3. **Modify service implementations** for variant-specific behavior
   - Example: Variant X adds aggressive Redis caching
   - Example: Variant Y uses read replicas
4. **Update README.md** to document variant specifics
5. **Run benchmarks** and compare with baseline
6. **Git commit** results to separate branches/repos if needed

### Variant X Example (Redis-Optimized)

```bash
# Inside Variant X WSL instance
cd /home/syracuse/orange-315-forever

# Modify docker-compose.yml - increase Redis resources
# Edit services to add cache-aside pattern with batch prefetch
# Update environment variables if needed

# Rebuild and start
podman-compose build
podman-compose up -d

# Run benchmarks
./benchmark_orders.sh
```

## Cleanup and Management

### Stop All Services in Instance

```bash
podman-compose down
```

### Remove WSL Instance

```bash
# From Windows PowerShell
wsl --terminate orange-315-variant-x
wsl --unregister orange-315-variant-x
```

### Backup Instance

```bash
# Export current state
wsl --export orange-315-variant-x C:\wsl-backups\variant-x-$(date +%Y%m%d).tar
```

## Troubleshooting

### Instance Won't Start

```bash
# From PowerShell
wsl --terminate orange-315-variant-x
wsl --shutdown
wsl -d orange-315-variant-x
```

### Port Conflicts

Check that only one variant is running at a time if accessing from Windows host:

```bash
# From PowerShell
wsl --list --running
```

### Network Issues

Restart Podman network in WSL instance:

```bash
podman network rm podman
podman network create --subnet 10.88.0.0/16 podman
podman-compose up -d
```

## Best Practices

1. **One variant per WSL instance** - Don't try to run multiple variants in same instance
2. **Document changes** - Update README.md in each variant to explain differences
3. **Consistent naming** - Use `orange-315-{variant-name}` for WSL instances
4. **Git branching** - Consider separate git branches or repos per variant
5. **Backup before benchmarks** - Export WSL instance before major benchmark runs
6. **Resource monitoring** - Use `podman stats` to monitor resource usage
7. **Clean state** - `podman-compose down && podman system prune -af` between major changes

## Performance Considerations

- Each WSL instance runs independently
- CPU cores are shared across all instances (configure .wslconfig to limit)
- Running benchmarks on multiple instances simultaneously will affect results
- Run benchmarks sequentially for fair comparison

## Example: Comparing Three Variants

```bash
# Setup
wsl --export orange-315-baseline C:\wsl-exports\baseline.tar
wsl --import orange-315-variant-x C:\wsl-distros\variant-x C:\wsl-exports\baseline.tar
wsl --import orange-315-variant-z C:\wsl-distros\variant-z C:\wsl-exports\baseline.tar

# Configure each variant
wsl -d orange-315-variant-x
# ... modify for variant X ...

wsl -d orange-315-variant-z
# ... modify for variant Z ...

# Run benchmarks sequentially
wsl -d orange-315-baseline -e bash -c "cd ~/orange-315-forever && ./benchmark_orders.sh"
wsl -d orange-315-variant-x -e bash -c "cd ~/orange-315-forever && ./benchmark_orders.sh"
wsl -d orange-315-variant-z -e bash -c "cd ~/orange-315-forever && ./benchmark_orders.sh"

# Compare results
# Results are written to /tmp/variant-*.txt in each instance
```
