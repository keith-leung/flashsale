"""Twitter Snowflake ID generator for high-concurrency distributed systems."""

import time
import threading
import os
from typing import Dict, Optional


class SnowflakeIDGenerator:
    """
    Twitter Snowflake ID Generator for distributed systems.
    
    64-bit structure:
    ┌─┬─────────────────────────────────────────────┬──────────────┬──────────────────┐
    │0│              Timestamp (41 bits)             │ Machine (10) │ Sequence (12)    │
    └─┴─────────────────────────────────────────────┴──────────────┴──────────────────┘
    
    Capacity: 4,096 IDs per millisecond per machine = 4,096,000 IDs/second per service
    """
    
    # Custom epoch (January 1, 2024 00:00:00 UTC) - gives us 69 years from 2024
    EPOCH = 1704067200000  # 2024-01-01 00:00:00 UTC in milliseconds
    
    # Bit lengths
    SEQUENCE_BITS = 12      # 4,096 sequences per millisecond
    MACHINE_ID_BITS = 10    # 1,024 different machines
    TIMESTAMP_BITS = 41     # ~69 years of milliseconds
    
    # Bit shifts
    MACHINE_ID_SHIFT = SEQUENCE_BITS                           # 12
    TIMESTAMP_SHIFT = SEQUENCE_BITS + MACHINE_ID_BITS          # 22
    
    # Masks
    SEQUENCE_MASK = (1 << SEQUENCE_BITS) - 1                   # 4095
    MACHINE_ID_MASK = (1 << MACHINE_ID_BITS) - 1               # 1023
    
    def __init__(self, machine_id: int):
        """
        Initialize Snowflake generator.
        
        Args:
            machine_id: Unique machine identifier (0-1023)
                       Python services: 1-341
                       C# services: 342-682  
                       Java services: 683-1023
        """
        if not (0 <= machine_id <= self.MACHINE_ID_MASK):
            raise ValueError(f"Machine ID must be between 0 and {self.MACHINE_ID_MASK}")
            
        self.machine_id = machine_id
        self.sequence = 0
        self.last_timestamp = 0
        self.lock = threading.Lock()
    
    def generate(self) -> int:
        """
        Generate next Snowflake ID.
        
        Returns:
            int: 64-bit Snowflake ID
            
        Raises:
            RuntimeError: If clock moves backwards
        """
        with self.lock:
            timestamp = self._get_timestamp()
            
            # Clock moved backwards - this should never happen in production
            if timestamp < self.last_timestamp:
                raise RuntimeError(
                    f"Clock moved backwards. Refusing to generate ID for "
                    f"{self.last_timestamp - timestamp} milliseconds"
                )
            
            # Same millisecond - increment sequence
            if timestamp == self.last_timestamp:
                self.sequence = (self.sequence + 1) & self.SEQUENCE_MASK
                
                # Sequence overflow - wait for next millisecond
                if self.sequence == 0:
                    timestamp = self._wait_for_next_millis(timestamp)
            else:
                # New millisecond - reset sequence
                self.sequence = 0
            
            self.last_timestamp = timestamp
            
            # Combine all parts into 64-bit ID
            snowflake_id = (
                ((timestamp - self.EPOCH) << self.TIMESTAMP_SHIFT) |
                (self.machine_id << self.MACHINE_ID_SHIFT) |
                self.sequence
            )
            
            return snowflake_id
    
    def parse(self, snowflake_id: int) -> Dict:
        """
        Parse Snowflake ID into components.
        
        Args:
            snowflake_id: 64-bit Snowflake ID
            
        Returns:
            dict: Parsed components
        """
        timestamp = ((snowflake_id >> self.TIMESTAMP_SHIFT) + self.EPOCH)
        machine_id = (snowflake_id >> self.MACHINE_ID_SHIFT) & self.MACHINE_ID_MASK
        sequence = snowflake_id & self.SEQUENCE_MASK
        
        return {
            'id': snowflake_id,
            'timestamp': timestamp,
            'machine_id': machine_id,
            'sequence': sequence,
            'datetime': time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(timestamp / 1000))
        }
    
    def _get_timestamp(self) -> int:
        """Get current timestamp in milliseconds."""
        return int(time.time() * 1000)
    
    def _wait_for_next_millis(self, last_timestamp: int) -> int:
        """Wait until next millisecond."""
        timestamp = self._get_timestamp()
        while timestamp <= last_timestamp:
            timestamp = self._get_timestamp()
        return timestamp


class PythonSnowflakeGenerator(SnowflakeIDGenerator):
    """Python service Snowflake generator (machine IDs 1-341)"""
    
    def __init__(self, instance_id: int = 1):
        if not (1 <= instance_id <= 341):
            raise ValueError("Python service instance_id must be between 1 and 341")
        super().__init__(instance_id)


class CSharpSnowflakeGenerator(SnowflakeIDGenerator):
    """C# service Snowflake generator (machine IDs 342-682)"""
    
    def __init__(self, instance_id: int = 1):
        if not (1 <= instance_id <= 341):
            raise ValueError("C# service instance_id must be between 1 and 341")
        machine_id = 341 + instance_id  # Offset to 342-682 range
        super().__init__(machine_id)


class JavaSnowflakeGenerator(SnowflakeIDGenerator):
    """Java service Snowflake generator (machine IDs 683-1023)"""
    
    def __init__(self, instance_id: int = 1):
        if not (1 <= instance_id <= 341):
            raise ValueError("Java service instance_id must be between 1 and 341")
        machine_id = 682 + instance_id  # Offset to 683-1023 range
        super().__init__(machine_id)


# Global generator instance (configure based on service type and instance)
SERVICE_TYPE = os.environ.get('SERVICE_TYPE', 'python')  # python|csharp|java
INSTANCE_ID = int(os.environ.get('INSTANCE_ID', '1'))    # 1-341

if SERVICE_TYPE == 'python':
    id_generator = PythonSnowflakeGenerator(INSTANCE_ID)
elif SERVICE_TYPE == 'csharp':
    id_generator = CSharpSnowflakeGenerator(INSTANCE_ID)
elif SERVICE_TYPE == 'java':
    id_generator = JavaSnowflakeGenerator(INSTANCE_ID)
else:
    # Default to Python with instance 1
    id_generator = PythonSnowflakeGenerator(1)


def generate_id() -> int:
    """Generate a new Snowflake ID."""
    return id_generator.generate()


def parse_id(snowflake_id: int) -> Dict:
    """Parse Snowflake ID components."""
    return id_generator.parse(snowflake_id)
