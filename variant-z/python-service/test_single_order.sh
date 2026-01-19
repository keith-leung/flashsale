#!/bin/bash
curl -s -X POST "http://localhost:30017/api/v1/orders/" \
  -H "Content-Type: application/json" \
  -d '{"customer_name": "Test", "customer_email": "test@example.com", "line_items": [{"sku_id": "2c2e23fa-f47b-4884-9b45-bf2a640f1ff3", "quantity": 1}], "currency": "USD"}'