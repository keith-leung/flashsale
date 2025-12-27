namespace FlashSale.Api.Services;

/// <summary>
/// Background service to periodically update flash sale statuses
/// </summary>
public class FlashSaleStatusUpdateService : BackgroundService
{
    private readonly IServiceProvider _serviceProvider;
    private readonly ILogger<FlashSaleStatusUpdateService> _logger;
    private readonly TimeSpan _updateInterval = TimeSpan.FromMinutes(1); // Update every minute

    public FlashSaleStatusUpdateService(IServiceProvider serviceProvider, ILogger<FlashSaleStatusUpdateService> logger)
    {
        _serviceProvider = serviceProvider;
        _logger = logger;
    }

    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        _logger.LogInformation("Flash Sale Status Update Service started");

        while (!stoppingToken.IsCancellationRequested)
        {
            try
            {
                using var scope = _serviceProvider.CreateScope();
                var flashSaleService = scope.ServiceProvider.GetRequiredService<IFlashSaleService>();
                
                await flashSaleService.UpdateFlashSaleStatusesAsync();
                
                await Task.Delay(_updateInterval, stoppingToken);
            }
            catch (OperationCanceledException)
            {
                // Expected when cancellation is requested
                break;
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error occurred while updating flash sale statuses");
                await Task.Delay(TimeSpan.FromSeconds(30), stoppingToken); // Wait before retrying
            }
        }

        _logger.LogInformation("Flash Sale Status Update Service stopped");
    }
}
