package com.flashsale.api.service;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.flashsale.api.entity.Sku;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Service;

import java.io.Serializable;
import java.math.BigDecimal;
import java.util.*;
import java.util.concurrent.TimeUnit;
import java.util.stream.Collectors;

@Service
public class RedisCacheService {

    private static final Logger logger = LoggerFactory.getLogger(RedisCacheService.class);
    private static final String SKU_KEY_PREFIX = "sku:";
    private static final String SKU_META_PREFIX = "sku:";
    private static final String CAMPAIGN_LIMIT_PREFIX = "fs:";
    private static final String CAMPAIGN_META_PREFIX = "fs:";
    private static final String INVENTORY_PREFIX = "inv:";
    private static final String ORDER_QUEUE = "order_queue";
    private static final long SKU_TTL_MINUTES = 10;

    private final RedisTemplate<String, Object> redisTemplate;
    private final ObjectMapper objectMapper;

    @Autowired
    public RedisCacheService(RedisTemplate<String, Object> redisTemplate, ObjectMapper objectMapper) {
        this.redisTemplate = redisTemplate;
        this.objectMapper = objectMapper;
    }

    /**
     * Batch fetch SKUs from Redis using pipelining (implicit in multiGet)
     */
    public Map<UUID, SkuCacheData> getMultiSku(List<UUID> skuIds) {
        if (skuIds == null || skuIds.isEmpty()) {
            return Collections.emptyMap();
        }

        List<String> keys = skuIds.stream()
                .map(id -> SKU_KEY_PREFIX + id.toString())
                .collect(Collectors.toList());

        List<Object> results = redisTemplate.opsForValue().multiGet(keys);
        
        Map<UUID, SkuCacheData> resultMap = new HashMap<>();
        
        if (results != null) {
            for (int i = 0; i < skuIds.size(); i++) {
                Object result = results.get(i);
                if (result != null) {
                    try {
                        SkuCacheData data;
                        if (result instanceof SkuCacheData) {
                            data = (SkuCacheData) result;
                        } else {
                            // Handle case where Redis returns LinkedHashMap or String (depending on serializer)
                            data = objectMapper.convertValue(result, SkuCacheData.class);
                        }
                        resultMap.put(skuIds.get(i), data);
                    } catch (Exception e) {
                        logger.error("Error deserializing SKU cache data for ID: {}", skuIds.get(i), e);
                    }
                }
            }
        }
        
        return resultMap;
    }

    public void setMultiSku(Map<UUID, SkuCacheData> dataMap) {
        if (dataMap == null || dataMap.isEmpty()) {
            return;
        }

        Map<String, SkuCacheData> batchMap = new HashMap<>();
        dataMap.forEach((id, data) -> batchMap.put(SKU_KEY_PREFIX + id.toString(), data));
        
        redisTemplate.opsForValue().multiSet(batchMap);
        
        // Set TTLs individually (Redis multiSet doesn't support TTL)
        batchMap.keySet().forEach(key -> 
            redisTemplate.expire(key, SKU_TTL_MINUTES, TimeUnit.MINUTES)
        );
    }
    
    public void setSku(UUID skuId, SkuCacheData data) {
        String key = SKU_KEY_PREFIX + skuId.toString();
        redisTemplate.opsForValue().set(key, data, SKU_TTL_MINUTES, TimeUnit.MINUTES);
    }

    public void invalidateSku(UUID skuId) {
        redisTemplate.delete(SKU_KEY_PREFIX + skuId.toString());
    }

    // ============ Flash Sale Campaign Methods ============

    /**
     * Get campaign limit remaining (atomic read)
     */
    public Long getCampaignLimit(UUID campaignId) {
        String key = CAMPAIGN_LIMIT_PREFIX + campaignId.toString() + ":limit";
        Object value = redisTemplate.opsForValue().get(key);
        if (value == null) return null;
        return Long.valueOf(value.toString());
    }

    /**
     * Get campaign metadata
     */
    public Map<String, String> getCampaignMeta(UUID campaignId) {
        String key = CAMPAIGN_META_PREFIX + campaignId.toString() + ":meta";
        Map<Object, Object> entries = redisTemplate.opsForHash().entries(key);

        if (entries == null || entries.isEmpty()) {
            return null;
        }

        Map<String, String> result = new HashMap<>();
        entries.forEach((k, v) -> result.put(k.toString(), v != null ? v.toString() : null));
        return result;
    }

    /**
     * Set campaign metadata
     */
    public void setCampaignMeta(UUID campaignId, Map<String, String> meta) {
        String key = CAMPAIGN_META_PREFIX + campaignId.toString() + ":meta";
        Map<String, Object> hashMap = new HashMap<>(meta);
        redisTemplate.opsForHash().putAll(key, hashMap);
    }

    /**
     * Set campaign limit
     */
    public void setCampaignLimit(UUID campaignId, long limit) {
        String key = CAMPAIGN_LIMIT_PREFIX + campaignId.toString() + ":limit";
        redisTemplate.opsForValue().set(key, limit);
    }

    /**
     * Atomically reserve inventory from campaign limit (DECR)
     * Returns new value after decrement
     */
    public Long reserveCampaignInventory(UUID campaignId, int quantity) {
        String key = CAMPAIGN_LIMIT_PREFIX + campaignId.toString() + ":limit";
        return redisTemplate.opsForValue().decrement(key, quantity);
    }

