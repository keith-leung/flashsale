using FlashSale.Api.V.Models;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Storage.ValueConversion;

namespace FlashSale.Api.V.Data;

public class FlashSaleDbContext : DbContext
{
    public FlashSaleDbContext(DbContextOptions<FlashSaleDbContext> options) : base(options) { }

    public DbSet<AuditOrderLog> AuditOrderLogs { get; set; }

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        base.OnModelCreating(modelBuilder);

        modelBuilder.Entity<AuditOrderLog>(entity =>
        {
            entity.ToTable("audit_order_log");
            entity.HasKey(e => e.Id);
            
            entity.Property(e => e.Id).HasColumnName("id");
            entity.Property(e => e.OrderId).HasColumnName("order_id").IsRequired();
            entity.Property(e => e.CustomerEmail).HasColumnName("customer_email").HasMaxLength(255).IsRequired();
            entity.Property(e => e.SkuId).HasColumnName("sku_id").IsRequired();
            entity.Property(e => e.Quantity).HasColumnName("quantity").IsRequired();
            entity.Property(e => e.UnitPrice).HasColumnName("unit_price").HasPrecision(10, 2).IsRequired();
            entity.Property(e => e.FlashSaleCampaignId).HasColumnName("flash_sale_campaign_id");
            entity.Property(e => e.Status)
                .HasColumnName("status")
                .HasMaxLength(20)
                .IsRequired()
                .HasConversion<string>();
            entity.Property(e => e.CreatedAt).HasColumnName("created_at").IsRequired();
            entity.Property(e => e.UpdatedAt).HasColumnName("updated_at");
            
            entity.HasIndex(e => new { e.OrderId, e.Status }).HasDatabaseName("idx_audit_lookup");
            entity.HasIndex(e => new { e.FlashSaleCampaignId, e.CreatedAt }).HasDatabaseName("idx_campaign_audit");
        });
    }
}
