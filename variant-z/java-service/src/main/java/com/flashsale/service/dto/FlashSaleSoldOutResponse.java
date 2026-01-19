package com.flashsale.service.dto;

import java.time.Instant;

/**
 * Flash sale sold out response DTO.
 */
public class FlashSaleSoldOutResponse {

    private String campaignId;
    private String soldOutAt;
    private String message = "Flash sale campaign is sold out";

    public FlashSaleSoldOutResponse() {}

    public FlashSaleSoldOutResponse(String campaignId, String soldOutAt) {
        this.campaignId = campaignId;
        this.soldOutAt = soldOutAt;
    }

    // Getters and Setters
    public String getCampaignId() {
        return campaignId;
    }

    public void setCampaignId(String campaignId) {
        this.campaignId = campaignId;
    }

    public String getSoldOutAt() {
        return soldOutAt;
    }

    public void setSoldOutAt(String soldOutAt) {
        this.soldOutAt = soldOutAt;
    }

    public String getMessage() {
        return message;
    }

    public void setMessage(String message) {
        this.message = message;
    }
}