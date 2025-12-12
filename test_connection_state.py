#!/usr/bin/env python3

"""Test script to check connection manager state."""

import sys
sys.path.insert(0, '/home/ti2103@domman.ad/dev/adtui')

from adtui.services.connection_manager import ConnectionManager, ConnectionState
from adtui.services.config_service import ADConfig

# Test connection manager states
try:
    print("Testing connection manager...")
    
    # Create a mock AD config
    ad_config = ADConfig(
        server="test-server",
        domain="TEST",
        base_dn="DC=test,DC=com",
        use_ssl=False
    )
    
    # Create connection manager
    conn_manager = ConnectionManager(
        ad_config=ad_config,
        username="testuser",
        password="testpass",
        max_retries=3,
        initial_retry_delay=1.0,
        max_retry_delay=10.0,
        health_check_interval=30.0
    )
    
    print(f"Connection manager created: {conn_manager}")
    print(f"Initial state: {conn_manager.get_state()}")
    print(f"Has get_connection method: {hasattr(conn_manager, 'get_connection')}")
    
    # Try to get connection
    conn = conn_manager.get_connection()
    print(f"Connection: {conn}")
    print(f"Connection state: {conn_manager.get_state()}")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()