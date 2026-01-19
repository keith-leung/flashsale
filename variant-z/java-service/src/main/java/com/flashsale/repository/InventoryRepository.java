package com.flashsale.repository;

import com.flashsale.entity.Inventory;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

/**
 * Inventory repository - Variant Z.
 */
@Repository
public interface InventoryRepository extends JpaRepository<Inventory, String> {
}