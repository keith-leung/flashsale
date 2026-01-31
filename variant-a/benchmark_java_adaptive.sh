#!/bin/bash

LOG_FILE="benchmark_results_java_adaptive.txt"
echo "Starting Java Adaptive Benchmark" > $LOG_FILE

# Ensure container is running
docker rm -f benchmark-java || true
docker run -d --rm --name benchmark-java \
  -e BENCHMARK_MODE=true \
  -e SPRING_REDIS_HOST=localhost \
  -e SPRING_DATASOURCE_URL=jdbc:mysql://localhost:3306/flashsale \
  -p 8081:8080 \
  flash-sale-java-variant-a \
  java -jar target/flashsale-api-0.0.1-SNAPSHOT.jar

# Allow startup
echo "Waiting for Java service to start..."
sleep 15

# Warmup
echo "Warming up..."
wrk -t2 -c10 -d5s http://127.0.0.1:8081/health > /dev/null
wrk -t2 -c10 -d5s http://127.0.0.1:8081/health2 > /dev/null

for c in 10 50 100 200 300 500; do
    echo "------------------------------------------------" | tee -a $LOG_FILE
    echo "Concurrency: $c" | tee -a $LOG_FILE
    
    echo "Testing /health (Baseline)..."
    echo "--- /health (c=$c) ---" >> $LOG_FILE
    wrk -t4 -c$c -d10s http://127.0.0.1:8081/health >> $LOG_FILE
    
    echo "Testing /health2 (Allocation)..."
    echo "--- /health2 (c=$c) ---" >> $LOG_FILE
    wrk -t4 -c$c -d10s http://127.0.0.1:8081/health2 >> $LOG_FILE
done

docker stop benchmark-java
echo "Java Benchmark Complete"
