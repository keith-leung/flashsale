package com.flashsale.api.config;

import com.flashsale.api.service.AllocationManagerV2;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.stereotype.Component;

import java.util.UUID;

/**
 * Startup Configuration for Variant A Corrected
 *
 * Initializes adaptive inventory on application startup:
 * 1. Claims allocation units from database
 * 2. Loads units into memory
 * 3. Makes adaptive inventory available to order service
 */
@Component
public class StartupConfiguration implements ApplicationRunner {

    private static final Logger logger = LoggerFactory.getLogger(StartupConfiguration.class);

    private final AllocationManagerV2 allocationManager;

    // Default campaign ID for flash sale
    private static final String DEFAULT_CAMPAIGN_ID = "750e8400-e29b-41d4-a716-446655440000";

    @Autowired
    public StartupConfiguration(AllocationManagerV2 allocationManager) {
        this.allocationManager = allocationManager;
    }

    @Override
    public void run(ApplicationArguments args) throws Exception {
        logger.info("Starting Flash Sale Service - Variant A Corrected");

        try {
            // Initialize adaptive inventory for default campaign
            UUID campaignId = UUID.fromString(DEFAULT_CAMPAIGN_ID);

            int claimedCount = allocationManager.claimAndLoadAllocations(campaignId);

            if (claimedCount == 0) {
                logger.warn(
                    "⚠️  WARNING: No allocation units claimed! " +
                    "Service will fall back to Redis campaign pool for all requests."
                );
            } else {
                logger.info(
                    "✓ Successfully claimed and loaded {} allocation units",
                    claimedCount
                );
            }

        } catch (Exception e) {
            logger.error("Failed to initialize adaptive inventory", e);
            logger.warn("Service will fall back to Redis campaign pool for all requests");
        }

        logger.info("Flash Sale Service startup complete");
    }
}
