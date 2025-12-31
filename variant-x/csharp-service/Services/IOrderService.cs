using FlashSale.Api.DTOs;

namespace FlashSale.Api.Services;

public interface IOrderService
{
    Task<IEnumerable<OrderResponseDto>> GetAllAsync(int skip = 0, int take = 100, string? customerEmail = null);
    Task<OrderResponseDto?> GetByIdAsync(Guid id);
    Task<OrderResponseDto> CreateAsync(OrderCreateDto dto);
    Task<OrderResponseDto?> UpdateStatusAsync(Guid id, string status);
    Task<bool> CancelAsync(Guid id);
    Task<PaymentResponseDto> CreatePaymentAsync(Guid orderId, PaymentCreateDto dto);
}
