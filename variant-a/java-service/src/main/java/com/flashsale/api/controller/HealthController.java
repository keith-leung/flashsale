package com.flashsale.api.controller;

import com.flashsale.api.service.CampaignMemoryAllocator;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestMethod;
import org.springframework.web.bind.annotation.RestController;

import java.math.BigDecimal;
import java.util.Collections;
import java.util.UUID;
import java.util.concurrent.locks.ReentrantLock;

/**
 * Health check endpoint for load balancer.
 */
@RestController
public class HealthController {

    private final CampaignMemoryAllocator allocator;
    
    // Benchmark constants
    private static final UUID BENCHMARK_CAMPAIGN_ID = UUID.fromString("00000000-0000-0000-0000-000000000001");
    private static final UUID BENCHMARK_SPU_ID = UUID.fromString("00000000-0000-0000-0000-000000000003");
    private static final UUID BENCHMARK_SKU_ID = UUID.fromString("00000000-0000-0000-0000-000000000002");
    
    private volatile boolean benchmarkLoaded = false;
    private final ReentrantLock benchmarkLock = new ReentrantLock();

    public HealthController(CampaignMemoryAllocator allocator) {
        this.allocator = allocator;
    }

    /**
     * Health check endpoint.
     * Returns plain text "200 OK" following BoA internal pattern.
     * Supports both GET and HEAD methods.
     */
    @RequestMapping(value = "/health", method = {RequestMethod.GET, RequestMethod.HEAD})
    public ResponseEntity<String> health() {
        return ResponseEntity.ok("200 OK");
    }

    /**
     * Benchmark endpoint to emulate Order creation (Fast Path only).
     * Emulates infinite inventory (10M items) to test raw allocation overhead without Redis I/O.
     */
    @RequestMapping(value = "/health2", method = RequestMethod.GET)
    public ResponseEntity<String> healthBenchmark() {
        // Lazy load benchmark campaign
        if (!benchmarkLoaded) {
            benchmarkLock.lock();
            try {
                if (!benchmarkLoaded) {
                    allocator.loadCampaign(
                        BENCHMARK_CAMPAIGN_ID,
                        BENCHMARK_SPU_ID,
                        Collections.singletonMap(BENCHMARK_SKU_ID, 10_000_000), // 10 Million items
                        new BigDecimal("100.00"),
                        new BigDecimal("200.00"),
                        20.0
                    );
                    benchmarkLoaded = true;
                }
            } finally {
                benchmarkLock.unlock();
            }
        }

        // Perform exactly one reservation (Fast Path simulation)
        CampaignMemoryAllocator.ReservationResult result = allocator.reserveItem(
            BENCHMARK_CAMPAIGN_ID,
            BENCHMARK_SKU_ID
        );

        if (result.success) {
            return ResponseEntity.ok("200 OK");
        } else {
            return ResponseEntity.internalServerError().body("Benchmark allocation failed: " + result.priceType);
        }
    }
}
