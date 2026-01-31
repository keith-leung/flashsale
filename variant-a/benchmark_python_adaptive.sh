#!/bin/bash

LOG_FILE="benchmark_results_python_adaptive.txt"
echo "Starting Python Adaptive Benchmark" > $LOG_FILE

# Ensure container is running
docker rm -f benchmark-python || true
docker run -d --rm --name benchmark-python \
  -e BENCHMARK_MODE=true \
  -p 8000:8000 \
  flash-sale-python-variant-a

# Allow startup
echo "Waiting for Python service to start..."
sleep 5

# Warmup
echo "Warming up..."
wrk -t2 -c10 -d5s http://127.0.0.1:8000/health > /dev/null
wrk -t2 -c10 -d5s http://127.0.0.1:8000/health2 > /dev/null

for c in 10 50 100 200 300 500; do
    echo "------------------------------------------------" | tee -a $LOG_FILE
    echo "Concurrency: $c" | tee -a $LOG_FILE
    
    echo "Testing /health (Baseline)..."
    echo "--- /health (c=$c) ---" >> $LOG_FILE
    wrk -t4 -c$c -d10s http://127.0.0.1:8000/health >> $LOG_FILE
    
    echo "Testing /health2 (Allocation)..."
    echo "--- /health2 (c=$c) ---" >> $LOG_FILE
    wrk -t4 -c$c -d10s http://127.0.0.1:8000/health2 >> $LOG_FILE
done

docker stop benchmark-python
echo "Python Benchmark Complete"