using Microsoft.AspNetCore.Mvc;

namespace FlashSale.Controllers;

[ApiController]
[Route("/")]
public class HealthController : ControllerBase
{
    [HttpGet("health")]
    public IActionResult Health()
    {
        return Ok("OK");
    }
}