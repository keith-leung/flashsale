package com.flashsale.api.entity;

/**
 * Status of campaign SKU allocation units
 */
public enum AllocationStatus {
    available,  // Unit is available to be claimed
    claimed,    // Unit is claimed by a service instance
    depleted    // Unit is fully consumed
}
