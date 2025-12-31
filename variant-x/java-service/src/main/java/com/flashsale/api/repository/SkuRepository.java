package com.flashsale.api.repository;

import com.flashsale.api.entity.Sku;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.Optional;
import java.util.UUID;

@Repository
public interface SkuRepository extends JpaRepository<Sku, UUID> {
    
    Optional<Sku> findBySkuCode(String skuCode);
    
    boolean existsBySkuCode(String skuCode);
    
    Page<Sku> findBySpuId(UUID spuId, Pageable pageable);
    
    @Query("SELECT s FROM Sku s WHERE s.isActive = :isActive")
    Page<Sku> findByIsActive(@Param("isActive") Boolean isActive, Pageable pageable);
    
    @Query("SELECT s FROM Sku s JOIN FETCH s.inventory WHERE s.id = :id")
    Optional<Sku> findByIdWithInventory(@Param("id") UUID id);

    @Query("SELECT s FROM Sku s LEFT JOIN FETCH s.inventory LEFT JOIN FETCH s.spu WHERE s.id = :id")
    Optional<Sku> findByIdWithInventoryAndSpu(@Param("id") UUID id);

    @Query("SELECT s FROM Sku s LEFT JOIN FETCH s.inventory")
    Page<Sku> findAllWithInventory(Pageable pageable);
}
