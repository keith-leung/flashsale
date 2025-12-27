package com.flashsale.api.controller;

import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestMethod;
import org.springframework.web.bind.annotation.RestController;

/**
 * Health check endpoint for load balancer.
 */
@RestController
public class HealthController {

    /**
     * Health check endpoint.
     * Returns plain text "200 OK" following BoA internal pattern.
     * Supports both GET and HEAD methods.
     */
    @RequestMapping(value = "/health", method = {RequestMethod.GET, RequestMethod.HEAD})
    public ResponseEntity<String> health() {
        return ResponseEntity.ok("200 OK");
    }
}
