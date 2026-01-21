package com.flashsale.service;

import com.flashsale.config.RedisManager;
import org.redisson.api.RLock;
import org.redisson.api.RedissonClient;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.concurrent.TimeUnit;

@Service
public class DistributedLockService {
    
    @Autowired
    private RedisManager redisManager;
    
    @Value("${lock.ttl:100}")
    private long lockTtlMs;
    
    @Value("${lock.timeout:50}")
    private long lockTimeoutMs;
    
    public LockGuard acquireLock(String skuId) throws InterruptedException {
        return acquireLock(Collections.singletonList(skuId));
    }
    
    public LockGuard acquireLock(List<String> skuIds) throws InterruptedException {
        List<RLock> locks = new ArrayList<>();
        List<RedissonClient> clients = new ArrayList<>();
        
        try {
            for (String skuId : skuIds) {
                RedissonClient client = redisManager.getClientForSku(skuId);
                RLock lock = client.getLock("lock:order:" + skuId);
                
                boolean acquired = lock.tryLock(lockTimeoutMs, lockTtlMs, TimeUnit.MILLISECONDS);
                if (!acquired) {
                    releaseLocks(locks);
                    throw new RuntimeException("Failed to acquire lock for SKU: " + skuId);
                }
                
                locks.add(lock);
                clients.add(client);
            }
            
            return new LockGuard(locks, clients);
        } catch (Exception e) {
            releaseLocks(locks);
            throw e;
        }
    }
    
    private void releaseLocks(List<RLock> locks) {
        for (RLock lock : locks) {
            try {
                if (lock.isHeldByCurrentThread()) {
                    lock.unlock();
                }
            } catch (Exception e) {
                // Ignore unlock errors
            }
        }
    }
    
    public static class LockGuard implements AutoCloseable {
        private final List<RLock> locks;
        private final List<RedissonClient> clients;
        
        public LockGuard(List<RLock> locks, List<RedissonClient> clients) {
            this.locks = locks;
            this.clients = clients;
        }
        
        @Override
        public void close() {
            for (RLock lock : locks) {
                try {
                    if (lock.isHeldByCurrentThread()) {
                        lock.unlock();
                    }
                } catch (Exception e) {
                    // Ignore unlock errors
                }
            }
        }
    }
}
