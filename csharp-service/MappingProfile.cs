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
        CreateMap<FlashSaleEventCreateDto, FlashSaleEvent>();
        CreateMap<FlashSaleEventUpdateDto, FlashSaleEvent>()
            .ForAllMembers(opts => opts.Condition((src, dest, srcMember) => srcMember != null));
        CreateMap<FlashSaleEvent, FlashSaleEventResponseDto>();

        // Inventory mappings
        CreateMap<InventoryUpdateDto, Inventory>()
            .ForAllMembers(opts => opts.Condition((src, dest, srcMember) => srcMember != null));
        CreateMap<Inventory, InventoryResponseDto>();
    }
}
