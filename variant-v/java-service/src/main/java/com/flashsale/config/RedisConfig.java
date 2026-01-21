package com.flashsale.config;

import org.redisson.Redisson;
import org.redisson.api.RedissonClient;
import org.redisson.config.Config;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.core.env.Environment;

import java.util.Arrays;
import java.util.List;

@Configuration
public class RedisConfig {
    
    @Bean
    public RedissonClient redissonClient(@Value("${redis.nodes[0]}") String firstNode) {
        Config config = new Config();
        
        // For Variant V, we use the first node as primary
        config.useSingleServer()
                .setAddress(firstNode);
        
        return Redisson.create(config);
    }
    
    @Bean
    public RedisManager redisManager(RedissonClient redissonClient, Environment env) {
        // Read all Redis nodes from configuration
        String[] nodes = env.getProperty("redis.nodes", String[].class, new String[0]);
        return new RedisManager(redissonClient, Arrays.asList(nodes));
    }
}
