package com.flashsale.service;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.io.ClassPathResource;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.data.redis.core.script.RedisScript;
import org.springframework.scripting.support.ResourceScriptSource;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.TimeUnit;

/**
 * Token pre-allocation service for Variant Z.
 * 
 * Manages campaign tokens in Redis sorted sets and handles atomic token acquisition
 * via Lua scripts.
 */
@Service
public class TokenService {

    private static final Logger logger = LoggerFactory.getLogger(TokenService.class);

    private final RedisTemplate<String, Object> redisTemplate;
    private final RedisScript<List> acquireTokenScript;
    private final String scriptContent;

    public TokenService(RedisTemplate<String, Object> redisTemplate) throws IOException {
        this.redisTemplate = redisTemplate;
        
        // Load Lua script from classpath
        ClassPathResource resource = new ClassPathResource("acquire_order_token.lua");
        this.scriptContent = new String(resource.getInputStream().readAllBytes(), StandardCharsets.UTF_8);
        
        // Initialize RedisScript
        this.acquireTokenScript = RedisScript.of(scriptContent, List.class);
        
        logger.info("TokenService initialized with Lua script loaded");
    }

    /**
     * Pre-allocate tokens for a campaign.
     * 
     * Tokens are distributed proportionally to SKU inventory ratios.
     */
    public int allocateCampaignTokens(String campaignId, String spuId, int totalLimit, 
                                  List<Map<String, Object>> skuInventories) {
        if (skuInventories.isEmpty()) {
            logger.warn("No SKUs found for SPU {}", spuId);
            return 0;
        }

        // Calculate total inventory across all SKUs
        int totalInventory = skuInventories.stream()
            .mapToInt(sku -> (Integer) sku.get("quantity"))
            .sum();

        if (totalInventory == 0) {
            logger.warn("No inventory available for SPU {}", spuId);
            return 0;
        }

        // Distribute tokens and create sorted set entries
        List<String> tokens = new ArrayList<>();
        int tokenIndex = 0;
        
        for (Map<String, Object> skuInv : skuInventories) {
            String skuId = (String) skuInv.get("id");
            int skuQuantity = (Integer) skuInv.get("quantity");
            
            // Proportional allocation
            int skuTokenCount = Math.min(
                skuQuantity,
                (int) (totalLimit * ((double) skuQuantity / totalInventory))
            );

            // Create tokens for this SKU
            for (int i = 0; i < skuTokenCount; i++) {
                String token = String.format("token_%s_%s", UUID.randomUUID(), skuId);
                tokens.add(token);
                
                // Cache SKU inventory in Redis (no TTL - inventory is source of truth in DB)
                String skuInventoryKey = String.format("sku:%s:inventory", skuId);
                redisTemplate.opsForValue().set(skuInventoryKey, skuQuantity);
                
                tokenIndex++;
            }

            logger.info("Allocated {} tokens for SKU {} (inventory: {})", 
                skuTokenCount, skuInv.get("sku_code"), skuQuantity);
        }

        // Store tokens in Redis sorted set
        String campaignTokensKey = String.format("campaign:%s:tokens", campaignId);
        for (int i = 0; i < tokens.size(); i++) {
            redisTemplate.opsForZSet().add(campaignTokensKey, tokens.get(i), (double) i);
        }

        // Set campaign metadata with 60-second TTL
        String metadataKey = String.format("campaign:%s:metadata", campaignId);
        Map<String, Object> metadata = Map.of(
            "total_tokens", totalLimit,
            "remaining_tokens", totalLimit,
            "status", "active"
        );
        redisTemplate.opsForValue().set(metadataKey, metadata, 60, TimeUnit.SECONDS);

        logger.info("Pre-allocated {} tokens for campaign {} (SPU: {}, limit: {})", 
            tokens.size(), campaignId, spuId, totalLimit);

        return tokens.size();
    }

    /**
     * Acquire a token atomically using Lua script.
     * 
     * The Lua script uses ZPOPMIN to pop the first available token from the
     * campaign's sorted set (FIFO ordering).
     */
    public Map<String, Object> acquireToken(String campaignId, String skuId, int quantity) {
        String campaignTokensKey = String.format("campaign:%s:tokens", campaignId);
        String skuInventoryKey = String.format("sku:%s:inventory", skuId);
        String metadataKey = String.format("campaign:%s:metadata", campaignId);

        List<String> keys = List.of(campaignTokensKey, skuInventoryKey, metadataKey);
        List<String> args = List.of(String.valueOf(quantity), campaignId);

        try {
            List<Object> result = redisTemplate.execute(
                acquireTokenScript,
                keys,
                args.toArray(new String[0])
            );

            if (result == null || result.isEmpty()) {
                return Map.of("err", "UNKNOWN_ERROR");
            }

            // Parse result from Lua script
            if (result.get(0) instanceof String && result.get(0).equals("ORDER_SUCCESS")) {
                return Map.of(
                    "ok", "ORDER_SUCCESS",
                    "remaining_stock", result.get(1),
                    "token", result.get(2)
                );
            } else {
                return Map.of("err", result.get(0));
            }
        } catch (Exception e) {
            logger.error("Token acquisition error: {}", e.getMessage(), e);
            return Map.of("err", "REDIS_ERROR", "message", e.getMessage());
        }
    }

    /**
     * Get remaining token count for a campaign.
     */
    public long getRemainingTokens(String campaignId) {
        String campaignTokensKey = String.format("campaign:%s:tokens", campaignId);
        Long count = redisTemplate.opsForZSet().size(campaignTokensKey);
        return count != null ? count : 0;
    }

    /**
     * Check if campaign has no remaining tokens (sold out).
     */
    public boolean isCampaignSoldOut(String campaignId) {
        return getRemainingTokens(campaignId) == 0;
    }
}