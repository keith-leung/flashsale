package com.flashsale.api.service;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicLong;

/**
 * Variant A: High-Performance Adaptive Batching (Producer-Consumer Pattern v2)
 *
 * Architecture:
 * - Each SKU has its own AdaptiveInventoryUnit with local RAM stock
 * - Producer: Async refill task triggered at low water mark (non-blocking)
 * - Consumer: Hot path serves from local RAM (~0ms latency)
 * - Failover: RAM -> SpinWait -> Direct Redis DECR -> Ordinary Stock
 *
 * Redis Keys:
 * - SKU Pool: fs:{campaign_id}:redis_pool:sku:{sku_id}
 * - Ordinary Stock: inv:{sku_id}
 */
@Service
public class CampaignMemoryAllocator {

    private static final Logger logger = LoggerFactory.getLogger(CampaignMemoryAllocator.class);

    private final RedisTemplate<String, Object> redisTemplate;
    private final ConcurrentHashMap<UUID, AdaptiveInventoryUnit> skuUnits;
    private final ConcurrentHashMap<UUID, CampaignConfig> campaignConfigs;
    private final ExecutorService refillExecutor;

    public CampaignMemoryAllocator(RedisTemplate<String, Object> redisTemplate) {
        this.redisTemplate = redisTemplate;
        this.skuUnits = new ConcurrentHashMap<>();
        this.campaignConfigs = new ConcurrentHashMap<>();
        // Use virtual threads for async refills (Java 21+)
        this.refillExecutor = Executors.newVirtualThreadPerTaskExecutor();

        logger.info("CampaignMemoryAllocator initialized (Producer-Consumer v2)");
    }

    /**
     * Load a campaign and create AdaptiveInventoryUnit for each SKU
     */
    public void loadCampaign(
            UUID campaignId,
            UUID spuId,
            Map<UUID, Integer> skuAllocations,
            BigDecimal flashPrice,
            BigDecimal ordinaryPrice,
            double refillWatermarkPct,
            int refillBatchSize
    ) {
        // Store campaign config
        campaignConfigs.put(campaignId, new CampaignConfig(
                campaignId, spuId, flashPrice, ordinaryPrice));

        // Create AdaptiveInventoryUnit for each SKU
        for (Map.Entry<UUID, Integer> entry : skuAllocations.entrySet()) {
            UUID skuId = entry.getKey();
            int allocatedQuantity = entry.getValue();

            AdaptiveInventoryUnit unit = new AdaptiveInventoryUnit(
                    campaignId,
                    skuId,
                    allocatedQuantity,
                    refillBatchSize,
                    refillWatermarkPct,
                    flashPrice,
                    ordinaryPrice,
                    redisTemplate,
                    refillExecutor
            );

            skuUnits.put(skuId, unit);

            logger.info(
                    "SKU {} initialized: {} items, batch={}, watermark={}%",
                    skuId, allocatedQuantity, refillBatchSize, refillWatermarkPct);
        }

        logger.info(
                "Campaign {} loaded: {} SKUs, flash={}, ordinary={}",
                campaignId, skuAllocations.size(), flashPrice, ordinaryPrice);
    }

    /**
     * Reserve one item using Producer-Consumer pattern
     */
    public ReservationResult reserveItem(UUID campaignId, UUID skuId) {
        AdaptiveInventoryUnit unit = skuUnits.get(skuId);

        if (unit == null) {
            logger.warn("SKU {} not allocated to this service", skuId);
            return new ReservationResult(false, "not_allocated", BigDecimal.ZERO);
        }

        return unit.reserveItem();
    }

    /**
     * Get metrics for monitoring
     */
    public Map<UUID, InventoryMetrics> getMetrics() {
        Map<UUID, InventoryMetrics> metrics = new HashMap<>();
        for (Map.Entry<UUID, AdaptiveInventoryUnit> entry : skuUnits.entrySet()) {
            metrics.put(entry.getKey(), entry.getValue().getMetrics());
        }
        return metrics;
    }

    // ========================================
    // Inner Classes
    // ========================================

    public static class CampaignConfig {
        public final UUID campaignId;
        public final UUID spuId;
        public final BigDecimal flashPrice;
        public final BigDecimal ordinaryPrice;

        public CampaignConfig(UUID campaignId, UUID spuId, BigDecimal flashPrice, BigDecimal ordinaryPrice) {
            this.campaignId = campaignId;
            this.spuId = spuId;
            this.flashPrice = flashPrice;
            this.ordinaryPrice = ordinaryPrice;
        }
    }

    public static class ReservationResult {
        public final boolean success;
        public final String priceType;  // campaign, ordinary, sold_out, not_allocated
        public final BigDecimal price;

        public ReservationResult(boolean success, String priceType, BigDecimal price) {
            this.success = success;
            this.priceType = priceType;
            this.price = price;
        }
    }

