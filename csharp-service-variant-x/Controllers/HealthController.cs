using Microsoft.AspNetCore.Mvc;

namespace FlashSale.Api.Controllers
{
    /// <summary>
    /// Health check endpoint for load balancer.
    /// </summary>
    [ApiController]
    public class HealthController : ControllerBase
    {
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
    }
}
