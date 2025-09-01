using FlashSale.Api.DTOs;
using FlashSale.Api.Models;

namespace FlashSale.Api.Services;

public interface IFlashSaleService
{
    Task<IEnumerable<FlashSaleEventResponseDto>> GetAllAsync(int skip = 0, int take = 100, FlashSaleStatus? status = null);
    Task<FlashSaleEventResponseDto?> GetByIdAsync(Guid id);
    Task<FlashSaleEventResponseDto> CreateAsync(FlashSaleEventCreateDto dto);
    Task<FlashSaleEventResponseDto?> UpdateAsync(Guid id, FlashSaleEventUpdateDto dto);
    Task<bool> DeleteAsync(Guid id);
    Task<PurchaseResponseDto> PurchaseAsync(Guid id, PurchaseRequestDto dto);
    Task UpdateFlashSaleStatusesAsync();
}
