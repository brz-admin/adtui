#!/usr/bin/env python3

"""Test script to verify the user details fix."""

import sys
import os

# Add the adtui directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'adtui'))

from widgets.user_details import UserDetailsPane
from services.connection_manager import ConnectionManager
from services.config_service import ADConfig

# Mock classes for testing
class MockConnection:
    def __init__(self):
        self.entries = []
        
    def search(self, dn, filter, search_scope='BASE', attributes=['*']):
        # Mock search that returns a user entry
        class MockEntry:
            def __init__(self):
                self.cn = type('obj', (object,), {'value': 'Test User'})()
                self.sAMAccountName = type('obj', (object,), {'value': 'testuser'})()
                self.displayName = type('obj', (object,), {'value': 'Test User Display'})()
                self.mail = type('obj', (object,), {'value': 'test@example.com'})()
                self.userAccountControl = type('obj', (object,), {'value': 512})()  # Normal account
                self.memberOf = type('obj', (object,), {'values': ['CN=Users,DC=example,DC=com']})()
                self.entry_attributes = {'cn': ['Test User'], 'sAMAccountName': ['testuser']}
        
        self.entries = [MockEntry()]

class MockConnectionManager:
    def __init__(self):
        self.connection = MockConnection()
        
    def execute_with_retry(self, operation):
        return operation(self.connection)
        
    def get_state(self):
        return "connected"

def test_user_details_loading():
    """Test that user details can be loaded correctly."""
    print("Testing user details loading...")
    
    # Create mock connection manager
    connection_manager = MockConnectionManager()
    
    # Create user details pane
    user_details = UserDetailsPane()
    
    # Test user DN
    test_dn = "CN=Test User,CN=Users,DC=example,DC=com"
    
    # Update user details
    user_details.update_user_details(test_dn, connection_manager)
    
    # Check if entry was loaded
    if user_details.entry is not None:
        print("✅ SUCCESS: User entry was loaded successfully")
        print(f"   User CN: {user_details.entry.cn.value}")
        print(f"   Username: {user_details.entry.sAMAccountName.value}")
        
        # Test content building
        content = user_details._build_content()
        if "No user data" not in content:
            print("✅ SUCCESS: Content was built successfully")
            print(f"   Content preview: {content[:100]}...")
        else:
            print("❌ FAILED: Content still shows 'No user data'")
            
    else:
        print("❌ FAILED: User entry was not loaded")
        print("   This indicates the fix did not work")
        
    return user_details.entry is not None

if __name__ == "__main__":
    success = test_user_details_loading()
    sys.exit(0 if success else 1)