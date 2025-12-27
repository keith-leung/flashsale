using FlashSale.Api.DTOs;
using FlashSale.Api.Services;
using Microsoft.AspNetCore.Mvc;

namespace FlashSale.Api.Controllers;

[ApiController]
[Route("api/v1/[controller]")]
public class SkusController : ControllerBase
{
    private readonly ISkuService _skuService;
    private readonly ILogger<SkusController> _logger;

    public SkusController(ISkuService skuService, ILogger<SkusController> logger)
    {
        _skuService = skuService;
        _logger = logger;
    }

    /// <summary>
    /// Get all SKUs
    /// </summary>
    [HttpGet]
    public async Task<ActionResult<IEnumerable<SkuResponseDto>>> GetSkus(
        [FromQuery] int skip = 0,
        [FromQuery] int take = 100,
        [FromQuery] Guid? spuId = null)
    {
        var skus = await _skuService.GetAllAsync(skip, take, spuId);
        return Ok(skus);
    }

    /// <summary>
    /// Get SKU by ID
    /// </summary>
    [HttpGet("{id}")]
    public async Task<ActionResult<SkuResponseDto>> GetSku(Guid id)
    {
        var sku = await _skuService.GetByIdAsync(id);
        if (sku == null)
            return NotFound();

        return Ok(sku);
    }

    /// <summary>
    /// Create a new SKU
    /// </summary>
    [HttpPost]
    public async Task<ActionResult<SkuResponseDto>> CreateSku(SkuCreateDto dto)
    {
        try
        {
            var sku = await _skuService.CreateAsync(dto);
            return CreatedAtAction(nameof(GetSku), new { id = sku.Id }, sku);
        }
        catch (InvalidOperationException ex)
        {
            return BadRequest(ex.Message);
        }
    }

    /// <summary>
    /// Update an existing SKU
    /// </summary>
    [HttpPut("{id}")]
    public async Task<ActionResult<SkuResponseDto>> UpdateSku(Guid id, SkuUpdateDto dto)
    {
        try
        {
            var sku = await _skuService.UpdateAsync(id, dto);
            if (sku == null)
                return NotFound();

            return Ok(sku);
        }
        catch (InvalidOperationException ex)
        {
            return BadRequest(ex.Message);
        }
    }

    /// <summary>
    /// Delete a SKU
    /// </summary>
    [HttpDelete("{id}")]
    public async Task<IActionResult> DeleteSku(Guid id)
    {
        var success = await _skuService.DeleteAsync(id);
        if (!success)
            return NotFound();

        return NoContent();
    }
}
