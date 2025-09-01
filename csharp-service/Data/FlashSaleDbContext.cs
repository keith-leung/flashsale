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
    
    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        base.OnModelCreating(modelBuilder);
        
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
    }
    
    public override int SaveChanges()
    {
        UpdateTimestamps();
        return base.SaveChanges();
    }
    
    public override Task<int> SaveChangesAsync(CancellationToken cancellationToken = default)
    {
        UpdateTimestamps();
        return base.SaveChangesAsync(cancellationToken);
    }
    
    private void UpdateTimestamps()
    {
        var entries = ChangeTracker.Entries()
            .Where(e => e.Entity is BaseEntity && e.State is EntityState.Modified);
            
        foreach (var entry in entries)
        {
            ((BaseEntity)entry.Entity).UpdatedAt = DateTime.UtcNow;
        }
    }
}
