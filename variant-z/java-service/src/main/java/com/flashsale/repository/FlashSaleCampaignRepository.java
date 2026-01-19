package com.flashsale.repository;

import com.flashsale.entity.FlashSaleCampaign;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.Instant;
import java.util.Optional;

/**
 * Flash sale campaign repository - Variant Z.
 */
@Repository
public interface FlashSaleCampaignRepository extends JpaRepository<FlashSaleCampaign, String> {

    @Query("""
        SELECT c FROM FlashSaleCampaign c
        WHERE c.spuId = :spuId
        AND c.isActive = true
        AND c.status = 'active'
        AND c.startTime <= :now
        AND c.endTime >= :now
    """)
    Optional<FlashSaleCampaign> findBySPUAndActive(@Param("spuId") String spuId, @Param("now") Instant now);
}