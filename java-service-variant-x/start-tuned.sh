#!/bin/bash
cd /home/syracuse/orange-315-forever/java-service-variant-x

# Start Java service with performance tuning
java -Xms4G -Xmx4G \
     -XX:+UseG1GC \
     -XX:MaxGCPauseMillis=50 \
     -XX:G1HeapRegionSize=16M \
     -XX:+ParallelRefProcEnabled \
     -XX:+UseStringDeduplication \
     -XX:+OptimizeStringConcat \
     -server \
     -jar target/flashsale-api-0.0.1-SNAPSHOT.jar
