using FlashSale.Api.DTOs;
using FlashSale.Api.Services;
using FlashSale.Api.Models;
using Microsoft.AspNetCore.Mvc;

namespace FlashSale.Api.Controllers;

[ApiController]
[Route("api/v1/[controller]")]
public class FlashSalesController : ControllerBase
{
    private readonly IFlashSaleService _flashSaleService;
    private readonly ILogger<FlashSalesController> _logger;

    public FlashSalesController(IFlashSaleService flashSaleService, ILogger<FlashSalesController> logger)
    {
        _flashSaleService = flashSaleService;
        _logger = logger;
    }

    /// <summary>
    /// Get all flash sales
    /// </summary>
    [HttpGet]
    public async Task<ActionResult<IEnumerable<FlashSaleEventResponseDto>>> GetFlashSales(
        [FromQuery] int skip = 0,
        [FromQuery] int take = 100,
        [FromQuery] FlashSaleStatus? status = null)
    {
        var flashSales = await _flashSaleService.GetAllAsync(skip, take, status);
        return Ok(flashSales);
    }

    /// <summary>
    /// Get flash sale by ID
    /// </summary>
    [HttpGet("{id}")]
    public async Task<ActionResult<FlashSaleEventResponseDto>> GetFlashSale(Guid id)
    {
        var flashSale = await _flashSaleService.GetByIdAsync(id);
        if (flashSale == null)
            return NotFound();

        return Ok(flashSale);
    }

    /// <summary>
    /// Create a new flash sale
    /// </summary>
    [HttpPost]
    public async Task<ActionResult<FlashSaleEventResponseDto>> CreateFlashSale(FlashSaleEventCreateDto dto)
    {
        try
        {
            var flashSale = await _flashSaleService.CreateAsync(dto);
            return CreatedAtAction(nameof(GetFlashSale), new { id = flashSale.Id }, flashSale);
        }
        catch (InvalidOperationException ex)
        {
            return BadRequest(ex.Message);
        }
    }

    /// <summary>
    /// Update an existing flash sale
    /// </summary>
    [HttpPut("{id}")]
    public async Task<ActionResult<FlashSaleEventResponseDto>> UpdateFlashSale(Guid id, FlashSaleEventUpdateDto dto)
    {
        try
        {
            var flashSale = await _flashSaleService.UpdateAsync(id, dto);
            if (flashSale == null)
                return NotFound();

            return Ok(flashSale);
        }
        catch (InvalidOperationException ex)
        {
            return BadRequest(ex.Message);
        }
    }

    /// <summary>
    /// Delete a flash sale
    /// </summary>
    [HttpDelete("{id}")]
    public async Task<IActionResult> DeleteFlashSale(Guid id)
    {
        var success = await _flashSaleService.DeleteAsync(id);
        if (!success)
            return NotFound();

        return NoContent();
    }

    /// <summary>
    /// Purchase items from a flash sale
    /// </summary>
    [HttpPost("{id}/purchase")]
    public async Task<ActionResult<PurchaseResponseDto>> Purchase(Guid id, PurchaseRequestDto dto)
    {
        try
        {
            var result = await _flashSaleService.PurchaseAsync(id, dto);
            return Ok(result);
        }
        catch (InvalidOperationException ex)
        {
            return BadRequest(ex.Message);
        }
    }
}
