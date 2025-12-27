using FlashSale.Api.DTOs;

namespace FlashSale.Api.Services;

public interface IInventoryService
{
    Task<InventoryResponseDto?> GetBySkuIdAsync(Guid skuId);
    Task<InventoryResponseDto?> UpdateAsync(Guid skuId, InventoryUpdateDto dto);
    Task<InventoryResponseDto?> AdjustAsync(Guid skuId, InventoryAdjustmentDto dto);
    Task<InventoryResponseDto?> ReserveAsync(Guid skuId, int quantity);
    Task<InventoryResponseDto?> ReleaseAsync(Guid skuId, int quantity);
}
