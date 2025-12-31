using AutoMapper;
using FlashSale.Api.Data;
using FlashSale.Api.DTOs;
using FlashSale.Api.Models;
using Microsoft.EntityFrameworkCore;

namespace FlashSale.Api.Services;

public class SpuService : ISpuService
{
    private readonly FlashSaleDbContext _context;
    private readonly IMapper _mapper;
    private readonly ILogger<SpuService> _logger;

    public SpuService(FlashSaleDbContext context, IMapper mapper, ILogger<SpuService> logger)
    {
        _context = context;
        _mapper = mapper;
        _logger = logger;
    }

    public async Task<IEnumerable<SpuResponseDto>> GetAllAsync(int skip = 0, int take = 100)
    {
        var spus = await _context.Spus
            .OrderByDescending(s => s.CreatedAt)
            .Skip(skip)
            .Take(take)
            .ToListAsync();

        return _mapper.Map<IEnumerable<SpuResponseDto>>(spus);
    }

    public async Task<SpuResponseDto?> GetByIdAsync(Guid id)
    {
        var spu = await _context.Spus.FindAsync(id);
        return spu == null ? null : _mapper.Map<SpuResponseDto>(spu);
    }

    public async Task<SpuResponseDto> CreateAsync(SpuCreateDto dto)
    {
        // Check if slug already exists
        if (await _context.Spus.AnyAsync(s => s.Slug == dto.Slug))
        {
            throw new InvalidOperationException("SPU with this slug already exists");
        }

        var spu = _mapper.Map<Spu>(dto);
        _context.Spus.Add(spu);
        await _context.SaveChangesAsync();

        _logger.LogInformation("Created SPU {SpuId} with name {Name}", spu.Id, spu.Name);
        
        return _mapper.Map<SpuResponseDto>(spu);
    }

    public async Task<SpuResponseDto?> UpdateAsync(Guid id, SpuUpdateDto dto)
    {
        var spu = await _context.Spus.FindAsync(id);
        if (spu == null) return null;

        // Check slug uniqueness if being updated
        if (!string.IsNullOrEmpty(dto.Slug) && dto.Slug != spu.Slug)
        {
            if (await _context.Spus.AnyAsync(s => s.Slug == dto.Slug))
            {
                throw new InvalidOperationException("SPU with this slug already exists");
            }
        }

        _mapper.Map(dto, spu);
        await _context.SaveChangesAsync();

        _logger.LogInformation("Updated SPU {SpuId}", spu.Id);
        
        return _mapper.Map<SpuResponseDto>(spu);
    }

    public async Task<bool> DeleteAsync(Guid id)
    {
        var spu = await _context.Spus.FindAsync(id);
        if (spu == null) return false;

        _context.Spus.Remove(spu);
        await _context.SaveChangesAsync();

        _logger.LogInformation("Deleted SPU {SpuId}", id);
        
        return true;
    }
}
