using AutoMapper;
using FlashSale.Api.DTOs;
using FlashSale.Api.Models;

namespace FlashSale.Api;

public class MappingProfile : Profile
{
    public MappingProfile()
    {
        // SPU mappings
        CreateMap<SpuCreateDto, Spu>();
        CreateMap<SpuUpdateDto, Spu>()
            .ForAllMembers(opts => opts.Condition((src, dest, srcMember) => srcMember != null));
        CreateMap<Spu, SpuResponseDto>();

        // SKU mappings
        CreateMap<SkuCreateDto, Sku>()
            .ForMember(dest => dest.Inventory, opt => opt.Ignore());
        CreateMap<SkuUpdateDto, Sku>()
            .ForAllMembers(opts => opts.Condition((src, dest, srcMember) => srcMember != null));
        CreateMap<Sku, SkuResponseDto>()
            .ForMember(dest => dest.AvailableQuantity, opt => opt.MapFrom(src => src.Inventory != null ? src.Inventory.AvailableQuantity : (int?)null));

        // Flash Sale mappings
        CreateMap<FlashSaleEventCreateDto, FlashSaleCampaign>();
        CreateMap<FlashSaleEventUpdateDto, FlashSaleCampaign>()
            .ForAllMembers(opts => opts.Condition((src, dest, srcMember) => srcMember != null));
        CreateMap<FlashSaleCampaign, FlashSaleEventResponseDto>();

        // Inventory mappings
        CreateMap<InventoryUpdateDto, Inventory>()
            .ForAllMembers(opts => opts.Condition((src, dest, srcMember) => srcMember != null));
        CreateMap<Inventory, InventoryResponseDto>();

        // Order mappings
        CreateMap<OrderCreateDto, Order>()
            .ForMember(dest => dest.LineItems, opt => opt.Ignore());
        CreateMap<OrderUpdateDto, Order>()
            .ForAllMembers(opts => opts.Condition((src, dest, srcMember) => srcMember != null));
        CreateMap<Order, OrderResponseDto>();

        // Order Line Item mappings
        CreateMap<OrderLineItemCreateDto, OrderLineItem>();
        CreateMap<OrderLineItem, OrderLineItemResponseDto>();

        // Payment mappings
        CreateMap<PaymentCreateDto, Payment>();
        CreateMap<Payment, PaymentResponseDto>();
    }
}
