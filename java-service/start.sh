#!/bin/sh
# Java start script
TARGET_HOST=${DB_HOST:-flash-mariadb}
echo "Waiting for database at ${TARGET_HOST}:3306..."

while ! nc -z ${TARGET_HOST} 3306; do
  echo "Database not ready yet..."
  sleep 1
done

echo "Database is ready!"
exec java -jar target/flashsale-api-0.0.1-SNAPSHOT.jar
