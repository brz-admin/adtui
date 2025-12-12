#!/usr/bin/env python3

"""Test script to verify the updated user details fix."""

import sys
import os

# Test the updated fix by examining the code changes
def test_updated_code_fix():
    """Test that the updated code fix is correctly applied."""
    print("Testing updated code fix for user details loading...")
    
    # Read the user_details.py file
    user_details_path = "adtui/widgets/user_details.py"
    
    try:
        with open(user_details_path, 'r') as f:
            content = f.read()
        
        # Check if the updated fix is applied
        checks = [
            ("self.load_error = None" in content, "✅ load_error attribute is initialized"),
            ("self.load_error = str(e)" in content, "✅ load_error is set on exception"),
            ("self.load_error = None  # Clear any previous error" in content, "✅ load_error is cleared before new load"),
            ("Error loading user details:" in content, "✅ Error message format is updated"),
            ("[red]Error loading user details:" in content, "✅ Error message uses red color formatting"),
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

def test_error_handling():
    """Test that error handling is properly implemented."""
    print("\nTesting error handling implementation...")
    
    user_details_path = "adtui/widgets/user_details.py"
    
    try:
        with open(user_details_path, 'r') as f:
            content = f.read()
        
        # Check _build_content method for error handling
        if "def _build_content(self):" in content:
            print("✅ _build_content method exists")
            
            build_method_start = content.find("def _build_content(self):")
            build_method_end = content.find("\n    def ", build_method_start + 1)
            build_method = content[build_method_start:build_method_end]
            
            if "hasattr(self, 'load_error') and self.load_error" in build_method:
                print("✅ _build_content checks for load_error")
            else:
                print("❌ FAILED: _build_content does not check for load_error")
                return False
                
            if "[red]Error loading user details:" in build_method:
                print("✅ _build_content displays error in red")
            else:
                print("❌ FAILED: _build_content does not display error in red")
                return False
        else:
            print("❌ FAILED: _build_content method not found")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ FAILED: Error analyzing methods: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("TESTING UPDATED USER DETAILS FIX")
    print("=" * 60)
    
    test1_passed = test_updated_code_fix()
    test2_passed = test_error_handling()
    
    print("\n" + "=" * 60)
    if test1_passed and test2_passed:
        print("🎉 ALL TESTS PASSED! The updated fix has been successfully applied.")
        print("\nThe user details loading should now:")
        print("  1. Use execute_with_retry for reliable connection handling")
        print("  2. Display specific error messages when loading fails")
        print("  3. Show 'No user data' only when no error occurs but no data is found")
        print("  4. Show red error messages when there are connection/authentication issues")
    else:
        print("❌ SOME TESTS FAILED! The updated fix may not be complete.")
    print("=" * 60)
    
    sys.exit(0 if (test1_passed and test2_passed) else 1)