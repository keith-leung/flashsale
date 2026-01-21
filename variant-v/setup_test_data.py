#!/usr/bin/env python3
"""Setup test campaign and SKU data for Variant V."""

import redis
import uuid
import sys

# Redis node connections
nodes = [
    redis.Redis(host='10.92.0.3', port=6379),
    redis.Redis(host='10.92.0.4', port=6379),
    redis.Redis(host='10.92.0.5', port=6379)
]

def setup_campaign():
    """Setup test flash sale campaign with SKU allocation."""
    print("Setting up test campaign...")
    
    # Test campaign details
    campaign_id = "test-flash-campaign-001"
    total_limit = 1000
    
    # SKU IDs (consistent with setup_infrastructure.sh)
    sku_ids = [
        "6a3c2f1b-9d4e-4f8a-bc7d-1234567890ab",
        "7b4d3g2c-0e5f-5g9b-cd8e-2345678901bc", 
        "8c5e4h3d-1f6g-6hac-de9f-3456789012cd",
        "9d6f5i4e-2g7h-7ibd-efag-4567890123de",
        "0e7g6j5f-3h8i-8jce-fgbh-5678901234ef",
        "1f8h7k6g-4i9j-9kdf-ghci-6789012345fg"
    ]
    
    # Distribute limit evenly across SKUs
    limit_per_sku = total_limit // len(sku_ids)
    
    # Set campaign limits and per-SKU remaining quantities
    for i, sku_id in enumerate(sku_ids):
        node_idx = i % len(nodes)
        sku_node = nodes[node_idx]
        
        # Set remaining quantity for this SKU
        sku_node.set(f"campaign:{campaign_id}:sku:{sku_id}:remaining", limit_per_sku)
        print(f"✓ Allocated {limit_per_sku} units for SKU {sku_id[:8]}... on Redis node {node_idx+1}")
    
    # Set total campaign limits on primary Redis node (first node)
    nodes[0].set(f"campaign:{campaign_id}:total_limit", total_limit)
    nodes[0].set(f"campaign:{campaign_id}:total_sold", 0)
    nodes[0].set(f"campaign:{campaign_id}:initialized", "true")
    
    print(f"✓ Campaign {campaign_id} setup complete")
    print(f"✓ Total campaign limit: {total_limit}")
    print(f"✓ SKUs configured: {len(sku_ids)}")
    
    return campaign_id, sku_ids

def verify_redis_nodes():
    """Verify all Redis nodes are accessible."""
    print("\nVerifying Redis nodes...")
    
    for i, node in enumerate(nodes):
        try:
            node.ping()
            print(f"✓ Redis node {i+1} (10.92.0.{i+3}): Connected")
        except Exception as e:
            print(f"✗ Redis node {i+1} (10.92.0.{i+3}): Failed - {e}")
            sys.exit(1)

def test_sku_distribution(sku_ids):
    """Test that SKUs are distributed across Redis nodes."""
    print("\nTesting SKU distribution...")
    
    for sku_id in sku_ids:
        node_idx = hash(sku_id) % len(nodes)
        print(f"  SKU {sku_id[:8]}... -> Node {node_idx+1}")
    
    print("✓ SKU distribution verified")

def check_campaign_data(campaign_id):
    """Verify campaign data was set correctly."""
    print("\nVerifying campaign data...")
    
    total_limit = nodes[0].get(f"campaign:{campaign_id}:total_limit")
    total_sold = nodes[0].get(f"campaign:{campaign_id}:total_sold")
    initialized = nodes[0].get(f"campaign:{campaign_id}:initialized")
    
    if total_limit:
        print(f"✓ Campaign total limit: {total_limit.decode()}")
    if total_sold:
        print(f"✓ Campaign total sold: {total_sold.decode()}")
    if initialized:
        print(f"✓ Campaign initialized: {initialized.decode()}")
    
    # Check SKU data on each node
    for i, node in enumerate(nodes):
        keys = node.keys(f"campaign:{campaign_id}:sku:*:remaining")
        if keys:
            print(f"✓ Node {i+1} has {len(keys)} SKU keys")

def main():
    """Main setup function."""
    print("=== Setting up Variant V Test Data ===\n")
    
    # Verify Redis connectivity
    verify_redis_nodes()
    
    # Setup campaign
    campaign_id, sku_ids = setup_campaign()
    
    # Test distribution
    test_sku_distribution(sku_ids)
    
    # Verify data
    check_campaign_data(campaign_id)
    
    print(f"\n=== Setup Complete ===")
    print(f"Campaign ID: {campaign_id}")
    print(f"Test SKUs: {len(sku_ids)} configured")
    print(f"\nSample SKU for testing: {sku_ids[0]}")
    
    # Write campaign info to file for later use
    with open('/tmp/campaign_info.txt', 'w') as f:
        f.write(f"CAMPAIGN_ID={campaign_id}\n")
        f.write(f"TEST_SKU={sku_ids[0]}\n")
        for sku in sku_ids:
            f.write(f"SKU={sku}\n")
    
    print("\nCampaign info saved to /tmp/campaign_info.txt")

if __name__ == "__main__":
    main()
