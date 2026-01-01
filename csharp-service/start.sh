#!/bin/sh
# Dynamic start script
# DB_HOST is passed from environment at runtime
TARGET_HOST=${DB_HOST:-flash-mariadb}
echo "Waiting for database at ${TARGET_HOST}:3306..."

# Loop until NC success
while ! nc -z ${TARGET_HOST} 3306; do
  echo "Database not ready yet..."
  sleep 1
done

echo "Database is ready!"
exec dotnet FlashSale.Api.dll
