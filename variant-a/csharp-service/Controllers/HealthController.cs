using Microsoft.AspNetCore.Mvc;
using FlashSaleAPI.Services;
using System;
using System.Collections.Generic;

namespace FlashSale.Api.Controllers
{
    /// <summary>
    /// Health check endpoint for load balancer.
    /// </summary>
    [ApiController]
    public class HealthController : ControllerBase
    {
        private readonly CampaignMemoryAllocator _allocator;
        private static readonly Guid BenchmarkCampaignId = Guid.Parse("00000000-0000-0000-0000-000000000001");
        private static readonly Guid BenchmarkSkuId = Guid.Parse("00000000-0000-0000-0000-000000000002");
        private static bool _benchmarkLoaded = false;
        private static readonly object _benchmarkLock = new object();

        public HealthController(CampaignMemoryAllocator allocator)
        {
            _allocator = allocator;
        }

        /// <summary>
        /// Health check endpoint.
        /// Returns plain text "200 OK" following BoA internal pattern.
        /// Supports both GET and HEAD methods.
        /// </summary>
        [HttpGet("/health")]
        [HttpHead("/health")]
        public IActionResult Health()
        {
            return Ok("200 OK");
        }

        /// <summary>
        /// Benchmark endpoint to emulate Order creation (Fast Path only).
        /// Emulates infinite inventory (10M items) to test raw allocation overhead without Redis I/O.
        /// </summary>
        [HttpGet("/health2")]
        public async Task<IActionResult> Health2()
        {
            // Lazy load benchmark campaign with massive inventory
            if (!_benchmarkLoaded)
            {
                lock (_benchmarkLock)
                {
                    if (!_benchmarkLoaded)
                    {
                        var skuAllocations = new Dictionary<Guid, int>
                        {
                            { BenchmarkSkuId, 10_000_000 } // 10 Million items
                        };

                        _allocator.LoadCampaign(
                            BenchmarkCampaignId,
                            Guid.NewGuid(),
                            skuAllocations,
                            100m,
                            200m,
                            20 // 20% watermark
                        );
                        _benchmarkLoaded = true;
                    }
                }
            }

            // Perform exactly one reservation (Fast Path simulation)
            var result = await _allocator.ReserveItemAsync(BenchmarkCampaignId, BenchmarkSkuId);

            if (result.Success)
            {
                return Ok("200 OK");
            }
            else
            {
                return StatusCode(500, $"Benchmark allocation failed: {result.PriceType}");
            }
        }

        /// <summary>
        /// Benchmark: POST + JSON parsing + allocation + JSON response
        /// Isolates JSON overhead from full order path.
        /// </summary>
        [HttpPost("/health3")]
        public async Task<IActionResult> Health3([FromBody] Health3Request request)
        {
            // Lazy load benchmark campaign
            if (!_benchmarkLoaded)
            {
                lock (_benchmarkLock)
                {
                    if (!_benchmarkLoaded)
                    {
                        var skuAllocations = new Dictionary<Guid, int>
                        {
                            { BenchmarkSkuId, 10_000_000 }
                        };
                        _allocator.LoadCampaign(BenchmarkCampaignId, Guid.NewGuid(), skuAllocations, 100m, 200m, 20);
                        _benchmarkLoaded = true;
                    }
                }
            }

            // Allocation
            var result = await _allocator.ReserveItemAsync(BenchmarkCampaignId, BenchmarkSkuId);

            if (result.Success)
            {
                return Ok(new Health3Response { Success = true, Price = result.Price });
            }
            return StatusCode(500, new { error = result.PriceType });
        }

        /// <summary>
        /// Benchmark: Full order simulation using REAL campaign (with refills)
        /// </summary>
        [HttpPost("/health4")]
        public async Task<IActionResult> Health4([FromBody] Health3Request request)
        {
            // Use real campaign
            var campaignId = Guid.Parse("99999999-8888-7777-6666-555544443333");
            var skuId = Guid.Parse("11111111-2222-3333-4444-555555555555");

            var result = await _allocator.ReserveItemAsync(campaignId, skuId);

            if (result.Success)
            {
                // Build payload like real order (but don't queue)
                var payload = new Dictionary<string, object>
                {
                    ["order_number"] = $"ORD-{DateTime.UtcNow.Ticks}",
                    ["sku_id"] = skuId.ToString(),
                    ["price"] = result.Price
                };
                return Ok(new Health3Response { Success = true, Price = result.Price });
            }
            return StatusCode(500, new { error = result.PriceType });
        }
    }

    public class Health3Request
    {
        public string? Email { get; set; }
        public int Quantity { get; set; } = 1;
    }

    public class Health3Response
    {
        public bool Success { get; set; }
        public decimal Price { get; set; }
    }
}
