package com.flashsale.repository;

import com.flashsale.entity.Order;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.Optional;

/**
 * Order repository - Variant Z.
 */
@Repository
public interface OrderRepository extends JpaRepository<Order, String> {
}