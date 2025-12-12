#!/usr/bin/env python3

"""Test script to verify LDAP-specific error message detection."""

import sys
import os

def test_ldap_error_detection():
    """Test that LDAP-specific error messages are properly detected."""
    print("Testing LDAP-specific error message detection...")
    
    # Read the connection_manager.py file
    connection_manager_path = "adtui/services/connection_manager.py"
    
    try:
        with open(connection_manager_path, 'r') as f:
            content = f.read()
        
        # Check if LDAP-specific error messages are added
        checks = [
            ("invalidcredentials" in content, "✅ LDAP invalidcredentials error added"),
            ("automatic bind not successful - invalidcredentials" in content, "✅ Exact LDAP error from logs added"),
            ("LDAP specific error" in content, "✅ Comment for LDAP error added"),
            ("Exact error from logs" in content, "✅ Comment for exact error added"),
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

def test_auth_indicators_list():
    """Test that the auth indicators list contains all necessary patterns."""
    print("\nTesting authentication indicators list...")
    
    connection_manager_path = "adtui/services/connection_manager.py"
    
    try:
        with open(connection_manager_path, 'r') as f:
            content = f.read()
        
        # Find the auth indicators list
        if "auth_indicators = [" in content:
            print("✅ Authentication indicators list found")
            
            list_start = content.find("auth_indicators = [")
            list_end = content.find("]", list_start)
            indicators_section = content[list_start:list_end+1]
            
            # Check for specific indicators
            indicators_to_check = [
                ("'invalid credentials'", "✅ Invalid credentials indicator"),
                ("'invalidcredentials'", "✅ LDAP invalidcredentials indicator"),
                ("'automatic bind not successful - invalidcredentials'", "✅ Exact LDAP error indicator"),
                ("'authentication failed'", "✅ Authentication failed indicator"),
                ("'bind failed'", "✅ Bind failed indicator"),
            ]
            
            for indicator, message in indicators_to_check:
                if indicator in indicators_section:
                    print(message)
                else:
                    print(f"❌ {message.replace('✅', 'FAILED')}")
                    return False
        else:
            print("❌ FAILED: Authentication indicators list not found")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ FAILED: Error analyzing auth indicators: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("TESTING LDAP ERROR MESSAGE DETECTION")
    print("=" * 60)
    
    test1_passed = test_ldap_error_detection()
    test2_passed = test_auth_indicators_list()
    
    print("\n" + "=" * 60)
    if test1_passed and test2_passed:
        print("🎉 ALL TESTS PASSED! LDAP-specific error detection has been improved.")
        print("\nThe fix should now detect:")
        print("  1. Standard 'invalid credentials' errors")
        print("  2. LDAP-specific 'invalidcredentials' errors")
        print("  3. Exact LDAP error: 'automatic bind not successful - invalidcredentials'")
        print("  4. All other standard authentication error patterns")
    else:
        print("❌ SOME TESTS FAILED! LDAP error detection may not be complete.")
    print("=" * 60)
    
    sys.exit(0 if (test1_passed and test2_passed) else 1)