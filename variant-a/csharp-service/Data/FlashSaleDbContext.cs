using FlashSale.Api.Models;
using Microsoft.EntityFrameworkCore;

namespace FlashSale.Api.Data;

public class FlashSaleDbContext : DbContext
{
    public FlashSaleDbContext(DbContextOptions<FlashSaleDbContext> options) : base(options)
    {
    }
    
    public DbSet<Spu> Spus { get; set; }
    public DbSet<Sku> Skus { get; set; }
    public DbSet<Inventory> Inventories { get; set; }
    public DbSet<FlashSaleEvent> FlashSaleEvents { get; set; }
    public DbSet<Models.FlashSale> FlashSaleCampaigns { get; set; }
    public DbSet<Order> Orders { get; set; }
    public DbSet<OrderLineItem> OrderLineItems { get; set; }
    public DbSet<Payment> Payments { get; set; }
    public DbSet<CampaignSkuAllocation> CampaignSkuAllocations { get; set; }
    
    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        base.OnModelCreating(modelBuilder);

        // Configure explicit table names to match Python schema
        modelBuilder.Entity<Spu>().ToTable("spus");
        modelBuilder.Entity<Sku>().ToTable("skus");
        modelBuilder.Entity<Inventory>().ToTable("inventory");
        modelBuilder.Entity<FlashSaleEvent>().ToTable("flash_sale_events");
        modelBuilder.Entity<Order>().ToTable("orders");
        modelBuilder.Entity<OrderLineItem>().ToTable("order_line_items");
        modelBuilder.Entity<Payment>().ToTable("payments");
        modelBuilder.Entity<CampaignSkuAllocation>().ToTable("campaign_sku_allocations");

        // Spu configuration
        modelBuilder.Entity<Spu>(entity =>
        {
            entity.HasIndex(e => e.Slug).IsUnique();
            entity.Property(e => e.UpdatedAt).HasDefaultValueSql("CURRENT_TIMESTAMP");
        });
        
        // Sku configuration
        modelBuilder.Entity<Sku>(entity =>
        {
            entity.HasIndex(e => e.SkuCode).IsUnique();
            entity.Property(e => e.UpdatedAt).HasDefaultValueSql("CURRENT_TIMESTAMP");
            
            entity.HasOne(e => e.Spu)
                  .WithMany(e => e.Skus)
                  .HasForeignKey(e => e.SpuId)
                  .OnDelete(DeleteBehavior.Cascade);
        });
        
        // Inventory configuration
        modelBuilder.Entity<Inventory>(entity =>
        {
            entity.HasIndex(e => e.SkuId).IsUnique();
            entity.Property(e => e.UpdatedAt).HasDefaultValueSql("CURRENT_TIMESTAMP");
            
            entity.HasOne(e => e.Sku)
                  .WithOne(e => e.Inventory)
                  .HasForeignKey<Inventory>(e => e.SkuId)
                  .OnDelete(DeleteBehavior.Cascade);
        });
        
        // FlashSaleEvent configuration
        modelBuilder.Entity<FlashSaleEvent>(entity =>
        {
            entity.HasIndex(e => e.StartTime);
            entity.HasIndex(e => e.EndTime);
            entity.HasIndex(e => e.Status);
            entity.Property(e => e.UpdatedAt).HasDefaultValueSql("CURRENT_TIMESTAMP");

            entity.HasOne(e => e.Sku)
                  .WithMany(e => e.FlashSales)
                  .HasForeignKey(e => e.SkuId)
                  .OnDelete(DeleteBehavior.Cascade);

            entity.Property(e => e.Status)
                  .HasConversion<string>();
        });

        // FlashSale (SPU-level campaigns) configuration
        modelBuilder.Entity<Models.FlashSale>(entity =>
        {
            entity.ToTable("flash_sale_campaigns");
            entity.HasIndex(e => e.Name);
            entity.HasIndex(e => e.SpuId);
            entity.HasIndex(e => e.StartTime);
            entity.HasIndex(e => e.EndTime);
            entity.HasIndex(e => e.Status);
            entity.HasIndex(e => e.IsActive);
            entity.HasIndex(e => e.CreatedAt);
            entity.Property(e => e.UpdatedAt).HasDefaultValueSql("CURRENT_TIMESTAMP");

            entity.HasOne(e => e.Spu)
                  .WithMany()
                  .HasForeignKey(e => e.SpuId)
                  .OnDelete(DeleteBehavior.Cascade);
        });

        // Order configuration
        modelBuilder.Entity<Order>(entity =>
        {
            entity.HasIndex(e => e.OrderNumber).IsUnique();
            entity.HasIndex(e => e.CustomerEmail);
            entity.HasIndex(e => e.Status);
            entity.HasIndex(e => e.CreatedAt);
            entity.Property(e => e.UpdatedAt).HasDefaultValueSql("CURRENT_TIMESTAMP");

            entity.HasOne(e => e.FlashSaleCampaign)
                  .WithMany(e => e.Orders)
                  .HasForeignKey(e => e.FlashSaleCampaignId)
                  .OnDelete(DeleteBehavior.SetNull);
                  
            entity.Property(e => e.Status)
                  .HasConversion<string>();
        });
        
        // OrderLineItem configuration
        modelBuilder.Entity<OrderLineItem>(entity =>
        {
            entity.HasIndex(e => e.OrderId);
            entity.HasIndex(e => e.SkuId);
            entity.Property(e => e.UpdatedAt).HasDefaultValueSql("CURRENT_TIMESTAMP");
            
            entity.HasOne(e => e.Order)
                  .WithMany(e => e.LineItems)
                  .HasForeignKey(e => e.OrderId)
                  .OnDelete(DeleteBehavior.Cascade);
                  
            entity.HasOne(e => e.Sku)
                  .WithMany()
                  .HasForeignKey(e => e.SkuId)
                  .OnDelete(DeleteBehavior.Restrict);
        });
        
        // Payment configuration
        modelBuilder.Entity<Payment>(entity =>
        {
            entity.HasIndex(e => e.OrderId);
            entity.HasIndex(e => e.GatewayTransactionId);
            entity.HasIndex(e => e.Status);
            entity.HasIndex(e => e.CreatedAt);
            entity.Property(e => e.UpdatedAt).HasDefaultValueSql("CURRENT_TIMESTAMP");
            
            entity.HasOne(e => e.Order)
                  .WithMany(e => e.Payments)
                  .HasForeignKey(e => e.OrderId)
                  .OnDelete(DeleteBehavior.Cascade);
                  
            entity.Property(e => e.Status)
                  .HasConversion<string>();
        });
    }
    
    // Timestamps are handled by database defaults (created_at, updated_at)
}
