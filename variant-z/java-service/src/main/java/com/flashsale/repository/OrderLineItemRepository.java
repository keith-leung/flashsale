package com.flashsale.repository;

import com.flashsale.entity.OrderLineItem;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

/**
 * Order line item repository - Variant Z.
 */
@Repository
public interface OrderLineItemRepository extends JpaRepository<OrderLineItem, String> {
}