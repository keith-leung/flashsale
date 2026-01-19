package com.flashsale.repository;

import com.flashsale.entity.Payment;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

/**
 * Payment repository - Variant Z.
 */
@Repository
public interface PaymentRepository extends JpaRepository<Payment, String> {
}