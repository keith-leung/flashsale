package com.flashsale.repository;

import com.flashsale.entity.SKU;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.Optional;

/**
 * SKU repository - Variant Z.
 */
@Repository
public interface SKURepository extends JpaRepository<SKU, String> {

    @Query("SELECT s FROM SKU s LEFT JOIN FETCH s.inventory i WHERE s.id = :skuId AND s.isActive = true")
    Optional<SKU> findByIdWithInventory(@Param("skuId") String skuId);
}