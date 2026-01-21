#!/bin/bash
# Initialize database and Redis for Variant V

set -e

echo "=== Setting up Variant V Infrastructure ==="

# 1. Run migrations
echo "Running database migrations..."
docker-compose exec -T mariadb mysql -uroot -proot orange315 < migrations/001_add_audit_log.sql

# 2. Pre-allocate test campaign across 3 Redis nodes
echo "Setting up test campaign in Redis nodes..."
cd python-service

# Install dependencies if needed
pip install -r requirements.txt

# Create setup script
python3 - << 'PYTHON_SCRIPT'
import redis
import uuid
import sys

# Redis node URLs
nodes = [
    redis.Redis(host='10.92.0.3', port=6379),
    redis.Redis(host='10.92.0.4', port=6379),
    redis.Redis(host='10.92.0.5', port=6379)
]

# Verify all nodes are accessible
for i, node in enumerate(nodes):
    try:
        node.ping()
        print(f"Redis node {i+1}: Connected")
    except Exception as e:
        print(f"Redis node {i+1}: Failed - {e}")
        sys.exit(1)

# Create test campaign
campaign_id = str(uuid.uuid4())
total_limit = 1000
sku_ids = [
    "6a3c2f1b-9d4e-4f8a-bc7d-1234567890ab",
    "7b4d3g2c-0e5f-5g9b-cd8e-2345678901bc", 
    "8c5e4h3d-1f6g-6hac-de9f-3456789012cd",
    "9d6f5i4e-2g7h-7ibd-efag-4567890123de",
    "0e7g6j5f-3h8i-8jce-fgbh-5678901234ef",
    "1f8h7k6g-4i9j-9kdf-ghci-6789012345fg"
]

# Distribute limit across SKUs evenly
limit_per_sku = total_limit // len(sku_ids)

# Store campaign in MariaDB (would need DB connection)
# For now, just set in Redis counters
for i, sku_id in enumerate(sku_ids):
    node_idx = i % len(nodes)
    current = int(nodes[node_idx].get(f"campaign:{campaign_id}:sku:{sku_id}:remaining") or 0)
    nodes[node_idx].set(f"campaign:{campaign_id}:sku:{sku_id}:remaining", limit_per_sku)
    print(f"Allocated {limit_per_sku} units for SKU {sku_id} on Redis node {node_idx+1}")

nodes[0].set(f"campaign:{campaign_id}:total_limit", total_limit)
nodes[0].set(f"campaign:{campaign_id}:total_sold", 0)

print(f"Test campaign {campaign_id} setup complete")
PYTHON_SCRIPT

cd ..

# 3. Start batch processor worker in background
echo "Starting batch processor worker..."
docker-compose exec python celery -A app.workers.batch_processor worker --loglevel=info --detach

echo "=== Infrastructure setup complete ==="
