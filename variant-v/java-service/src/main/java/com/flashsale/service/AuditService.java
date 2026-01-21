package com.flashsale.service;

import com.flashsale.entity.AuditOrderLog;
import com.flashsale.repository.AuditOrderLogRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;


@Service
public class AuditService {
    
    @Autowired
    private AuditOrderLogRepository auditRepository;
    
    @Transactional
    public AuditOrderLog createAuditRecord(String customerEmail, String skuId, Integer quantity, 
                                         BigDecimal unitPrice, String flashSaleCampaignId) {
        AuditOrderLog audit = new AuditOrderLog();
        audit.setId(java.util.UUID.randomUUID().toString());
        audit.setOrderId(java.util.UUID.randomUUID().toString());
        audit.setCustomerEmail(customerEmail);
        audit.setSkuId(skuId);
        audit.setQuantity(quantity);
        audit.setUnitPrice(unitPrice);
        audit.setFlashSaleCampaignId(flashSaleCampaignId);
        audit.setStatus(AuditOrderLog.AuditStatus.PENDING);
        audit.setCreatedAt(LocalDateTime.now());
        
        return auditRepository.save(audit);
    }
    
    @Transactional
    public void confirmAudit(String auditId) {
        AuditOrderLog audit = auditRepository.findById(auditId)
            .orElseThrow(() -> new RuntimeException("Audit record not found: " + auditId));
        audit.setStatus(AuditOrderLog.AuditStatus.CONFIRMED);
        auditRepository.save(audit);
    }
    
    @Transactional
    public void failAudit(String auditId, String reason) {
        AuditOrderLog audit = auditRepository.findById(auditId)
            .orElseThrow(() -> new RuntimeException("Audit record not found: " + auditId));
        audit.setStatus(AuditOrderLog.AuditStatus.FAILED);
        auditRepository.save(audit);
    }
    
    @Transactional(readOnly = true)
    public List<AuditOrderLog> getPendingAudits(LocalDateTime cutoffTime) {
        return auditRepository.findPendingAuditsOlderThan(cutoffTime);
    }
    
    @Transactional(readOnly = true)
    public AuditOrderLog getAuditById(String auditId) {
        return auditRepository.findById(auditId)
            .orElseThrow(() -> new RuntimeException("Audit record not found: " + auditId));
    }
}
