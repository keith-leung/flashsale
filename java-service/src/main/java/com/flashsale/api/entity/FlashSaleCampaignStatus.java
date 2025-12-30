package com.flashsale.api.entity;

/**
 * Status of a Flash Sale Campaign
 */
public enum FlashSaleCampaignStatus {
    pending,    // Campaign scheduled but not started
    active,     // Campaign is currently active
    sold_out,   // Campaign sold all units
    ended       // Campaign ended (time expired or manually ended)
}
