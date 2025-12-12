#!/usr/bin/env python3

"""Test script to debug user details loading."""

import sys
sys.path.insert(0, '/home/ti2103@domman.ad/dev/adtui')

from adtui.widgets.user_details import UserDetailsPane

# Mock connection manager
class MockConnectionManager:
    def __init__(self):
        self.conn = None
    
    def get_connection(self):
        print("DEBUG: Mock get_connection called")
        return self.conn

# Test the user details loading
try:
    print("Creating UserDetailsPane...")
    user_details = UserDetailsPane()
    
    print("Creating mock connection manager...")
    mock_conn_manager = MockConnectionManager()
    
    print("Calling update_user_details...")
    user_details.update_user_details("CN=Test User,DC=domman,DC=ad", mock_conn_manager)
    
    print(f"Entry loaded: {user_details.entry is not None}")
    print(f"Member of: {user_details.member_of}")
    print(f"Raw attributes: {user_details.raw_attributes}")
    
    if user_details.entry:
        content = user_details._build_content()
        print(f"Content preview: {content[:200]}...")
    else:
        print("No entry found - this is expected with mock connection")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()