#!/usr/bin/env python3

"""Simple test to verify the user details fix without dependencies."""

import sys
import os

# Test the fix by examining the code changes
def test_code_fix():
    """Test that the code fix is correctly applied."""
    print("Testing code fix for user details loading...")
    
    # Read the user_details.py file
    user_details_path = "adtui/widgets/user_details.py"
    
    try:
        with open(user_details_path, 'r') as f:
            content = f.read()
        
        # Check if the fix is applied
        checks = [
            ("execute_with_retry" in content, "✅ execute_with_retry is used"),
            ("search_user_op" in content, "✅ search_user_op function is defined"),
            ("conn = self.connection_manager.get_connection()" not in content, "✅ Old get_connection() call is removed"),
            ("self.connection_error" not in content, "✅ connection_error attribute is removed"),
            ("Connection not available" not in content, "✅ Old error message is removed"),
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

def test_key_methods():
    """Test that key methods have the expected structure."""
    print("\nTesting key method structures...")
    
    user_details_path = "adtui/widgets/user_details.py"
    
    try:
        with open(user_details_path, 'r') as f:
            content = f.read()
        
        # Check load_user_details method structure
        if "def load_user_details(self):" in content:
            print("✅ load_user_details method exists")
            
            # Check that it uses execute_with_retry
            load_method_start = content.find("def load_user_details(self):")
            load_method_end = content.find("\n    def ", load_method_start + 1)
            load_method = content[load_method_start:load_method_end]
            
            if "execute_with_retry" in load_method:
                print("✅ load_user_details uses execute_with_retry")
            else:
                print("❌ FAILED: load_user_details does not use execute_with_retry")
                return False
                
            if "get_connection()" in load_method:
                print("❌ FAILED: load_user_details still uses get_connection()")
                return False
            else:
                print("✅ load_user_details does not use get_connection()")
        else:
            print("❌ FAILED: load_user_details method not found")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ FAILED: Error analyzing methods: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("TESTING USER DETAILS FIX")
    print("=" * 60)
    
    test1_passed = test_code_fix()
    test2_passed = test_key_methods()
    
    print("\n" + "=" * 60)
    if test1_passed and test2_passed:
        print("🎉 ALL TESTS PASSED! The fix has been successfully applied.")
        print("\nThe user details loading should now work correctly by:")
        print("  1. Using execute_with_retry instead of get_connection()")
        print("  2. Following the same pattern as GroupDetailsPane")
        print("  3. Properly handling connection retries and errors")
    else:
        print("❌ SOME TESTS FAILED! The fix may not be complete.")
    print("=" * 60)
    
    sys.exit(0 if (test1_passed and test2_passed) else 1)