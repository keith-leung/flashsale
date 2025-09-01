using System.ComponentModel.DataAnnotations;

namespace FlashSale.Api.DTOs;

public class SpuCreateDto
{
    [Required]
    [StringLength(250, MinimumLength = 1)]
    public string Name { get; set; } = string.Empty;
    
    [Required]
    [StringLength(255, MinimumLength = 1)]
    public string Slug { get; set; } = string.Empty;
    
    public string? Description { get; set; }
    
    public bool IsActive { get; set; } = true;
}

public class SpuUpdateDto
{
    [StringLength(250, MinimumLength = 1)]
    public string? Name { get; set; }
    
    [StringLength(255, MinimumLength = 1)]
    public string? Slug { get; set; }
    
    public string? Description { get; set; }
    
    public bool? IsActive { get; set; }
}

public class SpuResponseDto
{
    public Guid Id { get; set; }
    public string Name { get; set; } = string.Empty;
    public string Slug { get; set; } = string.Empty;
    public string? Description { get; set; }
    public bool IsActive { get; set; }
    public DateTime CreatedAt { get; set; }
    public DateTime UpdatedAt { get; set; }
}
