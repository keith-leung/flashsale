package com.flashsale.api.repository;

import com.flashsale.api.entity.Inventory;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.Optional;
import java.util.UUID;

@Repository
public interface InventoryRepository extends JpaRepository<Inventory, UUID> {
    
    Optional<Inventory> findBySkuId(UUID skuId);
    
    boolean existsBySkuId(UUID skuId);
    
    @Modifying
    @Query("UPDATE Inventory i SET i.quantity = i.quantity + :adjustment WHERE i.skuId = :skuId")
    int adjustQuantity(@Param("skuId") UUID skuId, @Param("adjustment") Integer adjustment);
    
    @Modifying
    @Query("UPDATE Inventory i SET i.reservedQuantity = i.reservedQuantity + :quantity WHERE i.skuId = :skuId")
    int reserveQuantity(@Param("skuId") UUID skuId, @Param("quantity") Integer quantity);
    
    @Modifying
    @Query("UPDATE Inventory i SET i.reservedQuantity = i.reservedQuantity - :quantity WHERE i.skuId = :skuId AND i.reservedQuantity >= :quantity")
    int releaseQuantity(@Param("skuId") UUID skuId, @Param("quantity") Integer quantity);
}
