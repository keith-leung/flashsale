using FlashSale.Api.Data;
using FlashSale.Api.DTOs;
using Microsoft.EntityFrameworkCore;

namespace FlashSale.Api.Services;

public class SkuService : ISkuService
{
    private readonly FlashSaleDbContext _context;

    public SkuService(FlashSaleDbContext context)
    {
        _context = context;
    }

    public async Task<IEnumerable<SkuResponseDto>> GetAllAsync(int skip = 0, int take = 100, Guid? spuId = null)
    {
        var query = _context.Skus.AsQueryable();

        if (spuId.HasValue)
        {
            query = query.Where(s => s.SpuId == spuId.Value);
        }

        var skus = await query
            .OrderBy(s => s.CreatedAt)
            .Skip(skip)
            .Take(take)
            .Select(s => new SkuResponseDto
            {
                Id = s.Id,
                SpuId = s.SpuId,
                SkuCode = s.SkuCode,
                Name = s.Name,
                Price = s.Price,
                CostPrice = s.CostPrice,
                Weight = s.Weight,
                TrackInventory = s.TrackInventory,
                IsActive = s.IsActive,
                CreatedAt = s.CreatedAt,
                UpdatedAt = s.UpdatedAt
            })
            .ToListAsync();

        return skus;
    }

    public async Task<SkuResponseDto?> GetByIdAsync(Guid id)
    {
        var sku = await _context.Skus.FindAsync(id);
        if (sku == null) return null;

        return new SkuResponseDto
        {
            Id = sku.Id,
            SpuId = sku.SpuId,
            SkuCode = sku.SkuCode,
            Name = sku.Name,
            Price = sku.Price,
            CostPrice = sku.CostPrice,
            Weight = sku.Weight,
            TrackInventory = sku.TrackInventory,
            IsActive = sku.IsActive,
            CreatedAt = sku.CreatedAt,
            UpdatedAt = sku.UpdatedAt
        };
    }

    public Task<SkuResponseDto> CreateAsync(SkuCreateDto dto)
    {
        throw new NotImplementedException();
    }

    public Task<SkuResponseDto?> UpdateAsync(Guid id, SkuUpdateDto dto)
    {
        throw new NotImplementedException();
    }

    public Task<bool> DeleteAsync(Guid id)
    {
        throw new NotImplementedException();
    }
}
