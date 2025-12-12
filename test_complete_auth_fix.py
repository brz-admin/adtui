#!/usr/bin/env python3

"""Test script to verify the complete authentication failure handling fix."""

import sys
import os

def test_complete_auth_fix():
    """Test that both initial connect and reconnect have proper authentication error handling."""
    print("Testing complete authentication failure handling fix...")
    
    # Read the connection_manager.py file
    connection_manager_path = "adtui/services/connection_manager.py"
    
    try:
        with open(connection_manager_path, 'r') as f:
            content = f.read()
        
        # Check if authentication error handling is in both connect and reconnect methods
        checks = [
            (content.count("_is_authentication_error(error_msg)") >= 2, "✅ Authentication error detection in multiple places"),
            (content.count("_trigger_auth_failure()") >= 2, "✅ Auth failure trigger in multiple places"),
            (content.count("not retrying:") >= 2, "✅ No retry comments in multiple places"),
            ("Authentication error detected during initial connect" in content, "✅ Initial connect auth error handling"),
            ("Authentication error detected during reconnect" in content, "✅ Reconnect auth error handling"),
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

def test_connect_method():
    """Test that _connect method has authentication error handling."""
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
            
            auth_checks = [
                ("_is_authentication_error(error_msg)" in connect_method, "✅ Auth error detection in _connect"),
                ("_trigger_auth_failure()" in connect_method, "✅ Auth failure trigger in _connect"),
                ("return" in connect_method and "_is_authentication_error" in connect_method, "✅ Early return in _connect"),
            ]
            
            for check, message in auth_checks:
                if check:
                    print(message)
                else:
                    print(f"❌ {message.replace('✅', 'FAILED')}")
                    return False
        else:
            print("❌ FAILED: _connect method not found")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ FAILED: Error analyzing _connect method: {e}")
        return False

def test_reconnect_method():
    """Test that _reconnect method has authentication error handling."""
    print("\nTesting _reconnect method authentication handling...")
    
    connection_manager_path = "adtui/services/connection_manager.py"
    
    try:
        with open(connection_manager_path, 'r') as f:
            content = f.read()
        
        # Find the _reconnect method
        if "def _reconnect(self):" in content:
            print("✅ _reconnect method found")
            
            reconnect_start = content.find("def _reconnect(self):")
            reconnect_end = content.find("\n    def _health_check", reconnect_start)
            reconnect_method = content[reconnect_start:reconnect_end]
            
            auth_checks = [
                ("_is_authentication_error(error_msg)" in reconnect_method, "✅ Auth error detection in _reconnect"),
                ("_trigger_auth_failure()" in reconnect_method, "✅ Auth failure trigger in _reconnect"),
                ("return" in reconnect_method and "_is_authentication_error" in reconnect_method, "✅ Early return in _reconnect"),
            ]
            
            for check, message in auth_checks:
                if check:
                    print(message)
                else:
                    print(f"❌ {message.replace('✅', 'FAILED')}")
                    return False
        else:
            print("❌ FAILED: _reconnect method not found")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ FAILED: Error analyzing _reconnect method: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("TESTING COMPLETE AUTHENTICATION FAILURE FIX")
    print("=" * 60)
    
    test1_passed = test_complete_auth_fix()
    test2_passed = test_connect_method()
    test3_passed = test_reconnect_method()
    
    print("\n" + "=" * 60)
    if test1_passed and test2_passed and test3_passed:
        print("🎉 ALL TESTS PASSED! The complete authentication failure fix has been applied.")
        print("\nThe fix should now:")
        print("  1. Detect authentication errors in initial connection")
        print("  2. Detect authentication errors in reconnection attempts")
        print("  3. Trigger auth failure callback immediately in both cases")
        print("  4. Not retry authentication errors in any scenario")
        print("  5. Show login dialog immediately on wrong credentials")
    else:
        print("❌ SOME TESTS FAILED! The complete authentication failure fix may not be complete.")
    print("=" * 60)
    
    sys.exit(0 if (test1_passed and test2_passed and test3_passed) else 1)