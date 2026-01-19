package com.flashsale;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.data.jpa.repository.config.EnableJpaAuditing;

/**
 * Flash Sale Microservice - Variant Z
 * Architecture: Token Pre-Allocation with Synchronous Database Persistence
 */
@SpringBootApplication
@EnableJpaAuditing
public class FlashSaleApplication {

    public static void main(String[] args) {
        SpringApplication.run(FlashSaleApplication.class, args);
    }
}