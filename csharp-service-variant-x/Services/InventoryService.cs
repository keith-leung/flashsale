using FlashSale.Api.Data;
using FlashSale.Api.DTOs;
using Microsoft.EntityFrameworkCore;

namespace FlashSale.Api.Services;

public class InventoryService : IInventoryService
{
    private readonly FlashSaleDbContext _context;

    public InventoryService(FlashSaleDbContext context)
    {
        _context = context;
    }

    public async Task<InventoryResponseDto?> GetBySkuIdAsync(Guid skuId)
    {
        var inventory = await _context.Inventories
            .FirstOrDefaultAsync(i => i.SkuId == skuId);

        if (inventory == null) return null;

        return new InventoryResponseDto
        {
            Id = inventory.Id,
            SkuId = inventory.SkuId,
            Quantity = inventory.Quantity,
            ReservedQuantity = inventory.ReservedQuantity,
            AvailableQuantity = inventory.Quantity - inventory.ReservedQuantity,
            AllowNegativeStock = inventory.AllowNegativeStock,
            CreatedAt = inventory.CreatedAt,
            UpdatedAt = inventory.UpdatedAt
        };
    }

    public async Task<InventoryResponseDto?> UpdateAsync(Guid skuId, InventoryUpdateDto dto)
    {
        var inventory = await _context.Inventories
            .FirstOrDefaultAsync(i => i.SkuId == skuId);

        if (inventory == null) return null;

        if (dto.Quantity.HasValue)
        {
            inventory.Quantity = dto.Quantity.Value;
        }

        if (dto.AllowNegativeStock.HasValue)
        {
            inventory.AllowNegativeStock = dto.AllowNegativeStock.Value;
        }

        inventory.UpdatedAt = DateTime.UtcNow;
        await _context.SaveChangesAsync();

        return new InventoryResponseDto
        {
            Id = inventory.Id,
            SkuId = inventory.SkuId,
            Quantity = inventory.Quantity,
            ReservedQuantity = inventory.ReservedQuantity,
            AvailableQuantity = inventory.Quantity - inventory.ReservedQuantity,
            AllowNegativeStock = inventory.AllowNegativeStock,
            CreatedAt = inventory.CreatedAt,
            UpdatedAt = inventory.UpdatedAt
        };
    }

    public async Task<InventoryResponseDto?> AdjustAsync(Guid skuId, InventoryAdjustmentDto dto)
    {
        var inventory = await _context.Inventories
            .FirstOrDefaultAsync(i => i.SkuId == skuId);

        if (inventory == null) return null;

        inventory.Quantity += dto.Adjustment;
        inventory.UpdatedAt = DateTime.UtcNow;
        await _context.SaveChangesAsync();

        return new InventoryResponseDto
        {
            Id = inventory.Id,
            SkuId = inventory.SkuId,
            Quantity = inventory.Quantity,
            ReservedQuantity = inventory.ReservedQuantity,
            AvailableQuantity = inventory.Quantity - inventory.ReservedQuantity,
            AllowNegativeStock = inventory.AllowNegativeStock,
            CreatedAt = inventory.CreatedAt,
            UpdatedAt = inventory.UpdatedAt
        };
    }

    public async Task<InventoryResponseDto?> ReserveAsync(Guid skuId, int quantity)
    {
        var inventory = await _context.Inventories
            .FirstOrDefaultAsync(i => i.SkuId == skuId);

        if (inventory == null) return null;

        inventory.ReservedQuantity += quantity;
        inventory.UpdatedAt = DateTime.UtcNow;
        await _context.SaveChangesAsync();

        return new InventoryResponseDto
        {
            Id = inventory.Id,
            SkuId = inventory.SkuId,
            Quantity = inventory.Quantity,
            ReservedQuantity = inventory.ReservedQuantity,
            AvailableQuantity = inventory.Quantity - inventory.ReservedQuantity,
            AllowNegativeStock = inventory.AllowNegativeStock,
            CreatedAt = inventory.CreatedAt,
            UpdatedAt = inventory.UpdatedAt
        };
    }

    public async Task<InventoryResponseDto?> ReleaseAsync(Guid skuId, int quantity)
    {
        var inventory = await _context.Inventories
            .FirstOrDefaultAsync(i => i.SkuId == skuId);

        if (inventory == null) return null;

        inventory.ReservedQuantity -= quantity;
        if (inventory.ReservedQuantity < 0)
        {
            inventory.ReservedQuantity = 0;
        }
        inventory.UpdatedAt = DateTime.UtcNow;
        await _context.SaveChangesAsync();

        return new InventoryResponseDto
        {
            Id = inventory.Id,
            SkuId = inventory.SkuId,
            Quantity = inventory.Quantity,
            ReservedQuantity = inventory.ReservedQuantity,
            AvailableQuantity = inventory.Quantity - inventory.ReservedQuantity,
            AllowNegativeStock = inventory.AllowNegativeStock,
            CreatedAt = inventory.CreatedAt,
            UpdatedAt = inventory.UpdatedAt
        };
    }
}
