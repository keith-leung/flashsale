namespace FlashSale.Models;

public class FlashSaleCampaign : BaseEntity
{
    public Guid SpuId { get; set; }
    public string Name { get; set; } = string.Empty;
    public string Status { get; set; } = "not_started"; // not_started, active, sold_out, ended
    public DateTime StartTime { get; set; }
    public DateTime EndTime { get; set; }
    public int TotalSaleLimit { get; set; }
    public int SoldQuantity { get; set; }
    
    // Navigation properties
    public Spu Spu { get; set; } = null!;
}