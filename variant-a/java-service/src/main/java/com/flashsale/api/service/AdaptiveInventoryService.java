package com.flashsale.api.service;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.data.redis.core.script.DefaultRedisScript;

import java.util.Collections;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicLong;
import java.util.concurrent.atomic.AtomicReference;

/**
 * Adaptive Inventory Service for Flash Sale Variant A
 *
 * Uses a 2-tier adaptive strategy:
 * - BATCH MODE: Local cache with ReentrantLock (500 items)
 * - DIRECT MODE: Direct Redis calls when stock < LOW_WATER_MARK
 *
 * Network I/O Reduction: 99.6%+ (500 requests = 1 Redis call in batch mode)
 */
public class AdaptiveInventoryService {

    private static final Logger logger = LoggerFactory.getLogger(AdaptiveInventoryService.class);

    // Configuration constants
    public static final int BATCH_SIZE = 500;
    public static final int LOW_WATER_MARK = 2000;

    private final String campaignId;
    private final String skuId;
    private final RedisTemplate<String, Object> redisTemplate;
    private final DefaultRedisScript<Long> luaScript;

    // Redis key for this SKU's inventory
    private final String inventoryKey;

    // L1 Cache (Local Memory)
    private final AtomicLong localStock = new AtomicLong(0);

    // Mode control
    private final AtomicBoolean directMode = new AtomicBoolean(false);
    private final AtomicBoolean modeSwitched = new AtomicBoolean(false);

    // Single-flight refill protection (async)
    private final AtomicReference<CompletableFuture<Boolean>> refillFuture = new AtomicReference<>(null);

    // Metrics
    private final AtomicLong batchModeRequests = new AtomicLong(0);
    private final AtomicLong directModeRequests = new AtomicLong(0);
    private final AtomicLong totalRedisCalls = new AtomicLong(0);

    public AdaptiveInventoryService(
            String campaignId,
            String skuId,
            RedisTemplate<String, Object> redisTemplate,
            DefaultRedisScript<Long> luaScript) {
        this.campaignId = campaignId;
        this.skuId = skuId;
        this.redisTemplate = redisTemplate;
        this.luaScript = luaScript;
        this.inventoryKey = String.format("fs:%s:sku:%s:limit", campaignId, skuId);
    }

    /**
     * Attempt to reserve one item from inventory
     *
     * Hot Path Flow:
     * 1. Try local cache (pure memory, no network)
     * 2. If cache empty, trigger async refill and spin-wait
     * 3. If directMode, bypass cache and hit Redis
     *
     * @return true if reservation successful, false if sold out
     */
    public boolean reserveItem() {
        // Fast path: Try local cache first (BATCH MODE)
        if (!directMode.get()) {
            long current = localStock.get();
            if (current > 0) {
                // Try atomic decrement
                if (localStock.compareAndSet(current, current - 1)) {
                    batchModeRequests.incrementAndGet();
                    return true;  // ← Network I/O saved here! Pure RAM operation
                }
                // CAS failed, retry (another thread decremented)
                return reserveItem();
            }

            // Stock is 0 - spin wait for refill (critical for 100K+ req/s)
            // A refill might be 5-10ms away, avoid false "sold out"
            long spinStart = System.nanoTime();
            long spinDeadline = spinStart + 10_000_000; // 10ms max spin

            while (System.nanoTime() < spinDeadline) {
                Thread.onSpinWait(); // Hint to CPU we're spinning

                current = localStock.get();
                if (current > 0) {
                    if (localStock.compareAndSet(current, current - 1)) {
                        batchModeRequests.incrementAndGet();
                        return true;  // Caught the refill!
                    }
                }

                // Check if we should give up (refill failed)
                if (refillFuture.get() == null && localStock.get() == 0) {
                    break; // No refill in progress and still 0
                }
            }
        }

        // Slow path: Trigger refill or direct Redis
        return refillOrDirect();
    }

