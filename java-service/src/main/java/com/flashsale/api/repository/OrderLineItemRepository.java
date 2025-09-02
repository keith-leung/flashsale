package com.flashsale.api.repository;

import com.flashsale.api.entity.OrderLineItem;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.UUID;

@Repository
public interface OrderLineItemRepository extends JpaRepository<OrderLineItem, UUID> {
    
    List<OrderLineItem> findByOrderId(UUID orderId);
}
