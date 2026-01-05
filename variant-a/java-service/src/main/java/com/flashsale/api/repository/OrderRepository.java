package com.flashsale.api.repository;

import com.flashsale.api.entity.Order;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.Optional;
import java.util.UUID;

@Repository
public interface OrderRepository extends JpaRepository<Order, UUID> {
    
    Optional<Order> findByOrderNumber(String orderNumber);
    
    @Query("SELECT o FROM Order o LEFT JOIN FETCH o.lineItems WHERE o.id = :id")
    Optional<Order> findByIdWithLineItems(@Param("id") UUID id);
    
    @Query("SELECT o FROM Order o WHERE (:customerEmail IS NULL OR o.customerEmail LIKE %:customerEmail%)")
    Page<Order> findAllWithFilter(@Param("customerEmail") String customerEmail, Pageable pageable);
}
