using FlashSale.Api.DTOs;
using FlashSale.Api.Services;
using Microsoft.AspNetCore.Mvc;

namespace FlashSale.Api.Controllers;

[ApiController]
[Route("api/v1/[controller]")]
public class InventoryController : ControllerBase
{
    private readonly IInventoryService _inventoryService;
    private readonly ILogger<InventoryController> _logger;

    public InventoryController(IInventoryService inventoryService, ILogger<InventoryController> logger)
    {
        _inventoryService = inventoryService;
        _logger = logger;
    }

    /// <summary>
    /// Get all inventory records
    /// </summary>
    [HttpGet]
    public async Task<ActionResult<IEnumerable<InventoryResponseDto>>> GetInventory(
        [FromQuery] int skip = 0,
        [FromQuery] int take = 100,
        [FromQuery] long? skuId = null)
    {
        var inventory = await _inventoryService.GetAllAsync(skip, take, skuId);
        return Ok(inventory);
    }

    /// <summary>
    /// Get inventory by ID
    /// </summary>
    [HttpGet("{id}")]
    public async Task<ActionResult<InventoryResponseDto>> GetInventoryById(long id)
    {
        var inventory = await _inventoryService.GetByIdAsync(id);
        if (inventory == null)
            return NotFound();

        return Ok(inventory);
    }

    /// <summary>
    /// Get inventory by SKU ID
    /// </summary>
    [HttpGet("sku/{skuId}")]
    public async Task<ActionResult<InventoryResponseDto>> GetInventoryBySkuId(long skuId)
    {
        var inventory = await _inventoryService.GetBySkuIdAsync(skuId);
        if (inventory == null)
            return NotFound();

        return Ok(inventory);
    }

    /// <summary>
    /// Create new inventory record
    /// </summary>
    [HttpPost]
    public async Task<ActionResult<InventoryResponseDto>> CreateInventory(InventoryCreateDto dto)
    {
        try
        {
            var inventory = await _inventoryService.CreateAsync(dto);
            return CreatedAtAction(nameof(GetInventoryById), new { id = inventory.Id }, inventory);
        }
        catch (InvalidOperationException ex)
        {
            return BadRequest(ex.Message);
        }
    }

    /// <summary>
    /// Update inventory record
    /// </summary>
    [HttpPut("{id}")]
    public async Task<ActionResult<InventoryResponseDto>> UpdateInventory(long id, InventoryUpdateDto dto)
    {
        try
        {
            var inventory = await _inventoryService.UpdateAsync(id, dto);
            if (inventory == null)
                return NotFound();

            return Ok(inventory);
        }
        catch (InvalidOperationException ex)
        {
            return BadRequest(ex.Message);
        }
    }

    /// <summary>
    /// Delete inventory record
    /// </summary>
    [HttpDelete("{id}")]
    public async Task<IActionResult> DeleteInventory(long id)
    {
        var success = await _inventoryService.DeleteAsync(id);
        if (!success)
            return NotFound();

        return NoContent();
    }
}
