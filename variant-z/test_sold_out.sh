#!/bin/bash

# Consume all remaining tokens (9978 tokens)
echo "Starting to consume 9978 tokens..."
for i in {1..9978}; do
  curl -s -X POST http://localhost:30017/api/v1/orders/ \
    -H 'Content-Type: application/json' \
    -d "{\"customer_name\":\"Customer $i\",\"customer_email\":\"customer$i@test.com\",\"line_items\":[{\"sku_id\":\"2c2e23fa-f47b-4884-9b45-bf2a640f1ff3\",\"quantity\":1}]}" > /dev/null
  
  if [ $((i % 1000)) -eq 0 ]; then
    echo "Created $i orders..."
  fi
done

echo ""
echo "All tokens consumed. Testing sold out scenario..."
echo "------------------------------------------------"
curl -X POST http://localhost:30017/api/v1/orders/ \
  -H 'Content-Type: application/json' \
  -d '{"customer_name":"Last Customer","customer_email":"last@test.com","line_items":[{"sku_id":"2c2e23fa-f47b-4884-9b45-bf2a640f1ff3","quantity":1}]}'
echo ""
echo "------------------------------------------------"