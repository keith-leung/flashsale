#!/bin/bash

echo "=== Variant Z Python Service - Final Test ==="
echo ""

# Test 1: Health check
echo "Test 1: Health Check"
curl -s http://localhost:30017/health | python3 -m json.tool
echo ""

# Test 2: Create a few more orders
echo "Test 2: Create 5 more orders"
for i in {1..5}; do
  echo "Order $i:"
  curl -s -X POST http://localhost:30017/api/v1/orders/ \
    -H 'Content-Type: application/json' \
    -d "{\"customer_name\":\"Test $i\",\"customer_email\":\"test$i@example.com\",\"line_items\":[{\"sku_id\":\"2c2e23fa-f47b-4884-9b45-bf2a640f1ff3\",\"quantity\":1}]}" | python3 -m json.tool | grep -E '"order_id"|"status"'
done
echo ""

# Test 3: Check token count
echo "Test 3: Remaining token count"
docker exec flash-redis-z redis-cli ZCARD campaign:e26bb7d0-c863-4cd6-b08c-44fcca0a8c28:tokens
echo ""

# Test 4: Check order count
echo "Test 4: Total orders in database"
docker exec flash-mariadb-z mysql -u syracuse -p'Orange_315_Forever!' orange315 -e 'SELECT COUNT(*) as total_orders FROM orders;' 2>/dev/null
echo ""

# Test 5: Test invalid SKU
echo "Test 5: Invalid SKU error handling"
curl -s -X POST http://localhost:30017/api/v1/orders/ \
  -H 'Content-Type: application/json' \
  -d '{"customer_name":"Test","customer_email":"test@example.com","line_items":[{"sku_id":"invalid-sku","quantity":1}]}' | python3 -m json.tool
echo ""

echo "=== All Tests Complete ==="