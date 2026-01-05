using FlashSale.Api.DTOs;

namespace FlashSale.Api.Services;

public interface ISkuService
{
    Task<IEnumerable<SkuResponseDto>> GetAllAsync(int skip = 0, int take = 100, Guid? spuId = null);
    Task<SkuResponseDto?> GetByIdAsync(Guid id);
    Task<SkuResponseDto> CreateAsync(SkuCreateDto dto);
    Task<SkuResponseDto?> UpdateAsync(Guid id, SkuUpdateDto dto);
    Task<bool> DeleteAsync(Guid id);
}