    /**
     * Release campaign inventory (rollback)
     */
    public Long releaseCampaignInventory(UUID campaignId, int quantity) {
        String key = CAMPAIGN_LIMIT_PREFIX + campaignId.toString() + ":limit";
        return redisTemplate.opsForValue().increment(key, quantity);
    }

    /**
     * Get SKU inventory level
     */
    public Long getSkuInventory(UUID skuId) {
        String key = INVENTORY_PREFIX + skuId.toString();
        Object value = redisTemplate.opsForValue().get(key);
        if (value == null) return null;
        return Long.valueOf(value.toString());
    }

    /**
     * Set SKU inventory level
     */
    public void setSkuInventory(UUID skuId, long quantity) {
        String key = INVENTORY_PREFIX + skuId.toString();
        redisTemplate.opsForValue().set(key, quantity);
    }

    /**
     * Atomically reserve SKU inventory (DECR)
     */
    public Long reserveSkuInventory(UUID skuId, int quantity) {
        String key = INVENTORY_PREFIX + skuId.toString();
        return redisTemplate.opsForValue().decrement(key, quantity);
    }

    /**
     * Release SKU inventory (rollback)
     */
    public Long releaseSkuInventory(UUID skuId, int quantity) {
        String key = INVENTORY_PREFIX + skuId.toString();
        return redisTemplate.opsForValue().increment(key, quantity);
    }

    /**
     * Get SKU metadata from Redis hash
     */
    public Map<String, String> getSkuMeta(UUID skuId) {
        String key = SKU_META_PREFIX + skuId.toString() + ":meta";
        Map<Object, Object> entries = redisTemplate.opsForHash().entries(key);

        if (entries == null || entries.isEmpty()) {
            return null;
        }

        Map<String, String> result = new HashMap<>();
        entries.forEach((k, v) -> result.put(k.toString(), v != null ? v.toString() : null));
        return result;
    }

    /**
     * Set SKU metadata
     */
    public void setSkuMeta(UUID skuId, Map<String, String> meta) {
        String key = SKU_META_PREFIX + skuId.toString() + ":meta";
        Map<String, Object> hashMap = new HashMap<>(meta);
        redisTemplate.opsForHash().putAll(key, hashMap);
    }

    /**
     * Queue order for async batch processing
     */
    public void queueOrder(Map<String, Object> orderData) {
        try {
            String jsonData = objectMapper.writeValueAsString(orderData);
            Map<String, String> streamData = new HashMap<>();
            streamData.put("order_data", jsonData);

            redisTemplate.opsForStream().add(ORDER_QUEUE, streamData);
            logger.debug("Order queued to Redis stream: {}", ORDER_QUEUE);
        } catch (Exception e) {
            logger.error("Failed to queue order to Redis stream", e);
            throw new RuntimeException("Failed to queue order", e);
        }
    }

    /**
     * Get the underlying RedisTemplate instance
     * Used by adaptive inventory for direct Redis operations
     */
    public RedisTemplate<String, Object> getRedisTemplate() {
        return redisTemplate;
    }

    /**
     * Cache DTO optimized for serialization
     */
    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class SkuCacheData implements Serializable {
        private UUID id;
        private String skuCode;
        private BigDecimal price;
        private Integer quantity;
        private Integer reservedQuantity;
        private Boolean allowNegativeStock;
        private String spuName;
        private Boolean isActive;
        private Boolean trackInventory;
        
        public SkuCacheData() {}

        public static SkuCacheData fromEntity(Sku sku) {
            SkuCacheData data = new SkuCacheData();
            data.setId(sku.getId());
            data.setSkuCode(sku.getSkuCode());
            data.setPrice(sku.getPrice());
            data.setIsActive(sku.getIsActive());
            data.setTrackInventory(sku.getTrackInventory());
            
            if (sku.getInventory() != null) {
                data.setQuantity(sku.getInventory().getQuantity());
                data.setReservedQuantity(sku.getInventory().getReservedQuantity());
                data.setAllowNegativeStock(sku.getInventory().getAllowNegativeStock());
            } else {
                data.setQuantity(0);
                data.setReservedQuantity(0);
                data.setAllowNegativeStock(false);
            }
            
            if (sku.getSpu() != null) {
                data.setSpuName(sku.getSpu().getName());
            }
            
            return data;
        }

        public UUID getId() { return id; }
        public void setId(UUID id) { this.id = id; }
        
        public String getSkuCode() { return skuCode; }
        public void setSkuCode(String skuCode) { this.skuCode = skuCode; }
        
        public BigDecimal getPrice() { return price; }
        public void setPrice(BigDecimal price) { this.price = price; }
        
        public Integer getQuantity() { return quantity; }
        public void setQuantity(Integer quantity) { this.quantity = quantity; }
        
        public Integer getReservedQuantity() { return reservedQuantity; }
        public void setReservedQuantity(Integer reservedQuantity) { this.reservedQuantity = reservedQuantity; }
        
        public Boolean getAllowNegativeStock() { return allowNegativeStock; }
        public void setAllowNegativeStock(Boolean allowNegativeStock) { this.allowNegativeStock = allowNegativeStock; }
        
        public String getSpuName() { return spuName; }
        public void setSpuName(String spuName) { this.spuName = spuName; }

        public Boolean getIsActive() { return isActive; }
        public void setIsActive(Boolean isActive) { this.isActive = isActive; }

        public Boolean getTrackInventory() { return trackInventory; }
        public void setTrackInventory(Boolean trackInventory) { this.trackInventory = trackInventory; }
    }
}
