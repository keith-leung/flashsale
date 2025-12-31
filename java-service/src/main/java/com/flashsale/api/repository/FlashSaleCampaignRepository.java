package com.flashsale.api.repository;

import com.flashsale.api.entity.FlashSaleCampaign;
import com.flashsale.api.entity.FlashSaleStatus;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Repository
public interface FlashSaleCampaignRepository extends JpaRepository<FlashSaleCampaign, UUID> {

    Page<FlashSaleCampaign> findBySpuId(UUID spuId, Pageable pageable);

    @Query("SELECT f FROM FlashSaleCampaign f WHERE f.status = :status")
    Page<FlashSaleCampaign> findByStatus(@Param("status") FlashSaleStatus status, Pageable pageable);

    @Query("SELECT f FROM FlashSaleCampaign f WHERE f.isActive = true AND f.status IN ('SCHEDULED', 'ACTIVE')")
    List<FlashSaleCampaign> findActiveFlashSales();

    /**
     * Find currently active campaign for a given SPU
     * CRITICAL: Used for dual validation during order creation
     */
    @Query("SELECT f FROM FlashSaleCampaign f WHERE f.spuId = :spuId AND f.isActive = true AND f.status = 'ACTIVE' AND f.startTime <= :now AND f.endTime >= :now")
    Optional<FlashSaleCampaign> findActiveCampaignForSpu(@Param("spuId") UUID spuId, @Param("now") LocalDateTime now);

    @Query("SELECT f FROM FlashSaleCampaign f WHERE f.startTime <= :now AND f.endTime >= :now AND f.isActive = true")
    List<FlashSaleCampaign> findCurrentlyActiveFlashSales(@Param("now") LocalDateTime now);

    @Modifying
    @Query("UPDATE FlashSaleCampaign f SET f.soldQuantity = f.soldQuantity + :quantity WHERE f.id = :id")
    int incrementSoldQuantity(@Param("id") UUID id, @Param("quantity") Integer quantity);

    @Query("SELECT f FROM FlashSaleCampaign f JOIN FETCH f.spu s WHERE f.id = :id")
    FlashSaleCampaign findByIdWithSpu(@Param("id") UUID id);
}
