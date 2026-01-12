package com.flashsale.api.config;

import com.flashsale.api.entity.FlashSale;
import com.flashsale.api.entity.Sku;
import com.flashsale.api.repository.FlashSaleRepository;
import com.flashsale.api.repository.SkuRepository;
import com.flashsale.api.service.CampaignMemoryAllocator;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.stereotype.Component;

import java.math.BigDecimal;
import java.util.*;

/**
 * Startup Configuration for Variant A - Dual-Layer Architecture
 *
 * Initializes CampaignMemoryAllocator on application startup:
 * 1. Loads active flash sale campaigns from database
 * 2. Calculates per-service allocations based on ratios
 * 3. Loads campaigns into memory with dual-layer (SPU + SKU) tracking
 */
@Component
public class StartupConfiguration implements ApplicationRunner {

    private static final Logger logger = LoggerFactory.getLogger(StartupConfiguration.class);

    private final CampaignMemoryAllocator campaignAllocator;
    private final FlashSaleRepository flashSaleRepository;
    private final SkuRepository skuRepository;

    @Autowired
    public StartupConfiguration(
            CampaignMemoryAllocator campaignAllocator,
            FlashSaleRepository flashSaleRepository,
            SkuRepository skuRepository) {
        this.campaignAllocator = campaignAllocator;
        this.flashSaleRepository = flashSaleRepository;
        this.skuRepository = skuRepository;
    }

    @Override
    public void run(ApplicationArguments args) throws Exception {
        logger.info("=" + "=".repeat(60));
        logger.info("Starting Flash Sale Service - Variant A Dual-Layer");
        logger.info("=" + "=".repeat(60));

        try {
            // Load active flash sale campaigns with valid UUIDs only
            List<FlashSale> campaigns = flashSaleRepository.findActiveWithValidUUIDs("active").stream()
                .filter(c -> c.isTimeActive())
                .toList();

            if (campaigns.isEmpty()) {
                logger.warn("⚠️  No active flash sale campaigns found");
                logger.info("Flash Sale Service startup complete (no campaigns to load)");
                return;
            }

            logger.info("Found {} active campaigns to load", campaigns.size());

            int totalLoaded = 0;
            for (FlashSale campaign : campaigns) {
                try {
                    loadCampaign(campaign);
                    totalLoaded++;
                } catch (Exception e) {
                    logger.error("Failed to load campaign {}: {}", campaign.getId(), e.getMessage(), e);
                }
            }

            logger.info("=" + "=".repeat(60));
            logger.info("✓ Successfully loaded {} campaigns", totalLoaded);
            logger.info("=" + "=".repeat(60));

        } catch (Exception e) {
            logger.error("Failed to initialize campaign allocator", e);
            logger.warn("Service may fall back to Redis campaign pool for requests");
        }

        logger.info("Flash Sale Service startup complete");
    }

    /**
     * Load a single campaign into memory
     */
    private void loadCampaign(FlashSale campaign) {
        UUID campaignId = campaign.getId();
        UUID spuId = campaign.getSpuId();

        logger.info("Loading campaign: {} ({})", campaign.getName(), campaignId);

        // Get SKUs for this campaign's SPU
        List<Sku> skus = skuRepository.findBySpuIdAndIsActive(spuId, true);

        if (skus.isEmpty()) {
            logger.warn("Campaign {} has no active SKUs, skipping", campaignId);
            return;
        }

        // Calculate Java service allocation
        int totalLimit = campaign.getTotalSaleLimit();
        double preAllocPct = (campaign.getPreallocatePercentage() != null ?
                campaign.getPreallocatePercentage().doubleValue() : 60.0) / 100.0;

        int pythonRatio = campaign.getPythonAllocationRatio() != null ?
                campaign.getPythonAllocationRatio() : 1;
        int javaRatio = campaign.getJavaAllocationRatio() != null ?
                campaign.getJavaAllocationRatio() : 13;
        int csharpRatio = campaign.getCsharpAllocationRatio() != null ?
                campaign.getCsharpAllocationRatio() : 20;

        int totalRatio = pythonRatio + javaRatio + csharpRatio;

        int javaAllocation = (int) (totalLimit * preAllocPct * javaRatio / totalRatio);

        // Split evenly across SKUs
        Map<UUID, Integer> skuAllocations = new HashMap<>();
        int itemsPerSku = javaAllocation / skus.size();

        for (Sku sku : skus) {
            skuAllocations.put(sku.getId(), itemsPerSku);
        }

        // Get prices
        BigDecimal flashPrice = campaign.getFlashPrice();
        BigDecimal ordinaryPrice = skus.get(0).getPrice(); // Use first SKU's price as ordinary price

        // Load into campaign allocator
        double refillWatermarkPct = campaign.getRefillLowerWatermarkPct() != null ?
                campaign.getRefillLowerWatermarkPct().doubleValue() : 25.0;

        int refillBatchSize = 500; // Default batch size for Producer-Consumer pattern

        campaignAllocator.loadCampaign(
                campaignId,
                spuId,
                skuAllocations,
                flashPrice,
                ordinaryPrice,
                refillWatermarkPct,
                refillBatchSize
        );

        logger.info(
                "Campaign {} loaded: java_allocation={}, items_per_sku={}, skus={}",
                campaignId, javaAllocation, itemsPerSku, skus.size()
        );
    }
}
