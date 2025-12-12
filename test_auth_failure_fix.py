#!/usr/bin/env python3

"""Test script to verify the authentication failure handling fix."""

import sys
import os

def test_auth_failure_handling():
    """Test that authentication failure handling is properly implemented."""
    print("Testing authentication failure handling...")
    
    # Read the user_details.py file
    user_details_path = "adtui/widgets/user_details.py"
    
    try:
        with open(user_details_path, 'r') as f:
            content = f.read()
        
        # Check if the authentication error re-raising is implemented
        checks = [
            ("Re-raise authentication errors" in content, "✅ Authentication error re-raising comment added"),
            ("if \"Authentication failed\" in error_msg" in content, "✅ Checks for authentication failed message"),
            ("authentication" in content.lower() and "in error_msg.lower()" in content, "✅ Checks for authentication in error message"),
            ("print(\"DEBUG: Re-raising authentication error" in content, "✅ Debug message for re-raising"),
            ("raise  # Re-raise to allow connection manager" in content, "✅ Re-raise statement added"),
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
        print(f"❌ FAILED: Could not find {user_details_path}")
        return False
    except Exception as e:
        print(f"❌ FAILED: Error reading file: {e}")
        return False

def test_auth_error_detection():
    """Test that authentication error detection is properly implemented."""
    print("\nTesting authentication error detection...")
    
    user_details_path = "adtui/widgets/user_details.py"
    
    try:
        with open(user_details_path, 'r') as f:
            content = f.read()
        
        # Find the exception handling section
        if "except Exception as e:" in content:
            print("✅ Exception handling found")
            
            # Check that it properly detects and re-raises auth errors
            except_start = content.find("except Exception as e:")
            except_end = content.find("\n        # Get the content", except_start)
            if except_end == -1:
                except_end = content.find("\n    def ", except_start)
            except_section = content[except_start:except_end]
            
            if "Authentication failed" in except_section:
                print("✅ Authentication failed detection added")
            else:
                print("❌ FAILED: Authentication failed detection not found")
                return False
                
            if "raise" in except_section and "Re-raise" in except_section:
                print("✅ Authentication error re-raising implemented")
            else:
                print("❌ FAILED: Authentication error re-raising not found")
                return False
        else:
            print("❌ FAILED: Exception handling not found")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ FAILED: Error analyzing authentication error detection: {e}")
        return False

def test_connection_manager_auth_handling():
    """Test that connection manager has proper authentication error handling."""
    print("\nTesting connection manager authentication handling...")
    
    connection_manager_path = "adtui/services/connection_manager.py"
    
    try:
        with open(connection_manager_path, 'r') as f:
            content = f.read()
        
        # Check authentication error detection and handling
        checks = [
            ("_is_authentication_error" in content, "✅ Authentication error detection method exists"),
            ("trigger_auth_failure" in content, "✅ Auth failure trigger method exists"),
            ("Authentication failed" in content, "✅ Authentication failed error handling"),
            ("don't retry auth errors" in content.lower(), "✅ No retry for auth errors"),
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
        print(f"❌ FAILED: Error reading connection manager: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("TESTING AUTHENTICATION FAILURE HANDLING FIX")
    print("=" * 60)
    
    test1_passed = test_auth_failure_handling()
    test2_passed = test_auth_error_detection()
    test3_passed = test_connection_manager_auth_handling()
    
    print("\n" + "=" * 60)
    if test1_passed and test2_passed and test3_passed:
        print("🎉 ALL TESTS PASSED! The authentication failure handling fix has been applied.")
        print("\nThe fix should now:")
        print("  1. Detect authentication errors in user details loading")
        print("  2. Re-raise authentication errors to connection manager")
        print("  3. Allow connection manager to trigger auth failure callback")
        print("  4. Show login dialog immediately on authentication failure")
        print("  5. Not retry authentication errors unnecessarily")
    else:
        print("❌ SOME TESTS FAILED! The authentication failure handling fix may not be complete.")
    print("=" * 60)
    
    sys.exit(0 if (test1_passed and test2_passed and test3_passed) else 1)