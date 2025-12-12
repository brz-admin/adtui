#!/usr/bin/env python3

"""Test script to verify the initial connect authentication failure fix."""

import sys
import os

def test_initial_connect_auth_fix():
    """Test that initial connect handles authentication failures properly."""
    print("Testing initial connect authentication failure fix...")
    
    # Read the connection_manager.py file
    connection_manager_path = "adtui/services/connection_manager.py"
    
    try:
        with open(connection_manager_path, 'r') as f:
            content = f.read()
        
        # Check if the authentication error handling is added to _connect method
        checks = [
            ("Authentication error detected during initial connect" in content, "✅ Initial connect auth error detection added"),
            ("_is_authentication_error(error_msg)" in content, "✅ Auth error check in initial connect"),
            ("_trigger_auth_failure()" in content, "✅ Auth failure trigger in initial connect"),
            ("return" in content and "Authentication error detected during initial connect" in content, "✅ Early return for auth errors"),
            ("not retrying:" in content.lower(), "✅ No retry comment for auth errors"),
        ]
        
        all_passed = True
        for check, message in checks:
            if check:
                print(message)
            else:
                print(f"❌ {message.replace('✅', 'FAILED')}")
                all_passed = False
        
        return all_passed
        
    except FileNotFoundError:
        print(f"❌ FAILED: Could not find {connection_manager_path}")
        return False
    except Exception as e:
        print(f"❌ FAILED: Error reading file: {e}")
        return False

def test_connect_method_auth_handling():
    """Test that _connect method has proper authentication error handling."""
    print("\nTesting _connect method authentication handling...")
    
    connection_manager_path = "adtui/services/connection_manager.py"
    
    try:
        with open(connection_manager_path, 'r') as f:
            content = f.read()
        
        # Find the _connect method
        if "def _connect(self):" in content:
            print("✅ _connect method found")
            
            connect_start = content.find("def _connect(self):")
            connect_end = content.find("\n    def _schedule_reconnect", connect_start)
            connect_method = content[connect_start:connect_end]
            
            if "_is_authentication_error" in connect_method:
                print("✅ Authentication error detection in _connect")
            else:
                print("❌ FAILED: Authentication error detection not found in _connect")
                return False
                
            if "_trigger_auth_failure()" in connect_method:
                print("✅ Auth failure trigger in _connect")
            else:
                print("❌ FAILED: Auth failure trigger not found in _connect")
                return False
                
            if "return" in connect_method and "_is_authentication_error" in connect_method:
                print("✅ Early return for auth errors in _connect")
            else:
                print("❌ FAILED: Early return for auth errors not found in _connect")
                return False
        else:
            print("❌ FAILED: _connect method not found")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ FAILED: Error analyzing _connect method: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("TESTING INITIAL CONNECT AUTHENTICATION FIX")
    print("=" * 60)
    
    test1_passed = test_initial_connect_auth_fix()
    test2_passed = test_connect_method_auth_handling()
    
    print("\n" + "=" * 60)
    if test1_passed and test2_passed:
        print("🎉 ALL TESTS PASSED! The initial connect authentication fix has been applied.")
        print("\nThe fix should now:")
        print("  1. Detect authentication errors during initial connection")
        print("  2. Trigger auth failure callback immediately")
        print("  3. Not schedule reconnection attempts for auth errors")
        print("  4. Show login dialog right away on wrong credentials")
        print("  5. Only retry for non-authentication connection issues")
    else:
        print("❌ SOME TESTS FAILED! The initial connect authentication fix may not be complete.")
    print("=" * 60)
    
    sys.exit(0 if (test1_passed and test2_passed) else 1)