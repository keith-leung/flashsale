package com.flashsale.api.service;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.time.Instant;

/**
 * Twitter Snowflake ID Generator for distributed systems.
 * 
 * 64-bit structure:
 * ┌─┬─────────────────────────────────────────────┬──────────────┬──────────────────┐
 * │0│              Timestamp (41 bits)             │ Machine (10) │ Sequence (12)    │
 * └─┴─────────────────────────────────────────────┴──────────────┴──────────────────┘
 * 
 * Capacity: 4,096 IDs per millisecond per machine = 4,096,000 IDs/second per service
 */
@Component
public class SnowflakeIdGenerator {
    
    // Custom epoch (January 1, 2024 00:00:00 UTC)
    private static final long EPOCH = 1704067200000L;
    
    // Bit lengths
    private static final int SEQUENCE_BITS = 12;      // 4,096 sequences per millisecond
    private static final int MACHINE_ID_BITS = 10;    // 1,024 different machines
    private static final int TIMESTAMP_BITS = 41;     // ~69 years of milliseconds
    
    // Bit shifts
    private static final int MACHINE_ID_SHIFT = SEQUENCE_BITS;                    // 12
    private static final int TIMESTAMP_SHIFT = SEQUENCE_BITS + MACHINE_ID_BITS;   // 22
    
    // Masks
    private static final long SEQUENCE_MASK = (1L << SEQUENCE_BITS) - 1;          // 4095
    private static final long MACHINE_ID_MASK = (1L << MACHINE_ID_BITS) - 1;      // 1023
    
    private final long machineId;
    private long sequence = 0L;
    private long lastTimestamp = 0L;
    private final Object lock = new Object();
    
    /**
     * Initialize Snowflake generator for Java services.
     * Uses PID-based machine_id for multi-worker deployments.
     *
     * @param instanceId Java service instance ID (1-341, offset to 683-1023 range)
     */
    public SnowflakeIdGenerator(@Value("${app.instance-id:1}") int instanceId) {
        if (instanceId < 1 || instanceId > 341) {
            throw new IllegalArgumentException("Java service instance ID must be between 1 and 341");
        }

        // For multi-worker deployments, use PID to ensure each worker has unique machine_id
        long pid = ProcessHandle.current().pid();
        this.machineId = (instanceId * 100 + pid) % 1024;

        if (machineId < 0 || machineId > MACHINE_ID_MASK) {
            throw new IllegalArgumentException(
                String.format("Machine ID must be between 0 and %d", MACHINE_ID_MASK));
        }
    }
    
    /**
     * Generate next Snowflake ID.
     * 
     * @return 64-bit Snowflake ID
     * @throws RuntimeException if clock moves backwards
     */
    public long generate() {
        synchronized (lock) {
            long timestamp = getTimestamp();
            
            // Clock moved backwards - this should never happen in production
            if (timestamp < lastTimestamp) {
                throw new RuntimeException(
                    String.format("Clock moved backwards. Refusing to generate ID for %d milliseconds",
                        lastTimestamp - timestamp));
            }
            
            // Same millisecond - increment sequence
            if (timestamp == lastTimestamp) {
                sequence = (sequence + 1) & SEQUENCE_MASK;
                
                // Sequence overflow - wait for next millisecond
                if (sequence == 0) {
                    timestamp = waitForNextMillis(timestamp);
                }
            } else {
                // New millisecond - reset sequence
                sequence = 0L;
            }
            
            lastTimestamp = timestamp;
            
            // Combine all parts into 64-bit ID
            return ((timestamp - EPOCH) << TIMESTAMP_SHIFT) |
                   (machineId << MACHINE_ID_SHIFT) |
                   sequence;
        }
    }
    
    /**
     * Parse Snowflake ID into components.
     * 
     * @param snowflakeId 64-bit Snowflake ID
     * @return Parsed components
     */
    public SnowflakeComponents parse(long snowflakeId) {
        long timestamp = ((snowflakeId >> TIMESTAMP_SHIFT) + EPOCH);
        long machineId = (snowflakeId >> MACHINE_ID_SHIFT) & MACHINE_ID_MASK;
        long sequence = snowflakeId & SEQUENCE_MASK;
        
        return SnowflakeComponents.builder()
            .id(snowflakeId)
            .timestamp(timestamp)
            .machineId(machineId)
            .sequence(sequence)
            .dateTime(Instant.ofEpochMilli(timestamp))
            .build();
    }
    
    private long getTimestamp() {
        return System.currentTimeMillis();
    }
    
    private long waitForNextMillis(long lastTimestamp) {
        long timestamp = getTimestamp();
        while (timestamp <= lastTimestamp) {
            timestamp = getTimestamp();
        }
        return timestamp;
    }
    
    /**
     * Snowflake ID components for parsing results.
     */
    public static class SnowflakeComponents {
        private long id;
        private long timestamp;
        private long machineId;
        private long sequence;
        private Instant dateTime;
        
        public static Builder builder() {
            return new Builder();
        }
        
        public static class Builder {
            private SnowflakeComponents components = new SnowflakeComponents();
            
            public Builder id(long id) {
                components.id = id;
                return this;
            }
            
            public Builder timestamp(long timestamp) {
                components.timestamp = timestamp;
                return this;
            }
            
            public Builder machineId(long machineId) {
                components.machineId = machineId;
                return this;
            }
            
            public Builder sequence(long sequence) {
                components.sequence = sequence;
                return this;
            }
            
            public Builder dateTime(Instant dateTime) {
                components.dateTime = dateTime;
                return this;
            }
            
            public SnowflakeComponents build() {
                return components;
            }
        }
        
        // Getters
        public long getId() { return id; }
        public long getTimestamp() { return timestamp; }
        public long getMachineId() { return machineId; }
        public long getSequence() { return sequence; }
        public Instant getDateTime() { return dateTime; }
    }
}
