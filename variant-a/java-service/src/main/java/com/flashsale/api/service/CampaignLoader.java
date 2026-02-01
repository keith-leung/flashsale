package com.flashsale.api.service;

import com.flashsale.api.entity.FlashSale;
import com.flashsale.api.entity.FlashSaleCampaignStatus;
import com.flashsale.api.entity.Sku;
import com.flashsale.api.repository.FlashSaleRepository;
import com.flashsale.api.repository.SkuRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.CommandLineRunner;
import org.springframework.context.annotation.Profile;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * Loads active flash sale campaigns into the CampaignMemoryAllocator on startup.
 * This is CRITICAL for Variant A (Fast Path) to function.
 * Without this, requests fall back to Variant Y (DB transactions).
 */
@Component
public class CampaignLoader implements CommandLineRunner {

    private static final Logger logger = LoggerFactory.getLogger(CampaignLoader.class);

    private final FlashSaleRepository flashSaleRepository;
    private final SkuRepository skuRepository;
    private final CampaignMemoryAllocator allocator;

    @Autowired
    public CampaignLoader(
            FlashSaleRepository flashSaleRepository,
            SkuRepository skuRepository,
            CampaignMemoryAllocator allocator) {
        this.flashSaleRepository = flashSaleRepository;
        this.skuRepository = skuRepository;
        this.allocator = allocator;
    }

    @Override
    @Transactional(readOnly = true)
    public void run(String... args) throws Exception {
        if ("true".equals(System.getenv("BENCHMARK_MODE"))) {
            logger.info("BENCHMARK_MODE=true: Skipping automatic campaign loading (benchmark will lazy load)");
            return;
        }

        logger.info("Starting CampaignLoader...");
        loadActiveCampaigns();
    }

    private void loadActiveCampaigns() {
        try {
            LocalDateTime now = LocalDateTime.now();
            List<FlashSale> activeCampaigns = flashSaleRepository.findActiveByStatus(
                    FlashSaleCampaignStatus.active, now
            );

            logger.info("Found {} active campaigns to load", activeCampaigns.size());

            for (FlashSale campaign : activeCampaigns) {
                loadCampaign(campaign);
            }
        } catch (Exception e) {
            logger.error("Failed to load active campaigns", e);
        }
    }

    private void loadCampaign(FlashSale campaign) {
        try {
            logger.info("Loading campaign: {} ({})", campaign.getName(), campaign.getId());

            // 1. Fetch SKUs for this SPU
            // We need to paginate or just fetch all. SkuRepository has findBySpuId returning Page.
            // Let's rely on the fact that standard flash sales don't have thousands of SKUs per SPU.
            // Using a large page size.
            // Actually, SkuRepository has findBySpuId but it takes Pageable.
            // Let's use findAllWithInventory/findBySpuId logic from service.
            // Or better, use a custom query if needed. 
            // SkuRepository has: Page<Sku> findBySpuId(UUID spuId, Pageable pageable);
            
            // Hack: Just get first 1000 SKUs.
            List<Sku> skus = skuRepository.findBySpuId(
                    campaign.getSpuId(), 
                    org.springframework.data.domain.PageRequest.of(0, 1000)
            ).getContent();

            if (skus.isEmpty()) {
                logger.warn("No SKUs found for campaign {}, skipping", campaign.getId());
                return;
            }

            // 2. Calculate Allocation
            BigDecimal preallocatePct = campaign.getPreallocatePercentage() != null 
                    ? campaign.getPreallocatePercentage() 
                    : new BigDecimal("60.00");
            
            int pythonRatio = campaign.getPythonAllocationRatio() != null ? campaign.getPythonAllocationRatio() : 1;
            int javaRatio = campaign.getJavaAllocationRatio() != null ? campaign.getJavaAllocationRatio() : 13;
            int csharpRatio = campaign.getCsharpAllocationRatio() != null ? campaign.getCsharpAllocationRatio() : 20;
            
            int totalRatio = pythonRatio + javaRatio + csharpRatio;
            
            // Calculate total items for this service (Java)
            // Total Limit * Preallocate% * (JavaRatio / TotalRatio)
            double serviceShare = (double) javaRatio / totalRatio;
            int totalPreallocated = (int) (campaign.getTotalSaleLimit() * (preallocatePct.doubleValue() / 100.0) * serviceShare);
            
            // Distribute evenly across SKUs
            int itemsPerSku = totalPreallocated / skus.size();
            
            Map<UUID, Integer> skuAllocations = new HashMap<>();
            for (Sku sku : skus) {
                skuAllocations.put(sku.getId(), itemsPerSku);
            }

            // 3. Load into Allocator
            BigDecimal ordinaryPrice = skus.get(0).getPrice(); // Assume similar price or take first
            double watermarkPct = campaign.getRefillLowerWatermarkPct() != null 
                    ? campaign.getRefillLowerWatermarkPct().doubleValue() 
                    : 25.0;

            allocator.loadCampaign(
                    campaign.getId(),
                    campaign.getSpuId(),
                    skuAllocations,
                    campaign.getFlashPrice(),
                    ordinaryPrice,
                    watermarkPct
            );

            logger.info("Successfully loaded campaign {}. Java Allocation: {} items across {} SKUs", 
                    campaign.getId(), totalPreallocated, skus.size());

        } catch (Exception e) {
            logger.error("Error loading campaign {}", campaign.getId(), e);
        }
    }
}
