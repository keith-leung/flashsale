# Redis to MariaDB Write-Back Implementation

## Overview
Event-based write-back system for variant X that persists flash sale data from Redis to MariaDB when campaigns end.

## Implementation Summary

### Files Created

1. **app/services/campaign_writeback.py** (Core Logic)
   - `writeback_campaign()` - Main write-back orchestration
   - `read_campaign_orders()` - Read orders from Redis Stream
   - `generate_failover_log()` - Create customer notification logs on failure
   - Transaction logging and Redis cleanup

2. **app/api/endpoints/campaign_admin.py** (Admin Endpoints)
   - `POST /api/v1/admin/campaigns/{id}/end` - Manual campaign end
   - `GET /api/v1/admin/campaigns/{id}/writeback-status` - Check write-back status
   - `POST /api/v1/admin/campaigns/{id}/writeback` - Manual retry

3. **app/tasks/campaign_monitor.py** (Background Task)
   - Runs every 60 seconds
   - Auto-triggers write-back when campaigns expire
   - Monitors campaigns where end_time <= NOW()

### Files Modified

1. **app/api/endpoints/orders.py**
   - Added sold-out detection after inventory reservation
   - Triggers async write-back when campaign_remaining == 0
   - Added BackgroundTasks dependency

2. **app/main.py**
   - Starts campaign_monitor_task on startup
   - Graceful shutdown handling for background task

3. **app/api/router.py**
   - Registered campaign_admin routes at /api/v1/admin

## Write-Back Triggers

The system triggers write-back on 3 events:

### 1. Scheduled Expiry (Time-Based)
- **Trigger**: Campaign end_time reached
- **How**: Background task checks every 60 seconds
- **Reason Code**: `scheduled_expiry`

### 2. Sold Out (Inventory Zero)
- **Trigger**: Campaign inventory hits 0
- **How**: Detected in orders.py after successful reservation
- **Reason Code**: `sold_out`

### 3. Manual End (Admin Action)
- **Trigger**: Admin calls endpoint
- **How**: `POST /api/v1/admin/campaigns/{id}/end`
- **Reason Code**: `manual`

## Write-Back Process

When triggered, the system:

1. **Reads orders from Redis Stream** (`order_queue`)
   - Filters by campaign_id
   - Parses all order data and line items

2. **Batch writes to MariaDB** (single transaction)
   - Inserts orders to `orders` table
   - Inserts line items to `order_line_items` table
   - Updates `flash_sale_campaigns.sold_quantity`
   - Idempotent (skips duplicates)

3. **Writes transaction log**
   - Location: `/var/log/flashsale/campaign_{id}_writeback.log`
   - Contains: campaign info, order count, timestamp

4. **Cleans up Redis keys**
   - Deletes: `fs:{campaign_id}:meta`
   - Deletes: `fs:{campaign_id}:limit`
   - Keeps: `order_queue` stream (for audit)

## Failover Logging

If write-back fails (Redis down, DB error), generates:

**Location**: `/var/log/flashsale/failover/campaign_{id}_pending.txt`

**Format**:
```
CAMPAIGN: Campaign Name (campaign-id)
FAILURE TIME: 2026-01-03 14:30:22 UTC
REASON: Exception details

PENDING ORDERS (may not have completed):
order_number,customer_email,customer_name,quantity,timestamp
ORD-123456,user@example.com,John Doe,2,2026-01-03 14:25:10

CUSTOMER NOTICE TEMPLATE:
"Dear {customer_name}, your order {order_number} for the flash sale
could not be completed due to system maintenance..."
```

This allows operators to contact customers and notify them.

## Testing Guide

### 1. Test Manual Trigger (Benchmark Use Case)

```bash
# Create a flash sale campaign
# Run benchmark orders
# Manually end the campaign

curl -X POST http://localhost:30011/api/v1/admin/campaigns/{campaign_id}/end

# Check write-back status
curl http://localhost:30011/api/v1/admin/campaigns/{campaign_id}/writeback-status
```

Expected:
- Campaign status changes to "ended"
- Orders written to MariaDB
- `sold_quantity` updated

### 2. Test Sold-Out Trigger

```bash
# Create campaign with small inventory (e.g., 10 units)
# Submit orders until inventory = 0
# Last order should trigger write-back automatically
```

Expected:
- Write-back triggered when inventory hits 0
- Log message: "Campaign {id} just sold out, triggering write-back"
- Orders persisted to database

### 3. Test Scheduled Expiry

```bash
# Create campaign with short duration (e.g., 2 minutes)
# Submit some orders
# Wait for end_time to pass
# Wait up to 60 seconds for monitor task
```

Expected:
- Monitor task detects expired campaign
- Write-back triggered with reason "scheduled_expiry"
- Campaign status updated to "ended"

### 4. Verify Database

