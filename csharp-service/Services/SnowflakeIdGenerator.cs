using System;
using System.Threading;

namespace FlashSale.Api.Services
{
    /// <summary>
    /// Twitter Snowflake ID Generator for distributed systems.
    /// 
    /// 64-bit structure:
    /// ┌─┬─────────────────────────────────────────────┬──────────────┬──────────────────┐
    /// │0│              Timestamp (41 bits)             │ Machine (10) │ Sequence (12)    │
    /// └─┴─────────────────────────────────────────────┴──────────────┴──────────────────┘
    /// 
    /// Capacity: 4,096 IDs per millisecond per machine = 4,096,000 IDs/second per service
    /// </summary>
    public class SnowflakeIdGenerator
    {
        // Custom epoch (January 1, 2024 00:00:00 UTC)
        private static readonly long EPOCH = 1704067200000L;
        
        // Bit lengths
        private const int SEQUENCE_BITS = 12;      // 4,096 sequences per millisecond
        private const int MACHINE_ID_BITS = 10;    // 1,024 different machines
        private const int TIMESTAMP_BITS = 41;     // ~69 years of milliseconds
        
        // Bit shifts
        private const int MACHINE_ID_SHIFT = SEQUENCE_BITS;                    // 12
        private const int TIMESTAMP_SHIFT = SEQUENCE_BITS + MACHINE_ID_BITS;   // 22
        
        // Masks
        private const long SEQUENCE_MASK = (1L << SEQUENCE_BITS) - 1;          // 4095
        private const long MACHINE_ID_MASK = (1L << MACHINE_ID_BITS) - 1;      // 1023
        
        private readonly long _machineId;
        private long _sequence = 0L;
        private long _lastTimestamp = 0L;
        private readonly object _lock = new object();
        
        /// <summary>
        /// Initialize Snowflake generator.
        /// </summary>
        /// <param name="machineId">Unique machine identifier (0-1023)
        /// C# services: 342-682</param>
        public SnowflakeIdGenerator(long machineId)
        {
            if (machineId < 0 || machineId > MACHINE_ID_MASK)
                throw new ArgumentException($"Machine ID must be between 0 and {MACHINE_ID_MASK}");
                
            _machineId = machineId;
        }
        
        /// <summary>
        /// Generate next Snowflake ID.
        /// </summary>
        /// <returns>64-bit Snowflake ID</returns>
        /// <exception cref="InvalidOperationException">If clock moves backwards</exception>
        public long Generate()
        {
            lock (_lock)
            {
                var timestamp = GetTimestamp();
                
                // Clock moved backwards - this should never happen in production
                if (timestamp < _lastTimestamp)
                {
                    throw new InvalidOperationException(
                        $"Clock moved backwards. Refusing to generate ID for {_lastTimestamp - timestamp} milliseconds");
                }
                
                // Same millisecond - increment sequence
                if (timestamp == _lastTimestamp)
                {
                    _sequence = (_sequence + 1) & SEQUENCE_MASK;
                    
                    // Sequence overflow - wait for next millisecond
                    if (_sequence == 0)
                    {
                        timestamp = WaitForNextMillis(timestamp);
                    }
                }
                else
                {
                    // New millisecond - reset sequence
                    _sequence = 0L;
                }
                
                _lastTimestamp = timestamp;
                
                // Combine all parts into 64-bit ID
                return ((timestamp - EPOCH) << TIMESTAMP_SHIFT) |
                       (_machineId << MACHINE_ID_SHIFT) |
                       _sequence;
            }
        }
        
        /// <summary>
        /// Parse Snowflake ID into components.
        /// </summary>
        /// <param name="snowflakeId">64-bit Snowflake ID</param>
        /// <returns>Parsed components</returns>
        public SnowflakeComponents Parse(long snowflakeId)
        {
            var timestamp = ((snowflakeId >> TIMESTAMP_SHIFT) + EPOCH);
            var machineId = (snowflakeId >> MACHINE_ID_SHIFT) & MACHINE_ID_MASK;
            var sequence = snowflakeId & SEQUENCE_MASK;
            
            return new SnowflakeComponents
            {
                Id = snowflakeId,
                Timestamp = timestamp,
                MachineId = machineId,
                Sequence = sequence,
                DateTime = DateTimeOffset.FromUnixTimeMilliseconds(timestamp).DateTime
            };
        }
        
        private long GetTimestamp() => DateTimeOffset.UtcNow.ToUnixTimeMilliseconds();
        
        private long WaitForNextMillis(long lastTimestamp)
        {
            var timestamp = GetTimestamp();
            while (timestamp <= lastTimestamp)
            {
                timestamp = GetTimestamp();
            }
            return timestamp;
        }
    }
    
    /// <summary>
    /// Snowflake ID components for parsing results.
    /// </summary>
    public class SnowflakeComponents
    {
        public long Id { get; set; }
        public long Timestamp { get; set; }
        public long MachineId { get; set; }
        public long Sequence { get; set; }
        public DateTime DateTime { get; set; }
    }
    
    /// <summary>
    /// C# Service-specific generator (machine IDs 342-682)
    /// </summary>
    public class CSharpSnowflakeGenerator : SnowflakeIdGenerator
    {
        public CSharpSnowflakeGenerator(int instanceId = 1) 
            : base(341 + instanceId) // Offset to 342-682 range
        {
            if (instanceId < 1 || instanceId > 341)
                throw new ArgumentException("C# service instance ID must be between 1 and 341");
        }
    }
}
