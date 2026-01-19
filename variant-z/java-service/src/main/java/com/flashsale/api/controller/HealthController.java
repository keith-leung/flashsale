package com.flashsale.api.controller;

import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestMethod;
import org.springframework.web.bind.annotation.RestController;

/**
 * Health check controller for load balancer.
 *
 * Returns plain text '200 OK' following BoA internal pattern.
 * Supports both GET and HEAD methods.
 */
@RestController
public class HealthController {

    @RequestMapping(value = "/health", method = {RequestMethod.GET, RequestMethod.HEAD}, produces = MediaType.TEXT_PLAIN_VALUE)
    public ResponseEntity<String> healthCheck() {
        return ResponseEntity.ok("200 OK");
    }
}