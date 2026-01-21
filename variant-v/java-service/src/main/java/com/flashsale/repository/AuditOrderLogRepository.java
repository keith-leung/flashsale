package com.flashsale.repository;

import com.flashsale.entity.AuditOrderLog;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.time.LocalDateTime;
import java.util.List;

public interface AuditOrderLogRepository extends JpaRepository<AuditOrderLog, String> {
    
    @Query("SELECT a FROM AuditOrderLog a WHERE a.status = 'PENDING' AND a.createdAt < :cutoffTime")
    List<AuditOrderLog> findPendingAuditsOlderThan(@Param("cutoffTime") LocalDateTime cutoffTime);
    
    List<AuditOrderLog> findByOrderId(String orderId);
    
    List<AuditOrderLog> findByFlashSaleCampaignId(String campaignId);
}
