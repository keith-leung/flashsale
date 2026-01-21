using FlashSale.Api.V.Data;
using FlashSale.Api.V.Models;
using Microsoft.EntityFrameworkCore;

namespace FlashSale.Api.V.Services;

public class AuditService
{
    private readonly FlashSaleDbContext _context;
    private readonly IConfiguration _config;
    private readonly ILogger<AuditService> _logger;
    
    public AuditService(FlashSaleDbContext context, IConfiguration config, ILogger<AuditService> logger)
    {
        _context = context;
        _config = config;
        _logger = logger;
    }
    
    public async Task<AuditOrderLog> CreateAuditRecordAsync(string customerEmail, string skuId, int quantity, decimal unitPrice, string? flashSaleCampaignId)
    {
        try
        {
            var audit = new AuditOrderLog
            {
                Id = Guid.NewGuid(),
                OrderId = Guid.NewGuid(),
                CustomerEmail = customerEmail,
                SkuId = Guid.Parse(skuId),
                Quantity = quantity,
                UnitPrice = unitPrice,
                FlashSaleCampaignId = flashSaleCampaignId != null ? Guid.Parse(flashSaleCampaignId) : null,
                Status = AuditStatus.PENDING
            };
            
            _context.AuditOrderLogs.Add(audit);
            await _context.SaveChangesAsync();
            
            return audit;
        }
        catch (DbUpdateException ex)
        {
            _logger.LogError(ex, "Failed to create audit record. Inner exception: {Inner}", ex.InnerException?.Message);
            _logger.LogError(ex, "Stack trace: {Stack}", ex.StackTrace);
            throw;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Unexpected error creating audit record: {Message}", ex.Message);
            throw;
        }
    }
    
    public async Task ConfirmAuditAsync(Guid auditId)
    {
        var audit = await _context.AuditOrderLogs.FindAsync(auditId);
        if (audit == null)
            throw new KeyNotFoundException($"Audit record not found: {auditId}");
            
        audit.Status = AuditStatus.CONFIRMED;
        audit.UpdatedAt = DateTime.UtcNow;
        await _context.SaveChangesAsync();
    }
    
    public async Task FailAuditAsync(Guid auditId, string reason)
    {
        var audit = await _context.AuditOrderLogs.FindAsync(auditId);
        if (audit == null)
            throw new KeyNotFoundException($"Audit record not found: {auditId}");
            
        audit.Status = AuditStatus.FAILED;
        audit.UpdatedAt = DateTime.UtcNow;
        await _context.SaveChangesAsync();
    }
    
    public async Task<List<AuditOrderLog>> GetPendingAuditsAsync(DateTime cutoffTime)
    {
        return await _context.AuditOrderLogs
            .Where(a => a.Status == AuditStatus.PENDING && a.CreatedAt < cutoffTime)
            .ToListAsync();
    }
    
    public async Task<AuditOrderLog> GetAuditByIdAsync(Guid auditId)
    {
        var audit = await _context.AuditOrderLogs.FindAsync(auditId);
        if (audit == null)
            throw new KeyNotFoundException($"Audit record not found: {auditId}");
        
        return audit;
    }
    
    public async Task<AuditOrderLog> GetAuditByIdAsync(string auditId)
    {
        var audit = await _context.AuditOrderLogs.FindAsync(Guid.Parse(auditId));
        if (audit == null)
            throw new KeyNotFoundException($"Audit record not found: {auditId}");
        
        return audit;
    }
}
