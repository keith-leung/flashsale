package com.flashsale.api.repository;

import com.flashsale.api.entity.AllocationStatus;
import com.flashsale.api.entity.CampaignSkuAllocation;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.UUID;

@Repository
public interface CampaignSkuAllocationRepository extends JpaRepository<CampaignSkuAllocation, Long> {

    /**
     * Find all allocations claimed by a specific service instance
     */
    List<CampaignSkuAllocation> findByClaimedBy(String serviceId);

    /**
     * Find all allocations for a campaign
     */
    List<CampaignSkuAllocation> findByCampaignId(UUID campaignId);

    /**
     * Find allocations claimed by service for specific campaign
     */
    List<CampaignSkuAllocation> findByClaimedByAndCampaignId(String serviceId, UUID campaignId);

    /**
     * Count available units for campaign
     */
    @Query("SELECT COUNT(a) FROM CampaignSkuAllocation a WHERE a.campaignId = :campaignId AND a.status = :status")
    long countByCampaignIdAndStatus(@Param("campaignId") UUID campaignId, @Param("status") AllocationStatus status);

    /**
     * Claim available allocation units atomically
     * Returns the number of units successfully claimed
     */
    @Modifying
    @Query(value = "UPDATE campaign_sku_allocations " +
                   "SET claimed_by = :serviceId, claimed_at = NOW(), status = 'claimed' " +
                   "WHERE campaign_id = :campaignId AND status = 'available' " +
                   "ORDER BY id LIMIT :maxUnits",
           nativeQuery = true)
    int claimUnits(@Param("serviceId") String serviceId,
                   @Param("campaignId") String campaignId,
                   @Param("maxUnits") int maxUnits);
}
