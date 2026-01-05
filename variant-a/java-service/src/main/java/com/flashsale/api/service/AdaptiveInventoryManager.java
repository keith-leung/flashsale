package com.flashsale.api.service;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.core.io.ClassPathResource;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.data.redis.core.script.DefaultRedisScript;
import org.springframework.scripting.support.ResourceScriptSource;
import org.springframework.stereotype.Service;

import jakarta.annotation.PostConstruct;
import java.io.IOException;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Manages adaptive inventory services for multiple SKUs
 * Singleton pattern - one instance per application
 */
@Service
public class AdaptiveInventoryManager {

    private static final Logger logger = LoggerFactory.getLogger(AdaptiveInventoryManager.class);

    private final RedisTemplate<String, Object> redisTemplate;
    private DefaultRedisScript<Long> luaScript;
    private final Map<String, AdaptiveInventoryService> services = new ConcurrentHashMap<>();

    @Autowired
    public AdaptiveInventoryManager(RedisTemplate<String, Object> redisTemplate) {
        this.redisTemplate = redisTemplate;
    }

    /**
     * Initialize and load Lua script into Redis
     */
    @PostConstruct
    public void initialize() {
        try {
            luaScript = new DefaultRedisScript<>();
            luaScript.setResultType(Long.class);

            // Load Lua script from classpath
            ClassPathResource scriptResource = new ClassPathResource("lua/inventory_refill.lua");
            ResourceScriptSource scriptSource = new ResourceScriptSource(scriptResource);
            luaScript.setScriptSource(scriptSource);

            // Load script content to get SHA (for logging)
            String scriptContent = scriptSource.getScriptAsString();
            String sha = redisTemplate.execute((org.springframework.data.redis.core.RedisCallback<String>) connection ->
                new String(connection.scriptingCommands().scriptLoad(scriptContent.getBytes()))
            );

            logger.info("AdaptiveInventoryManager initialized");
            logger.info("  Lua Script SHA: {}", sha);
        } catch (IOException e) {
            logger.error("Failed to load Lua script", e);
            throw new RuntimeException("Failed to initialize AdaptiveInventoryManager", e);
        }
    }

    /**
     * Get or create adaptive inventory service for a SKU
     *
     * @param campaignId Campaign ID
     * @param skuId SKU ID
     * @return AdaptiveInventoryService instance for this SKU
     */
    public AdaptiveInventoryService getService(String campaignId, String skuId) {
        if (luaScript == null) {
            throw new IllegalStateException("AdaptiveInventoryManager not initialized");
        }

        String serviceKey = campaignId + ":" + skuId;

        return services.computeIfAbsent(serviceKey, key -> {
            logger.debug("Creating new AdaptiveInventoryService for {}", serviceKey);
            return new AdaptiveInventoryService(
                campaignId,
                skuId,
                redisTemplate,
                luaScript
            );
        });
    }

    /**
     * Get metrics for all active services
     */
    public Map<String, Map<String, Object>> getAllMetrics() {
        Map<String, Map<String, Object>> metrics = new HashMap<>();

        for (Map.Entry<String, AdaptiveInventoryService> entry : services.entrySet()) {
            AdaptiveInventoryService service = entry.getValue();
            AdaptiveInventoryService.InventoryMetrics m = service.getMetrics();

            Map<String, Object> serviceMetrics = new HashMap<>();
            serviceMetrics.put("batch_mode_requests", m.batchModeRequests);
            serviceMetrics.put("direct_mode_requests", m.directModeRequests);
            serviceMetrics.put("total_redis_calls", m.totalRedisCalls);
            serviceMetrics.put("mode_switched", m.modeSwitched);
            serviceMetrics.put("current_mode", service.getCurrentMode());

            metrics.put(entry.getKey(), serviceMetrics);
        }

        return metrics;
    }

    /**
     * Get count of active services
     */
    public int getServiceCount() {
        return services.size();
    }
}
