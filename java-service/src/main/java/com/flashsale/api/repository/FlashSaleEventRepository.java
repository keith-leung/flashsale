package com.flashsale.api.repository;

import com.flashsale.api.entity.FlashSaleEvent;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.LocalDateTime;
import java.util.List;
import java.util.UUID;

@Repository
public interface FlashSaleEventRepository extends JpaRepository<FlashSaleEvent, UUID> {
    
    Page<FlashSaleEvent> findBySkuId(UUID skuId, Pageable pageable);
    
    @Query("SELECT f FROM FlashSaleEvent f WHERE f.status = :status")
    Page<FlashSaleEvent> findByStatus(@Param("status") String status, Pageable pageable);
    
    @Query("SELECT f FROM FlashSaleEvent f WHERE f.isActive = true AND f.status IN ('scheduled', 'active')")
    List<FlashSaleEvent> findActiveFlashSales();
    
    @Query("SELECT f FROM FlashSaleEvent f WHERE f.startTime <= :now AND f.endTime >= :now AND f.isActive = true")
    List<FlashSaleEvent> findCurrentlyActiveFlashSales(@Param("now") LocalDateTime now);
    
    @Modifying
    @Query("UPDATE FlashSaleEvent f SET f.soldQuantity = f.soldQuantity + :quantity WHERE f.id = :id")
    int incrementSoldQuantity(@Param("id") UUID id, @Param("quantity") Integer quantity);
    
    @Query("SELECT f FROM FlashSaleEvent f JOIN FETCH f.sku s LEFT JOIN FETCH s.inventory WHERE f.id = :id")
    FlashSaleEvent findByIdWithSkuAndInventory(@Param("id") UUID id);
}