    /**
     * Refill local cache from Redis or switch to direct mode
     * Uses single-flight async pattern to prevent stampede
     */
    private boolean refillOrDirect() {
        // Try to claim the refill slot (single-flight)
        CompletableFuture<Boolean> existingRefill = refillFuture.get();

        if (existingRefill != null) {
            // Another thread is refilling, wait for it
            try {
                return existingRefill.join(); // Block waiting for refill result
            } catch (Exception e) {
                logger.error("Refill future failed", e);
                return false;
            }
        }

        // We're the first - create the refill future
        CompletableFuture<Boolean> myRefill = new CompletableFuture<>();

        if (!refillFuture.compareAndSet(null, myRefill)) {
            // Lost the race, another thread claimed it
            existingRefill = refillFuture.get();
            if (existingRefill != null) {
                try {
                    return existingRefill.join();
                } catch (Exception e) {
                    logger.error("Refill future failed", e);
                    return false;
                }
            }
        }

        // We won the race - perform the refill
        try {
            // Double-check stock before refilling
            if (!directMode.get()) {
                long current = localStock.get();
                if (current > 0) {
                    if (localStock.compareAndSet(current, current - 1)) {
                        batchModeRequests.incrementAndGet();
                        myRefill.complete(true);
                        return true;
                    }
                }
            }

            boolean result;
            if (directMode.get()) {
                result = tryDirectRedis();
            } else {
                result = tryRefillBatch();
            }

            myRefill.complete(result);
            return result;
        } catch (Exception e) {
            myRefill.completeExceptionally(e);
            throw e;
        } finally {
            // Clear the refill future so next request can trigger a new one
            refillFuture.compareAndSet(myRefill, null);
        }
    }

    /**
     * Try to refill local cache from Redis using Lua script
     */
    private boolean tryRefillBatch() {
        totalRedisCalls.incrementAndGet();

        // Execute Lua script
        // KEYS[1] = inventory key
        // ARGV[1] = batch size
        // ARGV[2] = low water mark
        Long result = redisTemplate.execute(
            luaScript,
            Collections.singletonList(inventoryKey),
            String.valueOf(BATCH_SIZE),
            String.valueOf(LOW_WATER_MARK)
        );

        if (result == null) {
            logger.error("Lua script returned null for SKU: {}", skuId);
            return false;
        }

        long granted = result;

        if (granted == -1) {
            // Sold out
            logger.debug("SKU {} sold out", skuId);
            return false;
        } else if (granted == -2) {
            // Switch to direct mode
            if (modeSwitched.compareAndSet(false, true)) {
                logger.info("[MODE SWITCH] SKU {}: Stock below {} - switching to DIRECT mode to prevent fragmentation",
                    skuId, LOW_WATER_MARK);
            }
            directMode.set(true);
            return tryDirectRedis();
        } else {
            // Granted batch
            localStock.set(granted);
            if (localStock.get() > 0) {
                localStock.decrementAndGet();
                batchModeRequests.incrementAndGet();
                return true;
            }
            return false;
        }
    }

    /**
     * Direct Redis mode - hit Redis for every request
     * Used when stock < LOW_WATER_MARK to prevent fragmentation
     */
    private boolean tryDirectRedis() {
        totalRedisCalls.incrementAndGet();
        directModeRequests.incrementAndGet();

        // Atomic decrement
        Long stock = redisTemplate.opsForValue().decrement(inventoryKey);
        if (stock != null && stock >= 0) {
            return true;
        } else {
            // Restore if went negative
            redisTemplate.opsForValue().increment(inventoryKey);
            return false;
        }
    }

    /**
     * Get current metrics
     */
    public InventoryMetrics getMetrics() {
        return new InventoryMetrics(
            batchModeRequests.get(),
            directModeRequests.get(),
            totalRedisCalls.get(),
            modeSwitched.get()
        );
    }

    /**
     * Get current operation mode
     */
    public String getCurrentMode() {
        return directMode.get() ? "DIRECT" : "BATCH";
    }

    /**
     * Metrics data class
     */
    public static class InventoryMetrics {
        public final long batchModeRequests;
        public final long directModeRequests;
        public final long totalRedisCalls;
        public final boolean modeSwitched;

        public InventoryMetrics(long batchModeRequests, long directModeRequests,
                               long totalRedisCalls, boolean modeSwitched) {
            this.batchModeRequests = batchModeRequests;
            this.directModeRequests = directModeRequests;
            this.totalRedisCalls = totalRedisCalls;
            this.modeSwitched = modeSwitched;
        }
    }
}
