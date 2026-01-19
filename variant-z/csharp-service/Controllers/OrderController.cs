using FlashSale.DTOs;
using FlashSale.Services;
using Microsoft.AspNetCore.Mvc;

namespace FlashSale.Controllers;

[ApiController]
[Route("api/v1")]
public class OrderController : ControllerBase
{
    private readonly IOrderService _orderService;
    private readonly ILogger<OrderController> _logger;

    public OrderController(IOrderService orderService, ILogger<OrderController> logger)
    {
        _orderService = orderService;
        _logger = logger;
    }

    [HttpPost("orders")]
    [ProducesResponseType(typeof(OrderResponse), StatusCodes.Status201Created)]
    [ProducesResponseType(typeof(ErrorResponse), StatusCodes.Status400BadRequest)]
    public async Task<IActionResult> CreateOrder([FromBody] OrderRequest request)
    {
        try
        {
            var response = await _orderService.CreateOrderAsync(request);
            return CreatedAtAction(nameof(GetOrder), new { id = response.OrderId }, response);
        }
        catch (ArgumentException ex)
        {
            _logger.LogWarning(ex, "Invalid order request");
            return BadRequest(new ErrorResponse { Error = "INVALID_REQUEST", Message = ex.Message });
        }
        catch (InvalidOperationException ex)
        {
            _logger.LogWarning(ex, "Order creation failed: {Message}", ex.Message);
            return BadRequest(new ErrorResponse { Error = "ORDER_FAILED", Message = ex.Message });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Unexpected error creating order");
            return StatusCode(500, new ErrorResponse { Error = "INTERNAL_ERROR", Message = "An unexpected error occurred" });
        }
    }

    [HttpGet("orders/{id}")]
    [ProducesResponseType(typeof(OrderResponse), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<IActionResult> GetOrder(Guid id)
    {
        try
        {
            var order = await _orderService.GetOrderByIdAsync(id);
            if (order == null)
            {
                return NotFound();
            }

            var response = new OrderResponse
            {
                OrderId = order.Id,
                OrderNumber = order.OrderNumber,
                Status = order.Status,
                TotalAmount = order.TotalAmount,
                CustomerEmail = order.CustomerEmail
            };

            return Ok(response);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error retrieving order {OrderId}", id);
            return StatusCode(500, new ErrorResponse { Error = "INTERNAL_ERROR", Message = "An unexpected error occurred" });
        }
    }
}