    public static class InventoryMetrics {
        public int localStock;
        public int lowWaterMark;
        public long totalRequests;
        public long ramHits;
        public long redisRefills;
        public long redisDirectHits;
        public String ramHitRate;
    }
}

/**
 * Per-SKU Adaptive Inventory Unit with Producer-Consumer Pattern
 *
 * Consumer: Hot path decrements local RAM stock (~0ms)
 * Producer: Async refill from Redis SKU pool when watermark hit
 */
class AdaptiveInventoryUnit {

    private static final Logger logger = LoggerFactory.getLogger(AdaptiveInventoryUnit.class);

    private final UUID campaignId;
    private final UUID skuId;
    private final RedisTemplate<String, Object> redisTemplate;
    private final ExecutorService refillExecutor;

    // Configuration
    private final int initialQuantity;
    private final int refillBatchSize;
    private final double lowWaterMarkPct;
    private final BigDecimal flashPrice;
    private final BigDecimal ordinaryPrice;

    // Local memory counter (CONSUMER) - Lock-free using CAS
    private final AtomicInteger localStock;

    // Refill coordination (PRODUCER)
    private volatile boolean refillInProgress;
    private volatile int currentLowWaterMark;

    // Metrics
    private final AtomicLong totalRequests = new AtomicLong(0);
    private final AtomicLong ramHits = new AtomicLong(0);
    private final AtomicLong redisRefills = new AtomicLong(0);
    private final AtomicLong redisDirectHits = new AtomicLong(0);

    // Redis keys
    private final String skuPoolKey;
    private final String ordinaryStockKey;

    public AdaptiveInventoryUnit(
            UUID campaignId,
            UUID skuId,
            int allocatedQuantity,
            int refillBatchSize,
            double lowWaterMarkPct,
            BigDecimal flashPrice,
            BigDecimal ordinaryPrice,
            RedisTemplate<String, Object> redisTemplate,
            ExecutorService refillExecutor
    ) {
        this.campaignId = campaignId;
        this.skuId = skuId;
        this.redisTemplate = redisTemplate;
        this.refillExecutor = refillExecutor;

        this.initialQuantity = allocatedQuantity;
        this.refillBatchSize = refillBatchSize;
        this.lowWaterMarkPct = lowWaterMarkPct / 100.0;
        this.flashPrice = flashPrice;
        this.ordinaryPrice = ordinaryPrice;

        this.localStock = new AtomicInteger(allocatedQuantity);
        this.currentLowWaterMark = (int) (allocatedQuantity * this.lowWaterMarkPct);
        this.refillInProgress = false;

        // Redis keys - CORRECT FORMAT for Variant A v2
        this.skuPoolKey = String.format("fs:%s:redis_pool:sku:%s", campaignId, skuId);
        this.ordinaryStockKey = String.format("inv:%s", skuId);

        logger.info(
                "[SKU {}] Initialized: {} items, watermark={}, refill_source={}",
                skuId, allocatedQuantity, currentLowWaterMark, skuPoolKey);
    }

    /**
     * Reserve one item (Producer-Consumer pattern) - LOCK-FREE VERSION
     *
     * Uses CAS (Compare-And-Swap) instead of synchronized blocks
     * for maximum throughput under high concurrency.
     *
     * Returns: ReservationResult(success, price_type, price)
     */
    public CampaignMemoryAllocator.ReservationResult reserveItem() {
        totalRequests.incrementAndGet();

        // ========================================
        // FAST PATH: Local RAM with CAS (Consumer - ~0ms)
        // ========================================
        int current;
        do {
            current = localStock.get();
            if (current <= 0) {
                // Stock depleted, go to slow path
                return handleDepleted();
            }
        } while (!localStock.compareAndSet(current, current - 1));

        // Successfully decremented
        ramHits.incrementAndGet();

        // Check low water mark (trigger async refill) - non-blocking check
        if (current - 1 == currentLowWaterMark && !refillInProgress) {
            // Fire and forget - async refill in background
            refillExecutor.submit(this::asyncRefill);
        }

        return new CampaignMemoryAllocator.ReservationResult(true, "campaign", flashPrice);
    }

