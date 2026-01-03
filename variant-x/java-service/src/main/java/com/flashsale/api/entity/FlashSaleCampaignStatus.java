package com.flashsale.api.entity;

/**
 * Status of a Flash Sale Campaign
 * CRITICAL: Must match SACRED VERIFICATION schema exactly
 */
public enum FlashSaleCampaignStatus {
    scheduled,  // Campaign scheduled but not started
    active,     // Campaign is currently active
    ended,      // Campaign ended (time expired or manually ended)
    cancelled   // Campaign cancelled
}
