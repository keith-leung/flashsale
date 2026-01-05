# Write-Back Testing Quick Start

## Prerequisites
```bash
cd /home/syracuse/flashsale/variant-x
docker compose up -d
```

## Quick Test: Manual Trigger (For Benchmarks)

This is the most common use case - manually ending a campaign after a benchmark completes.

### 1. Create a test campaign
```bash
# Create campaign via API or database
# (Use existing campaign creation endpoint)
```

### 2. Run some test orders
```bash
# Submit orders to the campaign
curl -X POST http://localhost:30011/api/v1/orders \
  -H "Content-Type: application/json" \
  -d '{
    "customer_email": "test@example.com",
    "customer_name": "Test User",
    "line_items": [{"sku_id": "...", "quantity": 1}]
  }'
```

### 3. Manually end the campaign (TRIGGER WRITE-BACK)
```bash
# Replace {campaign_id} with actual campaign ID
curl -X POST http://localhost:30011/api/v1/admin/campaigns/{campaign_id}/end
```

Expected output:
```json
{
  "status": 200,
  "message": "Campaign ... ended successfully, write-back in progress",
  "data": {
    "campaign_id": "...",
    "new_status": "ended",
    "action": "write_back_queued"
  }
}
```

### 4. Check write-back status
```bash
curl http://localhost:30011/api/v1/admin/campaigns/{campaign_id}/writeback-status
```

Expected output:
```json
{
  "status": 200,
  "data": {
    "status": "ended",
    "sold_quantity": 10,  # Should be > 0 after write-back
    "writeback_complete": true
  }
}
```

### 5. Verify in database
```bash
docker exec flash-mariadb-x mysql -uroot -proot orange315 -e \
  "SELECT COUNT(*) as order_count FROM orders WHERE flash_sale_campaign_id = '{campaign_id}'"
```

Expected:
- `order_count` matches number of orders submitted

## Quick Test: Sold-Out Trigger

### 1. Create campaign with small inventory
```bash
# Create campaign with total_sale_limit = 5
```

### 2. Submit orders until sold out
```bash
# Submit 5 orders (or quantity = 5 total)
# The last order that brings inventory to 0 will trigger write-back
```

### 3. Check logs
```bash
docker logs flash-python-x | grep "sold out"
```

Expected:
```
Campaign {id} just sold out, triggering write-back
```

## Quick Test: Scheduled Expiry

### 1. Create short campaign
```bash
# Create campaign with:
# - start_time: NOW()
# - end_time: NOW() + 2 minutes
```

### 2. Submit some orders
```bash
# Submit a few test orders
```

### 3. Wait for expiry
```bash
# Wait 2 minutes for end_time
# Wait up to 60 seconds for monitor task to detect it
```

### 4. Check logs
```bash
docker logs flash-python-x | tail -n 50
```

Expected:
```
Campaign {id} ({name}) expired at ..., triggering write-back
Write-back completed for campaign {id}: X orders
```

## Verify Background Task Running

```bash
docker logs flash-python-x | grep "Campaign monitor"
```

Expected:
```
Campaign monitor background task started
Campaign monitor task started
```

## Check Transaction Logs

```bash
# Inside container
docker exec flash-python-x ls -la /var/log/flashsale/
docker exec flash-python-x cat /var/log/flashsale/campaign_{id}_writeback.log
```

## Admin Endpoints Reference

```bash
# Manual end
POST http://localhost:30011/api/v1/admin/campaigns/{id}/end

# Check status
GET http://localhost:30011/api/v1/admin/campaigns/{id}/writeback-status

# Retry write-back (if failed)
POST http://localhost:30011/api/v1/admin/campaigns/{id}/writeback
```

## Troubleshooting

### No write-back happening?
```bash
# Check Python service logs
docker logs flash-python-x -f

# Check if monitor task started
docker logs flash-python-x | grep "monitor"

# Manually trigger
curl -X POST http://localhost:30011/api/v1/admin/campaigns/{id}/end
```

### Orders not in database?
```bash
# Check for errors in logs
docker logs flash-python-x | grep -i error

# Check failover logs
docker exec flash-python-x ls /var/log/flashsale/failover/

# Verify Redis stream has orders
docker exec flash-redis-x redis-cli XLEN order_queue
```

### Force retry write-back
```bash
# If write-back failed, retry
curl -X POST http://localhost:30011/api/v1/admin/campaigns/{id}/writeback
```
