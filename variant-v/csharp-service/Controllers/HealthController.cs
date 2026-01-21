using Microsoft.AspNetCore.Mvc;

namespace FlashSale.Api.V.Controllers;

[ApiController]
[Route("[controller]")]
public class HealthController : ControllerBase
{
    [HttpGet]
    [HttpHead]
    public IActionResult Get()
    {
        return Ok("200 OK");
    }
}
