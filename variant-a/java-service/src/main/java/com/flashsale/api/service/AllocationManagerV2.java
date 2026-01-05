package com.flashsale.api.service;

import com.flashsale.api.entity.CampaignSkuAllocation;
import com.flashsale.api.repository.CampaignSkuAllocationRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.net.InetAddress;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Allocation Manager V2 - Claims and manages allocation units for service instances
 *
 * Responsibilities:
 * - Claim allocation units from database on startup
 * - Load claimed units into AdaptiveInventoryV2 managers
 * - Provide access to adaptive inventory instances
 */
@Service
public class AllocationManagerV2 {

    private static final Logger logger = LoggerFactory.getLogger(AllocationManagerV2.class);

    private final CampaignSkuAllocationRepository allocationRepository;
    private final RedisTemplate<String, Object> redisTemplate;

    // Service instance ID (unique per container/pod)
    private final String serviceId;

    // Map of SKU ID → AdaptiveInventoryV2 instance
    private final Map<UUID, AdaptiveInventoryV2> inventoryManagers = new ConcurrentHashMap<>();

    // Track claimed allocation IDs
    private final List<Long> claimedAllocationIds = new ArrayList<>();

    public AllocationManagerV2(
            CampaignSkuAllocationRepository allocationRepository,
            RedisTemplate<String, Object> redisTemplate) {

        this.allocationRepository = allocationRepository;
        this.redisTemplate = redisTemplate;

        // Generate unique service ID (hostname + UUID)
        this.serviceId = generateServiceId();
    }

    /**
     * Generate unique service ID for this instance
     * Format: java-{hostname}-{uuid}
     */
    private String generateServiceId() {
        try {
            String hostname = InetAddress.getLocalHost().getHostName();
            String shortUuid = UUID.randomUUID().toString().substring(0, 12);
            return String.format("java-%s-%s", hostname, shortUuid);
        } catch (Exception e) {
            logger.warn("Failed to get hostname, using UUID only", e);
            return String.format("java-%s", UUID.randomUUID().toString().substring(0, 12));
        }
    }

    /**
     * Claim allocation units and load into memory
     *
     * @param campaignId Campaign to claim units for
     * @return Number of units claimed
     */
    @Transactional
    public int claimAndLoadAllocations(UUID campaignId) {
        logger.info("=" + "=".repeat(60));
        logger.info("VARIANT A: Initializing Adaptive Inventory System");
        logger.info("=" + "=".repeat(60));
        logger.info("Service ID: {}", serviceId);

        // Determine max units to claim based on service capacity
        int maxUnits = getMaxUnitsForService();

        // Claim units atomically
        int claimedCount = allocationRepository.claimUnits(
            serviceId,
            campaignId.toString(),
            maxUnits
        );

        if (claimedCount == 0) {
            logger.warn(
                "⚠️  No allocation units claimed! " +
                "This service will fall back to Redis campaign pool immediately."
            );
            return 0;
        }

        logger.info("Claimed {} allocation units for campaign {}", claimedCount, campaignId);

        // Load claimed units into memory
        List<CampaignSkuAllocation> units = allocationRepository.findByClaimedByAndCampaignId(
            serviceId,
            campaignId
        );

        int totalAllocated = 0;
        for (CampaignSkuAllocation unit : units) {
            // Create AdaptiveInventoryV2 instance
            AdaptiveInventoryV2 inventory = new AdaptiveInventoryV2(
                unit.getId(),
                unit.getCampaignId(),
                unit.getSkuId(),
                unit.getAllocatedQuantity(),
                unit.getRefillBatchSize(),
                unit.getLowWaterMarkPct(),
                redisTemplate
            );

            // Store by SKU ID (for quick lookup during order processing)
            inventoryManagers.put(unit.getSkuId(), inventory);
            claimedAllocationIds.add(unit.getId());

            totalAllocated += unit.getAllocatedQuantity();

            logger.info(
                "Loaded allocation unit {}: SKU={}, qty={}, batch={}, watermark={}%",
                unit.getId(), unit.getSkuId(), unit.getAllocatedQuantity(),
                unit.getRefillBatchSize(), unit.getLowWaterMarkPct()
            );

            // Log initial metrics
            AdaptiveInventoryV2.InventoryMetrics metrics = inventory.getMetrics();
            logger.info(
                "  Unit {}: {} items in RAM, low_water_mark={}",
                metrics.allocationId, metrics.localStock, metrics.currentLowWaterMark
            );
        }

        logger.info("Total inventory loaded: {} items across {} units", totalAllocated, claimedCount);
        logger.info("=" + "=".repeat(60));
        logger.info("✓ Adaptive Inventory Initialization Complete");
        logger.info("  Ready to serve requests from local memory!");
        logger.info("=" + "=".repeat(60));

        return claimedCount;
    }

    /**
     * Get adaptive inventory manager for a SKU
     *
     * @param skuId SKU ID
     * @return AdaptiveInventoryV2 instance, or null if not found
     */
    public AdaptiveInventoryV2 getInventoryManager(UUID skuId) {
        return inventoryManagers.get(skuId);
    }

    /**
     * Check if service has allocation units for any SKU
     */
    public boolean hasAllocations() {
        return !inventoryManagers.isEmpty();
    }

    /**
     * Get all metrics from claimed allocation units
     */
    public Map<String, Object> getAllMetrics() {
        Map<String, Object> allMetrics = new HashMap<>();

        List<Map<String, Object>> unitMetrics = new ArrayList<>();
        for (AdaptiveInventoryV2 inventory : inventoryManagers.values()) {
            AdaptiveInventoryV2.InventoryMetrics m = inventory.getMetrics();

            Map<String, Object> metrics = new HashMap<>();
            metrics.put("allocation_id", m.allocationId);
            metrics.put("local_stock", m.localStock);
            metrics.put("current_low_water_mark", m.currentLowWaterMark);
            metrics.put("total_requests", m.totalRequests);
            metrics.put("ram_hits", m.ramHits);
            metrics.put("ram_hit_rate_pct", String.format("%.2f", m.getRamHitRate()));
            metrics.put("redis_refills", m.redisRefills);
            metrics.put("campaign_pool_hits", m.campaignPoolHits);
            metrics.put("refill_in_progress", m.refillInProgress);

            unitMetrics.add(metrics);
        }

        allMetrics.put("service_id", serviceId);
        allMetrics.put("claimed_units", claimedAllocationIds.size());
        allMetrics.put("unit_metrics", unitMetrics);

        return allMetrics;
    }

    /**
     * Calculate max units to claim based on service capacity
     * Can be configured via environment variables or service discovery
     *
     * @return Maximum number of units to claim
     */
    private int getMaxUnitsForService() {
        // For now, use simple heuristic: 2 units per service instance
        // In production, this could be based on:
        // - Available memory
        // - CPU cores
        // - Service tier/capacity
        // - Environment variable configuration

        String maxUnitsEnv = System.getenv("MAX_ALLOCATION_UNITS");
        if (maxUnitsEnv != null) {
            try {
                return Integer.parseInt(maxUnitsEnv);
            } catch (NumberFormatException e) {
                logger.warn("Invalid MAX_ALLOCATION_UNITS value: {}", maxUnitsEnv);
            }
        }

        return 2; // Default: 2 units per service
    }

    public String getServiceId() {
        return serviceId;
    }

    public List<Long> getClaimedAllocationIds() {
        return new ArrayList<>(claimedAllocationIds);
    }
}
