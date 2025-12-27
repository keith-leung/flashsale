package com.flashsale.api.service;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.flashsale.api.entity.Sku;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Service;

import java.time.Duration;
import java.util.*;
import java.util.concurrent.TimeUnit;
import java.util.stream.Collectors;

/**
 * Redis cache service for SKU and inventory data.
 * Implements cache-aside pattern with batch prefetch capabilities.
 */
@Service
public class RedisCacheService {

    private static final Logger logger = LoggerFactory.getLogger(RedisCacheService.class);

    private static final String SKU_KEY_PREFIX = "sku:";
    private static final long SKU_TTL_SECONDS = 600; // 10 minutes
    private static final long INVENTORY_TTL_SECONDS = 60; // 1 minute

    private final RedisTemplate<String, String> redisTemplate;
    private final ObjectMapper objectMapper;

    @Autowired
    public RedisCacheService(RedisTemplate<String, String> redisTemplate, ObjectMapper objectMapper) {
        this.redisTemplate = redisTemplate;
        this.objectMapper = objectMapper;
    }

    /**
     * Get multiple SKUs from cache using Redis pipeline.
     * Returns a map of SKU ID to cached SKU data (or null if cache miss).
     */
    public Map<UUID, SkuCacheData> getMultiSku(List<UUID> skuIds) {
        if (skuIds == null || skuIds.isEmpty()) {
            return Collections.emptyMap();
        }

        try {
            // Use pipeline to fetch all SKUs in a single round-trip
            List<String> keys = skuIds.stream()
                    .map(id -> SKU_KEY_PREFIX + id.toString())
                    .collect(Collectors.toList());

            List<String> values = redisTemplate.opsForValue().multiGet(keys);

            Map<UUID, SkuCacheData> result = new HashMap<>();
            for (int i = 0; i < skuIds.size(); i++) {
                UUID skuId = skuIds.get(i);
                String value = (values != null && i < values.size()) ? values.get(i) : null;

                if (value != null) {
                    try {
                        SkuCacheData cacheData = objectMapper.readValue(value, SkuCacheData.class);
                        result.put(skuId, cacheData);
                    } catch (JsonProcessingException e) {
                        logger.warn("Failed to deserialize SKU cache data for ID {}: {}", skuId, e.getMessage());
                        result.put(skuId, null);
                    }
                } else {
                    result.put(skuId, null);
                }
            }

            long cacheHits = result.values().stream().filter(Objects::nonNull).count();
            long cacheMisses = skuIds.size() - cacheHits;
            logger.debug("Redis multi-get: {} hits, {} misses out of {} SKUs", cacheHits, cacheMisses, skuIds.size());

            return result;

        } catch (Exception e) {
            logger.error("Redis multi-get error: {}", e.getMessage(), e);
            return skuIds.stream().collect(Collectors.toMap(id -> id, id -> null));
        }
    }

    /**
     * Cache a single SKU with TTL.
     */
    public void setSku(UUID skuId, SkuCacheData skuData) {
        if (skuId == null || skuData == null) {
            return;
        }

        try {
            String key = SKU_KEY_PREFIX + skuId.toString();
            String value = objectMapper.writeValueAsString(skuData);
            redisTemplate.opsForValue().set(key, value, SKU_TTL_SECONDS, TimeUnit.SECONDS);
            logger.debug("Cached SKU {}: {}", skuId, skuData.skuCode);
        } catch (JsonProcessingException e) {
            logger.error("Failed to serialize SKU cache data for ID {}: {}", skuId, e.getMessage());
        } catch (Exception e) {
            logger.error("Redis set error for SKU {}: {}", skuId, e.getMessage());
        }
    }

    /**
     * Cache multiple SKUs in a batch operation.
     */
    public void setMultiSku(Map<UUID, SkuCacheData> skuDataMap) {
        if (skuDataMap == null || skuDataMap.isEmpty()) {
            return;
        }

        try {
            redisTemplate.executePipelined((org.springframework.data.redis.core.RedisCallback<Object>) connection -> {
                skuDataMap.forEach((skuId, skuData) -> {
                    try {
                        String key = SKU_KEY_PREFIX + skuId.toString();
                        String value = objectMapper.writeValueAsString(skuData);
                        connection.setEx(
                                key.getBytes(),
                                SKU_TTL_SECONDS,
                                value.getBytes()
                        );
                    } catch (JsonProcessingException e) {
                        logger.error("Failed to serialize SKU cache data for ID {}: {}", skuId, e.getMessage());
                    }
                });
                return null;
            });
            logger.debug("Cached {} SKUs in batch", skuDataMap.size());
        } catch (Exception e) {
            logger.error("Redis multi-set error: {}", e.getMessage(), e);
        }
    }

    /**
     * Invalidate SKU cache.
     */
    public void invalidateSku(UUID skuId) {
        if (skuId == null) {
            return;
        }

        try {
            String key = SKU_KEY_PREFIX + skuId.toString();
            redisTemplate.delete(key);
            logger.debug("Invalidated cache for SKU {}", skuId);
        } catch (Exception e) {
            logger.error("Redis delete error for SKU {}: {}", skuId, e.getMessage());
        }
    }

    /**
     * Cache data structure for SKU.
     */
    public static class SkuCacheData {
        public UUID id;
        public String skuCode;
        public String name;
        public java.math.BigDecimal price;
        public Boolean trackInventory;
        public String spuName;
        public Integer availableQuantity;
        public Integer reservedQuantity;

        public SkuCacheData() {}

        public static SkuCacheData fromSku(Sku sku) {
            SkuCacheData data = new SkuCacheData();
            data.id = sku.getId();
            data.skuCode = sku.getSkuCode();
            data.name = sku.getName();
            data.price = sku.getPrice();
            data.trackInventory = sku.getTrackInventory();

            if (sku.getSpu() != null) {
                data.spuName = sku.getSpu().getName();
            }

            if (sku.getInventory() != null) {
                data.availableQuantity = sku.getInventory().getAvailableQuantity();
                data.reservedQuantity = sku.getInventory().getReservedQuantity();
            }

            return data;
        }
    }
}
