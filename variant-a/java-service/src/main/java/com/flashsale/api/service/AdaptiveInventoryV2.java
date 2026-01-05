package com.flashsale.api.service;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.data.redis.core.RedisTemplate;

import java.math.BigDecimal;
import java.util.UUID;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicLong;
import java.util.concurrent.locks.ReentrantLock;

/**
 * Adaptive Inventory V2 - Producer-Consumer Pattern with Async Refills
 *
 * Corrected implementation for Variant A flash sale:
 * - Each allocation unit starts with allocated_quantity items in RAM (e.g., 500)
 * - When hitting low water mark (e.g., 30% = 150 items), trigger async refill
 * - Async refill pulls refill_batch_size items (e.g., 50) from Redis campaign pool
 * - Refills cascade: 500→150→45→13... (each refill hits new 30% threshold)
 * - Three-tier fallback: Local RAM → Redis campaign pool → Ordinary stock
 */
public class AdaptiveInventoryV2 {

    private static final Logger logger = LoggerFactory.getLogger(AdaptiveInventoryV2.class);

    // Allocation unit configuration
    private final Long allocationId;
    private final UUID campaignId;
    private final UUID skuId;
    private final int allocatedQuantity;     // Initial quantity (e.g., 500)
    private final int refillBatchSize;        // Refill amount (e.g., 50)
    private final BigDecimal lowWaterMarkPct; // e.g., 0.30 (30%)

    // Redis client
    private final RedisTemplate<String, Object> redisTemplate;
    private final String campaignPoolKey;  // fs:{campaignId}:limit

    // Local stock management (Producer-Consumer)
    private final AtomicInteger localStock;
    private final AtomicInteger currentLowWaterMark;
    private final ReentrantLock stockLock = new ReentrantLock();

    // Refill management (single-flight pattern)
    private final AtomicBoolean refillInProgress = new AtomicBoolean(false);

    // Metrics
    private final AtomicLong totalRequests = new AtomicLong(0);
    private final AtomicLong ramHits = new AtomicLong(0);
    private final AtomicLong redisRefills = new AtomicLong(0);
    private final AtomicLong campaignPoolHits = new AtomicLong(0);

    public AdaptiveInventoryV2(
            Long allocationId,
            UUID campaignId,
            UUID skuId,
            int allocatedQuantity,
            int refillBatchSize,
            BigDecimal lowWaterMarkPct,
            RedisTemplate<String, Object> redisTemplate) {

        this.allocationId = allocationId;
        this.campaignId = campaignId;
        this.skuId = skuId;
        this.allocatedQuantity = allocatedQuantity;
        this.refillBatchSize = refillBatchSize;
        this.lowWaterMarkPct = lowWaterMarkPct;
        this.redisTemplate = redisTemplate;

        // Initialize local stock with allocated quantity
        this.localStock = new AtomicInteger(allocatedQuantity);

        // Calculate initial low water mark (30% of allocated quantity)
        int initialLowWaterMark = (int) (allocatedQuantity * lowWaterMarkPct.doubleValue());
        this.currentLowWaterMark = new AtomicInteger(initialLowWaterMark);

        // Redis key for campaign pool
        this.campaignPoolKey = String.format("fs:%s:limit", campaignId);

        logger.info(
            "[Allocation {}] Initialized: {} items in RAM, low_water_mark={}, refill_batch={}",
            allocationId, allocatedQuantity, initialLowWaterMark, refillBatchSize
        );
    }

    /**
     * Reserve one item using producer-consumer pattern
     *
     * Returns: ReservationResult with success flag, price type, and price value
     */
    public ReservationResult reserveItem() {
        totalRequests.incrementAndGet();

        // CONSUMER: Try local RAM first (fast path - pure memory)
        int current = localStock.get();
        if (current > 0) {
            if (localStock.compareAndSet(current, current - 1)) {
                ramHits.incrementAndGet();

                // Check if hit low water mark (trigger async refill)
                int newStock = current - 1;
                if (newStock == currentLowWaterMark.get() && !refillInProgress.get()) {
                    // Trigger async refill (PRODUCER - non-blocking!)
                    CompletableFuture.runAsync(this::doRefill);
                }

                return new ReservationResult(true, "campaign", BigDecimal.valueOf(79.99));
            }
            // CAS failed, retry
            return reserveItem();
        }

        // Local RAM depleted, try panic buffer (spin wait for refill)
        return handleDepleted();
    }

    /**
     * Handle depleted local stock
     * - Spin wait briefly (5-10ms) in case refill is in progress
     * - If still no stock, fall back to Redis campaign pool
     */
    private ReservationResult handleDepleted() {
        long spinStart = System.nanoTime();
        long spinDeadline = spinStart + 10_000_000; // 10ms max spin

        while (System.nanoTime() < spinDeadline) {
            Thread.onSpinWait(); // CPU hint for spin-wait

            int current = localStock.get();
            if (current > 0) {
                if (localStock.compareAndSet(current, current - 1)) {
                    ramHits.incrementAndGet();
                    return new ReservationResult(true, "campaign", BigDecimal.valueOf(79.99));
                }
            }

            // Check if should give up (no refill in progress and still 0)
            if (!refillInProgress.get() && localStock.get() == 0) {
                break;
            }
        }

        // Fallback: Try Redis campaign pool directly
        return tryRedisCampaignPool();
    }

