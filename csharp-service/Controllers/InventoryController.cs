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
    /// Get inventory by SKU ID
    /// </summary>
    [HttpGet("sku/{skuId}")]
    public async Task<ActionResult<InventoryResponseDto>> GetInventoryBySkuId(Guid skuId)
    {
        var inventory = await _inventoryService.GetBySkuIdAsync(skuId);
        if (inventory == null)
            return NotFound();

        return Ok(inventory);
    }

    /// <summary>
    /// Update inventory for a SKU
    /// </summary>
    [HttpPut("sku/{skuId}")]
    public async Task<ActionResult<InventoryResponseDto>> UpdateInventory(Guid skuId, InventoryUpdateDto dto)
    {
        try
        {
            var inventory = await _inventoryService.UpdateAsync(skuId, dto);
            if (inventory == null)
                return NotFound();

            return Ok(inventory);
        }
        catch (InvalidOperationException ex)
        {
            return BadRequest(ex.Message);
        }
    }

}
