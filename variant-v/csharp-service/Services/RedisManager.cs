using StackExchange.Redis;
using System.Security.Cryptography;
using System.Text;

namespace FlashSale.Api.V.Services;

public class RedisManager
{
    private readonly ConnectionMultiplexer[] _connections;
    private readonly IDatabase[] _databases;
    
    public RedisManager(string[] nodes)
    {
        _connections = new ConnectionMultiplexer[nodes.Length];
        _databases = new IDatabase[nodes.Length];
        
        for (int i = 0; i < nodes.Length; i++)
        {
            var config = ConfigurationOptions.Parse(nodes[i]);
            config.ConnectTimeout = 5000;
            config.SyncTimeout = 5000;
            config.AbortOnConnectFail = false;
            
            _connections[i] = ConnectionMultiplexer.Connect(config);
            _databases[i] = _connections[i].GetDatabase();
        }
    }
    
    public IDatabase GetDatabaseForSku(string skuId)
    {
        int nodeIndex = GetNodeIndexForSku(skuId);
        return _databases[nodeIndex];
    }
    
    public ConnectionMultiplexer GetConnectionForSku(string skuId)
    {
        int nodeIndex = GetNodeIndexForSku(skuId);
        return _connections[nodeIndex];
    }
    
    public IDatabase[] GetAllDatabases() => _databases;
    
    private int GetNodeIndexForSku(string skuId)
    {
        using (var md5 = MD5.Create())
        {
            var hash = md5.ComputeHash(Encoding.UTF8.GetBytes(skuId));
            int hashValue = BitConverter.ToInt32(hash, 0);
            return Math.Abs(hashValue) % _databases.Length;
        }
    }
}