    /**
     * PRODUCER: Execute async refill operation
     * Pulls refill_batch_size items from Redis campaign pool to local RAM
     */
    private void doRefill() {
        // Single-flight protection
        if (!refillInProgress.compareAndSet(false, true)) {
            return; // Another thread is already refilling
        }

        long refillStart = System.nanoTime();

        try {
            // Calculate refill amount
            int refillAmount = refillBatchSize;

            // Check if refill amount too small (not worth overhead)
            int currentStock = localStock.get();
            if (currentStock < 10 && refillAmount < 10) {
                logger.debug(
                    "[Allocation {}] Skipping refill: stock={}, refill={} too small",
                    allocationId, currentStock, refillAmount
                );
                return;
            }

            // DECRBY Redis campaign pool (ONLY HERE - rare Redis call!)
            Long campaignRemaining = redisTemplate.opsForValue().decrement(campaignPoolKey, refillAmount);

            if (campaignRemaining != null && campaignRemaining >= 0) {
                // Success: Add to local stock
                stockLock.lock();
                try {
                    int oldStock = localStock.get();
                    int newStock = oldStock + refillAmount;
                    localStock.set(newStock);

                    // Update cascading low water mark (30% of new stock)
                    int newLowWaterMark = (int) (newStock * lowWaterMarkPct.doubleValue());
                    currentLowWaterMark.set(newLowWaterMark);

                    redisRefills.incrementAndGet();

                    long refillLatencyMs = (System.nanoTime() - refillStart) / 1_000_000;

                    logger.info(
                        "[Allocation {}] Refill SUCCESS: {} → {} (+{}), " +
                        "new_low_mark={}, campaign_pool={}, latency={}ms",
                        allocationId, oldStock, newStock, refillAmount,
                        newLowWaterMark, campaignRemaining, refillLatencyMs
                    );
                } finally {
                    stockLock.unlock();
                }
            } else {
                // Campaign pool depleted, rollback
                redisTemplate.opsForValue().increment(campaignPoolKey, refillAmount);
                logger.warn(
                    "[Allocation {}] Refill FAILED: campaign pool depleted",
                    allocationId
                );
            }

        } catch (Exception e) {
            logger.error("[Allocation " + allocationId + "] Refill error", e);
        } finally {
            refillInProgress.set(false);
        }
    }

    /**
     * Try to reserve from Redis campaign pool directly (fallback tier 2)
     */
    private ReservationResult tryRedisCampaignPool() {
        Long remaining = redisTemplate.opsForValue().decrement(campaignPoolKey);

        if (remaining != null && remaining >= 0) {
            campaignPoolHits.incrementAndGet();
            logger.debug(
                "[Allocation {}] Reserved from campaign pool, remaining={}",
                allocationId, remaining
            );
            return new ReservationResult(true, "campaign", BigDecimal.valueOf(79.99));
        } else {
            // Restore if went negative
            if (remaining != null && remaining < 0) {
                redisTemplate.opsForValue().increment(campaignPoolKey);
            }

            // Campaign pool exhausted, fall back to ordinary stock (tier 3)
            logger.warn(
                "[BENCHMARK STOP INDICATOR] Allocation {} campaign pool exhausted, " +
                "falling back to ordinary stock",
                allocationId
            );
            return tryOrdinaryStock();
        }
    }

    /**
     * Try to reserve from ordinary stock (fallback tier 3)
     * In benchmark mode, this should stop the benchmark (campaign exhausted)
     */
    private ReservationResult tryOrdinaryStock() {
        String ordinaryStockKey = String.format("inv:%s", skuId);
        Long remaining = redisTemplate.opsForValue().decrement(ordinaryStockKey);

        if (remaining != null && remaining >= 0) {
            logger.warn(
                "[Allocation {}] Using ordinary stock (price=199.99), campaign exhausted",
                allocationId
            );
            return new ReservationResult(true, "ordinary", BigDecimal.valueOf(199.99));
        } else {
            // Restore if went negative
            if (remaining != null && remaining < 0) {
                redisTemplate.opsForValue().increment(ordinaryStockKey);
            }

            // Completely sold out
            return new ReservationResult(false, "sold_out", BigDecimal.ZERO);
        }
    }

    /**
     * Get current metrics for this allocation unit
     */
    public InventoryMetrics getMetrics() {
        return new InventoryMetrics(
            allocationId,
            localStock.get(),
            currentLowWaterMark.get(),
            totalRequests.get(),
            ramHits.get(),
            redisRefills.get(),
            campaignPoolHits.get(),
            refillInProgress.get()
        );
    }

    /**
     * Reservation result containing success flag, price type, and price
     */
    public static class ReservationResult {
        public final boolean success;
        public final String priceType;  // "campaign", "ordinary", "sold_out"
        public final BigDecimal price;

        public ReservationResult(boolean success, String priceType, BigDecimal price) {
            this.success = success;
            this.priceType = priceType;
            this.price = price;
        }
    }

    /**
     * Metrics for an allocation unit
     */
    public static class InventoryMetrics {
        public final Long allocationId;
        public final int localStock;
        public final int currentLowWaterMark;
        public final long totalRequests;
        public final long ramHits;
        public final long redisRefills;
        public final long campaignPoolHits;
        public final boolean refillInProgress;

        public InventoryMetrics(
                Long allocationId, int localStock, int currentLowWaterMark,
                long totalRequests, long ramHits, long redisRefills,
                long campaignPoolHits, boolean refillInProgress) {
            this.allocationId = allocationId;
            this.localStock = localStock;
            this.currentLowWaterMark = currentLowWaterMark;
            this.totalRequests = totalRequests;
            this.ramHits = ramHits;
            this.redisRefills = redisRefills;
            this.campaignPoolHits = campaignPoolHits;
            this.refillInProgress = refillInProgress;
        }

        public double getRamHitRate() {
            return totalRequests > 0 ? (double) ramHits / totalRequests * 100 : 0;
        }
    }
}
