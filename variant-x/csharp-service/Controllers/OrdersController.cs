using FlashSale.Api.DTOs;
using FlashSale.Api.Services;
using Microsoft.AspNetCore.Mvc;

namespace FlashSale.Api.Controllers;

[ApiController]
[Route("api/v1/[controller]")]
public class OrdersController : ControllerBase
{
    private readonly IOrderService _orderService;
    private readonly ILogger<OrdersController> _logger;

    public OrdersController(IOrderService orderService, ILogger<OrdersController> logger)
    {
        _orderService = orderService;
        _logger = logger;
    }

    /// <summary>
    /// Get all orders
    /// </summary>
    [HttpGet]
    public async Task<ActionResult<IEnumerable<OrderResponseDto>>> GetOrders(
        [FromQuery] int skip = 0,
        [FromQuery] int take = 100,
        [FromQuery] string? customerEmail = null)
    {
        var orders = await _orderService.GetAllAsync(skip, take, customerEmail);
        return Ok(orders);
    }

    /// <summary>
    /// Get order by ID
    /// </summary>
    [HttpGet("{id}")]
    public async Task<ActionResult<OrderResponseDto>> GetOrder(Guid id)
    {
        var order = await _orderService.GetByIdAsync(id);
        if (order == null)
            return NotFound();

        return Ok(order);
    }

    /// <summary>
    /// Create a new order
    /// </summary>
    [HttpPost]
    public async Task<ActionResult<OrderResponseDto>> CreateOrder(OrderCreateDto dto)
    {
        try
        {
            var order = await _orderService.CreateAsync(dto);
            return CreatedAtAction(nameof(GetOrder), new { id = order.Id }, order);
        }
        catch (InvalidOperationException ex)
        {
            return BadRequest(ex.Message);
        }
    }

    /// <summary>
    /// Update order status
    /// </summary>
    [HttpPut("{id}/status")]
    public async Task<ActionResult<OrderResponseDto>> UpdateOrderStatus(Guid id, [FromBody] string status)
    {
        try
        {
            var order = await _orderService.UpdateStatusAsync(id, status);
            if (order == null)
                return NotFound();

            return Ok(order);
        }
        catch (InvalidOperationException ex)
        {
            return BadRequest(ex.Message);
        }
    }

    /// <summary>
    /// Cancel an order
    /// </summary>
    [HttpDelete("{id}")]
    public async Task<IActionResult> CancelOrder(Guid id)
    {
        var success = await _orderService.CancelAsync(id);
        if (!success)
            return NotFound();

        return NoContent();
    }

    /// <summary>
    /// Create a payment for an order
    /// </summary>
    [HttpPost("{orderId}/payments")]
    public async Task<ActionResult<PaymentResponseDto>> CreatePayment(Guid orderId, PaymentCreateDto dto)
    {
        try
        {
            var payment = await _orderService.CreatePaymentAsync(orderId, dto);
            return CreatedAtAction(nameof(GetOrder), new { id = orderId }, payment);
        }
        catch (InvalidOperationException ex)
        {
            return BadRequest(ex.Message);
        }
    }
}
