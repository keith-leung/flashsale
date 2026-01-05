using System.ComponentModel.DataAnnotations;

namespace FlashSale.Api.DTOs;

public class SkuCreateDto
{
    [Required]
    [StringLength(255, MinimumLength = 1)]
    public string SkuCode { get; set; } = string.Empty;
    
    [StringLength(255)]
    public string? Name { get; set; }
    
    [Required]
    public Guid SpuId { get; set; }
    
    [Required]
    [Range(0.01, double.MaxValue)]
    public decimal Price { get; set; }
    
    [Range(0, double.MaxValue)]
    public decimal? CostPrice { get; set; }
    
    [Range(0, double.MaxValue)]
    public decimal? Weight { get; set; }
    
    public bool TrackInventory { get; set; } = true;
    
    public bool IsActive { get; set; } = true;
    
    [Range(0, int.MaxValue)]
    public int InitialQuantity { get; set; } = 0;
}

public class SkuUpdateDto
{
    [StringLength(255, MinimumLength = 1)]
    public string? SkuCode { get; set; }
    
    [StringLength(255)]
    public string? Name { get; set; }
    
    [Range(0.01, double.MaxValue)]
    public decimal? Price { get; set; }
    
    [Range(0, double.MaxValue)]
    public decimal? CostPrice { get; set; }
    
    [Range(0, double.MaxValue)]
    public decimal? Weight { get; set; }
    
    public bool? TrackInventory { get; set; }
    
    public bool? IsActive { get; set; }
}

public class SkuResponseDto
{
    public Guid Id { get; set; }
    public string SkuCode { get; set; } = string.Empty;
    public string? Name { get; set; }
    public Guid SpuId { get; set; }
    public decimal Price { get; set; }
    public decimal? CostPrice { get; set; }
    public decimal? Weight { get; set; }
    public bool TrackInventory { get; set; }
    public bool IsActive { get; set; }
    public DateTime CreatedAt { get; set; }
    public DateTime UpdatedAt { get; set; }
    public int? AvailableQuantity { get; set; }
}
