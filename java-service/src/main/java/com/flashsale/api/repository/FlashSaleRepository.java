package com.flashsale.api.repository;

import com.flashsale.api.entity.FlashSale;
import com.flashsale.api.entity.FlashSaleCampaignStatus;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Repository
public interface FlashSaleRepository extends JpaRepository<FlashSale, UUID> {

    List<FlashSale> findByStatus(FlashSaleCampaignStatus status);

    List<FlashSale> findBySpuId(UUID spuId);

    @Query("SELECT fs FROM FlashSale fs WHERE fs.status = :status " +
           "AND fs.startTime <= :now AND fs.endTime >= :now")
    List<FlashSale> findActiveByStatus(@Param("status") FlashSaleCampaignStatus status,
                                       @Param("now") LocalDateTime now);

    @Query("SELECT fs FROM FlashSale fs LEFT JOIN FETCH fs.spu WHERE fs.id = :id")
    Optional<FlashSale> findByIdWithSpu(@Param("id") UUID id);
}
