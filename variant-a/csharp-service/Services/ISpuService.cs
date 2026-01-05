using FlashSale.Api.DTOs;

namespace FlashSale.Api.Services;

public interface ISpuService
{
    Task<IEnumerable<SpuResponseDto>> GetAllAsync(int skip = 0, int take = 100);
    Task<SpuResponseDto?> GetByIdAsync(Guid id);
    Task<SpuResponseDto> CreateAsync(SpuCreateDto dto);
    Task<SpuResponseDto?> UpdateAsync(Guid id, SpuUpdateDto dto);
    Task<bool> DeleteAsync(Guid id);
}
