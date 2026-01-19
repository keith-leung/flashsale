using FlashSale.Models;
using Microsoft.EntityFrameworkCore;

namespace FlashSale.Data;

public class FlashSaleDbContext : DbContext
{
    public FlashSaleDbContext(DbContextOptions<FlashSaleDbContext> options) : base(options) { }

    public DbSet<Order> Orders { get; set; }
    public DbSet<OrderLineItem> OrderLineItems { get; set; }
    public DbSet<Payment> Payments { get; set; }
    public DbSet<Sku> Skus { get; set; }
    public DbSet<Inventory> Inventories { get; set; }
    public DbSet<Spu> Spus { get; set; }
    public DbSet<FlashSaleCampaign> FlashSaleCampaigns { get; set; }

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        base.OnModelCreating(modelBuilder);

        // Order configuration
        modelBuilder.Entity<Order>(entity =>
        {
            entity.HasKey(e => e.Id);
            entity.Property(e => e.OrderNumber).IsRequired().HasMaxLength(100);
            entity.Property(e => e.CustomerName).IsRequired().HasMaxLength(200);
            entity.Property(e => e.CustomerEmail).IsRequired().HasMaxLength(200);
            entity.Property(e => e.Status).IsRequired().HasMaxLength(50);
            entity.Property(e => e.TotalAmount).HasPrecision(10, 2);
        });

        // OrderLineItem configuration
        modelBuilder.Entity<OrderLineItem>(entity =>
        {
            entity.HasKey(e => e.Id);
            entity.Property(e => e.UnitPrice).HasPrecision(10, 2);
            entity.HasOne(e => e.Order)
                .WithMany(o => o.LineItems)
                .HasForeignKey(e => e.OrderId)
                .OnDelete(DeleteBehavior.Cascade);
            entity.HasOne(e => e.Sku)
                .WithMany(s => s.OrderLineItems)
                .HasForeignKey(e => e.SkuId)
                .OnDelete(DeleteBehavior.Restrict);
        });

        // Payment configuration
        modelBuilder.Entity<Payment>(entity =>
        {
            entity.HasKey(e => e.Id);
            entity.Property(e => e.Amount).HasPrecision(10, 2);
            entity.Property(e => e.Status).IsRequired().HasMaxLength(50);
            entity.Property(e => e.PaymentMethod).IsRequired().HasMaxLength(50);
            entity.HasOne(e => e.Order)
                .WithMany(o => o.Payments)
                .HasForeignKey(e => e.OrderId)
                .OnDelete(DeleteBehavior.Cascade);
        });

        // Sku configuration
        modelBuilder.Entity<Sku>(entity =>
        {
            entity.HasKey(e => e.Id);
            entity.Property(e => e.Name).IsRequired().HasMaxLength(200);
            entity.HasOne(e => e.Spu)
                .WithMany(s => s.Skus)
                .HasForeignKey(e => e.SpuId)
                .OnDelete(DeleteBehavior.Cascade);
            entity.HasOne(e => e.Inventory)
                .WithOne(i => i.Sku)
                .HasForeignKey<Inventory>(i => i.SkuId)
                .OnDelete(DeleteBehavior.Cascade);
        });

        // Inventory configuration
        modelBuilder.Entity<Inventory>(entity =>
        {
            entity.HasKey(e => e.Id);
            entity.HasOne(e => e.Sku)
                .WithOne(s => s.Inventory)
                .HasForeignKey<Inventory>(e => e.SkuId)
                .OnDelete(DeleteBehavior.Cascade);
        });

        // Spu configuration
        modelBuilder.Entity<Spu>(entity =>
        {
            entity.HasKey(e => e.Id);
            entity.Property(e => e.Name).IsRequired().HasMaxLength(200);
        });

        // FlashSaleCampaign configuration
        modelBuilder.Entity<FlashSaleCampaign>(entity =>
        {
            entity.HasKey(e => e.Id);
            entity.Property(e => e.Name).IsRequired().HasMaxLength(200);
            entity.Property(e => e.Status).IsRequired().HasMaxLength(50);
            entity.HasOne(e => e.Spu)
                .WithMany()
                .HasForeignKey(e => e.SpuId)
                .OnDelete(DeleteBehavior.Restrict);
        });
    }
}