using FlashSale.Api.Data;
using FlashSale.Api.DTOs;
using FlashSale.Api.Models;
using Microsoft.EntityFrameworkCore;

namespace FlashSale.Api.Services;

public class FlashSaleService : IFlashSaleService
{
    private readonly FlashSaleDbContext _context;

    public FlashSaleService(FlashSaleDbContext context)
    {
        _context = context;
    }

    public async Task<IEnumerable<FlashSaleEventResponseDto>> GetAllAsync(int skip = 0, int take = 100, FlashSaleStatus? status = null)
    {
        var query = _context.FlashSaleEvents.AsQueryable();

        if (status.HasValue)
        {
            query = query.Where(f => f.Status == status.Value);
        }

        var events = await query
            .OrderBy(f => f.StartTime)
            .Skip(skip)
            .Take(take)
            .ToListAsync();

        return events.Select(f => new FlashSaleEventResponseDto
        {
            Id = f.Id,
            Name = f.Name,
            Description = f.Description,
            SkuId = f.SkuId,
            TotalSaleLimit = f.TotalSaleLimit,
            SoldQuantity = f.SoldQuantity,
            RemainingQuantity = f.TotalSaleLimit - f.SoldQuantity,
            MaxQuantityPerCustomer = f.MaxQuantityPerCustomer,
            StartTime = f.StartTime,
            EndTime = f.EndTime,
            Status = f.Status,
            IsTimeActive = DateTime.UtcNow >= f.StartTime && DateTime.UtcNow <= f.EndTime,
            IsAvailable = f.IsActive && f.SoldQuantity < f.TotalSaleLimit && DateTime.UtcNow >= f.StartTime && DateTime.UtcNow <= f.EndTime,
            IsActive = f.IsActive,
            CreatedAt = f.CreatedAt,
            UpdatedAt = f.UpdatedAt
        });
    }

    public async Task<FlashSaleEventResponseDto?> GetByIdAsync(Guid id)
    {
        var flashSale = await _context.FlashSaleEvents.FindAsync(id);
        if (flashSale == null) return null;

        return new FlashSaleEventResponseDto
        {
            Id = flashSale.Id,
            Name = flashSale.Name,
            Description = flashSale.Description,
            SkuId = flashSale.SkuId,
            TotalSaleLimit = flashSale.TotalSaleLimit,
            SoldQuantity = flashSale.SoldQuantity,
            RemainingQuantity = flashSale.TotalSaleLimit - flashSale.SoldQuantity,
            MaxQuantityPerCustomer = flashSale.MaxQuantityPerCustomer,
            StartTime = flashSale.StartTime,
            EndTime = flashSale.EndTime,
            Status = flashSale.Status,
            IsTimeActive = DateTime.UtcNow >= flashSale.StartTime && DateTime.UtcNow <= flashSale.EndTime,
            IsAvailable = flashSale.IsActive && flashSale.SoldQuantity < flashSale.TotalSaleLimit && DateTime.UtcNow >= flashSale.StartTime && DateTime.UtcNow <= flashSale.EndTime,
            IsActive = flashSale.IsActive,
            CreatedAt = flashSale.CreatedAt,
            UpdatedAt = flashSale.UpdatedAt
        };
    }

    public Task<FlashSaleEventResponseDto> CreateAsync(FlashSaleEventCreateDto dto)
    {
        throw new NotImplementedException();
    }

    public Task<FlashSaleEventResponseDto?> UpdateAsync(Guid id, FlashSaleEventUpdateDto dto)
    {
        throw new NotImplementedException();
    }

    public Task<bool> DeleteAsync(Guid id)
    {
        throw new NotImplementedException();
    }

    public Task<PurchaseResponseDto> PurchaseAsync(Guid id, PurchaseRequestDto dto)
    {
        throw new NotImplementedException();
    }

    public Task UpdateFlashSaleStatusesAsync()
    {
        // Background task updates flash sale statuses based on current time
        return Task.CompletedTask;
    }
}
