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

    @Query(value = "SELECT * FROM flash_sale_campaigns WHERE status = :status AND is_active = 1 " +
                   "AND CHAR_LENGTH(id) = 36 AND id REGEXP '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$' " +
                   "AND CHAR_LENGTH(spu_id) = 36 AND spu_id REGEXP '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'",
           nativeQuery = true)
    List<FlashSale> findActiveWithValidUUIDs(@Param("status") String status);
}