```sql
-- Check orders were written
SELECT COUNT(*) FROM orders WHERE flash_sale_campaign_id = '{campaign_id}';

-- Check sold_quantity updated
SELECT sold_quantity, total_sale_limit
FROM flash_sale_campaigns
WHERE id = '{campaign_id}';

-- Check order details
SELECT o.order_number, o.customer_email, oli.quantity, oli.unit_price
FROM orders o
JOIN order_line_items oli ON oli.order_id = o.id
WHERE o.flash_sale_campaign_id = '{campaign_id}';
```

### 5. Test Failover Logging

```bash
# Stop MariaDB container during campaign
docker stop flash-mariadb-x

# Trigger write-back
curl -X POST http://localhost:30011/api/v1/admin/campaigns/{campaign_id}/end

# Check failover log created
cat /var/log/flashsale/failover/campaign_{campaign_id}_pending.txt
```

Expected:
- Failover log generated with customer details
- Operators can use this to notify customers

## Integration with Existing Code

### No Impact on Performance
- Write-back happens **asynchronously** (BackgroundTasks)
- Order acceptance continues at Redis speed (5,000+ req/s)
- Write-back doesn't block order processing

### Redis Data Flow

```
Order Request
    ↓
Reserve inventory in Redis (DECRBY)
    ↓
Queue order to Redis Stream (XADD order_queue)
    ↓
Return success to customer immediately
    ↓
[Later] Write-back triggered
    ↓
Read orders from stream (XREAD)
    ↓
Batch insert to MariaDB
```

## Logs and Monitoring

### Application Logs
- Campaign monitor: "Campaign monitor task started"
- Sold out detection: "Campaign {id} just sold out"
- Write-back start: "Starting write-back for campaign {id}"
- Write-back complete: "Write-back completed: {count} orders"

### Transaction Logs
- Success: `/var/log/flashsale/campaign_{id}_writeback.log`
- Failure: `/var/log/flashsale/failover/campaign_{id}_pending.txt`

### Health Check
Monitor background task status:
```bash
# Check if campaign monitor is running
docker logs flash-python-x | grep "Campaign monitor"
```

## API Endpoints

### Manual Campaign End
```
POST /api/v1/admin/campaigns/{campaign_id}/end
```

Response:
```json
{
  "status": 200,
  "message": "Campaign {name} ended successfully, write-back in progress",
  "data": {
    "campaign_id": "...",
    "campaign_name": "...",
    "previous_status": "active",
    "new_status": "ended",
    "action": "write_back_queued"
  }
}
```

### Check Write-Back Status
```
GET /api/v1/admin/campaigns/{campaign_id}/writeback-status
```

Response:
```json
{
  "status": 200,
  "data": {
    "campaign_id": "...",
    "status": "ended",
    "sold_quantity": 1000,
    "total_sale_limit": 1000,
    "writeback_complete": true
  }
}
```

### Manual Write-Back Retry
```
POST /api/v1/admin/campaigns/{campaign_id}/writeback
```

Use case: Retry if write-back failed due to temporary DB issue.

## Architecture Benefits

1. **Simple**: No continuous stream processing
2. **Low Overhead**: Write-back only at campaign end
3. **Failover Ready**: Transaction logs for customer notifications
4. **Zero Performance Impact**: Async write-back doesn't block orders
5. **Benchmark Friendly**: Manual trigger for benchmarks that don't run out inventory/time

## Production Readiness

✅ Idempotent (handles duplicate orders)
✅ Error handling (failover logs)
✅ Background task monitoring
✅ Transaction logging
✅ Graceful shutdown
✅ Admin endpoints for manual control

## Next Steps for Production

1. **Deploy**: Rebuild and restart Python service
2. **Monitor**: Watch logs for campaign monitor task
3. **Test**: Run end-to-end test with small campaign
4. **Verify**: Check MariaDB for persisted orders
5. **Alert**: Set up alerts for failover log creation

## Troubleshooting

### Write-Back Not Triggering
- Check: Is campaign_monitor_task running?
- Check: Campaign status = "active"?
- Check: Are there orders in Redis Stream?

### Orders Not in Database
- Check: Write-back completed? (check logs)
- Check: Failover log created? (database error?)
- Retry: Call manual writeback endpoint

### Failover Log Generated
- Check: MariaDB connection
- Check: Redis connection
- Review: Error details in failover log
- Action: Notify customers using template

## Files Summary

```
variant-x/python-service/
├── app/
│   ├── services/
│   │   ├── __init__.py
│   │   └── campaign_writeback.py          [NEW]
│   ├── api/
│   │   ├── router.py                      [MODIFIED]
│   │   └── endpoints/
│   │       ├── campaign_admin.py          [NEW]
│   │       └── orders.py                  [MODIFIED]
│   ├── tasks/
│   │   ├── __init__.py                    [NEW]
│   │   └── campaign_monitor.py            [NEW]
│   ├── main.py                            [MODIFIED]
│   └── core/
│       └── redis_cache.py                 [EXISTING - has get_campaign_meta]
└── logs/
    └── .gitkeep                           [NEW]
```