    /**
     * Handle local stock depletion (Failover Chain) - LOCK-FREE VERSION
     *
     * 1. Brief CAS retry if refill in progress (panic buffer)
     * 2. Direct Redis DECR on SKU pool
     * 3. Fallback to ordinary stock
     */
    private CampaignMemoryAllocator.ReservationResult handleDepleted() {
        // ========================================
        // TIER 2: Panic Buffer - Lock-free CAS retry
        // ========================================
        if (refillInProgress) {
            // Try up to 5 times with LockSupport.parkNanos yield
            for (int attempt = 0; attempt < 5; attempt++) {
                int current = localStock.get();
                if (current > 0) {
                    if (localStock.compareAndSet(current, current - 1)) {
                        ramHits.incrementAndGet();
                        return new CampaignMemoryAllocator.ReservationResult(true, "campaign", flashPrice);
                    }
                    // CAS failed, retry immediately
                    continue;
                }

                // Check if should give up
                if (!refillInProgress && localStock.get() == 0) {
                    break;
                }

                // Yield CPU for 1ms instead of blocking sleep
                java.util.concurrent.locks.LockSupport.parkNanos(1_000_000);
            }
        }

        // ========================================
        // TIER 3: Direct Redis DECR (SKU Pool)
        // ========================================
        try {
            Long remaining = redisTemplate.opsForValue().decrement(skuPoolKey);

            if (remaining != null && remaining >= 0) {
                redisDirectHits.incrementAndGet();
                logger.info(
                        "[SKU {}] Redis SKU pool hit, remaining: {}",
                        skuId, remaining);
                return new CampaignMemoryAllocator.ReservationResult(true, "campaign", flashPrice);
            } else if (remaining != null) {
                // Rollback negative
                redisTemplate.opsForValue().increment(skuPoolKey);
            }
        } catch (Exception e) {
            logger.error("[SKU {}] Redis SKU pool error: {}", skuId, e.getMessage());
        }

        // ========================================
        // TIER 4: Ordinary Stock (Final Fallback)
        // ========================================
        try {
            Long remaining = redisTemplate.opsForValue().decrement(ordinaryStockKey);

            if (remaining != null && remaining >= 0) {
                logger.warn(
                        "[SKU {}] BENCHMARK STOP: Fell back to ordinary stock, remaining: {}",
                        skuId, remaining);
                return new CampaignMemoryAllocator.ReservationResult(true, "ordinary", ordinaryPrice);
            } else if (remaining != null) {
                redisTemplate.opsForValue().increment(ordinaryStockKey);
            }
        } catch (Exception e) {
            logger.error("[SKU {}] Ordinary stock error: {}", skuId, e.getMessage());
        }

        // Completely sold out
        return new CampaignMemoryAllocator.ReservationResult(false, "sold_out", BigDecimal.ZERO);
    }

    /**
     * PRODUCER: Async refill from Redis SKU pool - LOCK-FREE VERSION
     *
     * Uses single-flight pattern (refillInProgress flag)
     * Implements cascading low water marks
     * Uses atomic operations instead of synchronized blocks
     */
    private void asyncRefill() {
        // Single-flight check
        if (refillInProgress) {
            logger.debug("[SKU {}] Refill already in progress, skipping", skuId);
            return;
        }

        refillInProgress = true;
        long refillStart = System.currentTimeMillis();

        try {
            // Check if refill worth it
            int currentStock = localStock.get();
            if (currentStock < 10 && refillBatchSize < 10) {
                logger.debug("[SKU {}] Skipping refill: stock too small", skuId);
                return;
            }

            // DECRBY Redis SKU pool
            Long remaining = redisTemplate.opsForValue().decrement(skuPoolKey, refillBatchSize);

            if (remaining != null && remaining >= 0) {
                // Success: Add to local stock using atomic operation
                int oldStock = localStock.get();
                int newStock = localStock.addAndGet(refillBatchSize);

                // Update cascading low water mark
                currentLowWaterMark = (int) (newStock * lowWaterMarkPct);

                redisRefills.incrementAndGet();

                long latencyMs = System.currentTimeMillis() - refillStart;

                logger.info(
                        "[SKU {}] Refill SUCCESS: {} -> {} (+{}), watermark={}, pool={}, latency={}ms",
                        skuId, oldStock, newStock, refillBatchSize, currentLowWaterMark, remaining, latencyMs);
            } else if (remaining != null) {
                // Pool depleted, rollback
                redisTemplate.opsForValue().increment(skuPoolKey, refillBatchSize);
                logger.warn("[SKU {}] Refill FAILED: SKU pool depleted", skuId);
            }
        } catch (Exception e) {
            logger.error("[SKU {}] Refill error: {}", skuId, e.getMessage());
        } finally {
            refillInProgress = false;
        }
    }

    public CampaignMemoryAllocator.InventoryMetrics getMetrics() {
        CampaignMemoryAllocator.InventoryMetrics metrics = new CampaignMemoryAllocator.InventoryMetrics();
        metrics.localStock = localStock.get();
        metrics.lowWaterMark = currentLowWaterMark;
        metrics.totalRequests = totalRequests.get();
        metrics.ramHits = ramHits.get();
        metrics.redisRefills = redisRefills.get();
        metrics.redisDirectHits = redisDirectHits.get();
        metrics.ramHitRate = totalRequests.get() > 0
                ? String.format("%.2f%%", (ramHits.get() * 100.0 / totalRequests.get()))
                : "0%";
        return metrics;
    }
}
