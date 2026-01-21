package com.flashsale.config;

import org.redisson.api.RedissonClient;

import java.security.MessageDigest;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

public class RedisManager {
    private final RedissonClient primaryClient;
    private final List<String> nodes;
    private final Map<Integer, RedissonClient> nodeClients = new ConcurrentHashMap<>();
    
    public RedisManager(RedissonClient primaryClient, List<String> nodes) {
        this.primaryClient = primaryClient;
        this.nodes = nodes;
    }
    
    public RedissonClient getClientForSku(String skuId) {
        int nodeIndex = getNodeIndexForSku(skuId);
        return getClientForNode(nodeIndex);
    }
    
    private RedissonClient getClientForNode(int nodeIndex) {
        return nodeClients.computeIfAbsent(nodeIndex, idx -> primaryClient);
    }
    
    public int getNodeIndexForSku(String skuId) {
        try {
            MessageDigest md = MessageDigest.getInstance("MD5");
            byte[] hash = md.digest(skuId.getBytes());
            int hashValue = 0;
            for (int i = 0; i < 4; i++) {
                hashValue = (hashValue << 8) | (hash[i] & 0xFF);
            }
            return Math.abs(hashValue) % nodes.size();
        } catch (Exception e) {
            return 0;
        }
    }
    
    public RedissonClient getPrimaryClient() {
        return primaryClient;
    }
}
