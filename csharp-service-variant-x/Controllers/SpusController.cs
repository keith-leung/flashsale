using FlashSale.Api.DTOs;
using FlashSale.Api.Services;
using Microsoft.AspNetCore.Mvc;

namespace FlashSale.Api.Controllers;

[ApiController]
[Route("api/v1/[controller]")]
public class SpusController : ControllerBase
{
    private readonly ISpuService _spuService;
    private readonly ILogger<SpusController> _logger;

    public SpusController(ISpuService spuService, ILogger<SpusController> logger)
    {
        _spuService = spuService;
        _logger = logger;
    }

    /// <summary>
    /// Get all SPUs
    /// </summary>
    [HttpGet]
    public async Task<ActionResult<IEnumerable<SpuResponseDto>>> GetSpus(
        [FromQuery] int skip = 0,
        [FromQuery] int take = 100)
    {
        var spus = await _spuService.GetAllAsync(skip, take);
        return Ok(spus);
    }

    /// <summary>
    /// Get SPU by ID
    /// </summary>
    [HttpGet("{id}")]
    public async Task<ActionResult<SpuResponseDto>> GetSpu(Guid id)
    {
        var spu = await _spuService.GetByIdAsync(id);
        if (spu == null)
            return NotFound();

        return Ok(spu);
    }

    /// <summary>
    /// Create a new SPU
    /// </summary>
    [HttpPost]
    public async Task<ActionResult<SpuResponseDto>> CreateSpu(SpuCreateDto dto)
    {
        try
        {
            var spu = await _spuService.CreateAsync(dto);
            return CreatedAtAction(nameof(GetSpu), new { id = spu.Id }, spu);
        }
        catch (InvalidOperationException ex)
        {
            return BadRequest(ex.Message);
        }
    }

    /// <summary>
    /// Update an existing SPU
    /// </summary>
    [HttpPut("{id}")]
    public async Task<ActionResult<SpuResponseDto>> UpdateSpu(Guid id, SpuUpdateDto dto)
    {
        try
        {
            var spu = await _spuService.UpdateAsync(id, dto);
            if (spu == null)
                return NotFound();

            return Ok(spu);
        }
        catch (InvalidOperationException ex)
        {
            return BadRequest(ex.Message);
        }
    }

    /// <summary>
    /// Delete an SPU
    /// </summary>
    [HttpDelete("{id}")]
    public async Task<IActionResult> DeleteSpu(Guid id)
    {
        var success = await _spuService.DeleteAsync(id);
        if (!success)
            return NotFound();

        return NoContent();
    }
}
