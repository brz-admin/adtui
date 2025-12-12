#!/usr/bin/env python3

"""Test script to verify the password expiry calculation fix."""

import sys
import os

def test_password_expiry_fix():
    """Test that the password expiry calculation fix is correctly applied."""
    print("Testing password expiry calculation fix...")
    
    # Read the user_details.py file
    user_details_path = "adtui/widgets/user_details.py"
    
    try:
        with open(user_details_path, 'r') as f:
            content = f.read()
        
        # Check if the timezone fixes are applied
        checks = [
            ("Handle timezone properly for days calculation" in content, "✅ Timezone handling comment added"),
            ("if pwd_last_set_dt.tzinfo is not None:" in content, "✅ Checks for timezone info"),
            ("now = datetime.now(pwd_last_set_dt.tzinfo)" in content, "✅ Uses timezone-aware now() when available"),
            ("now = datetime.now()" in content, "✅ Falls back to naive datetime when no timezone"),
            ("days_until_expiry = (pwd_expires - now).days" in content, "✅ Uses proper timezone-aware calculation"),
            ("Password expiry unknown (no last set date)" in content, "✅ Better message for missing pwdLastSet"),
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

def test_timezone_handling():
    """Test that timezone handling is properly implemented."""
    print("\nTesting timezone handling implementation...")
    
    user_details_path = "adtui/widgets/user_details.py"
    
    try:
        with open(user_details_path, 'r') as f:
            content = f.read()
        
        # Count timezone handling occurrences
        timezone_checks = content.count("if pwd_last_set_dt.tzinfo is not None:")
        timezone_aware_now = content.count("now = datetime.now(pwd_last_set_dt.tzinfo)")
        
        print(f"✅ Found {timezone_checks} timezone checks")
        print(f"✅ Found {timezone_aware_now} timezone-aware now() calls")
        
        if timezone_checks >= 2 and timezone_aware_now >= 2:
            print("✅ Timezone handling applied in multiple places")
            return True
        else:
            print("❌ FAILED: Timezone handling not applied consistently")
            return False
            
    except Exception as e:
        print(f"❌ FAILED: Error analyzing timezone handling: {e}")
        return False

def test_missing_pwdlastset_handling():
    """Test that missing pwdLastSet is handled properly."""
    print("\nTesting missing pwdLastSet handling...")
    
    user_details_path = "adtui/widgets/user_details.py"
    
    try:
        with open(user_details_path, 'r') as f:
            content = f.read()
        
        # Check for missing pwdLastSet handling
        if "not hasattr(self.entry, 'pwdLastSet') or not self.entry.pwdLastSet.value" in content:
            print("✅ Missing pwdLastSet attribute check added")
        else:
            print("❌ FAILED: Missing pwdLastSet attribute check not found")
            return False
            
        if "Password expiry unknown (no last set date)" in content:
            print("✅ Better error message for missing pwdLastSet")
        else:
            print("❌ FAILED: Better error message not found")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ FAILED: Error analyzing missing pwdLastSet handling: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("TESTING PASSWORD EXPIRY CALCULATION FIX")
    print("=" * 60)
    
    test1_passed = test_password_expiry_fix()
    test2_passed = test_timezone_handling()
    test3_passed = test_missing_pwdlastset_handling()
    
    print("\n" + "=" * 60)
    if test1_passed and test2_passed and test3_passed:
        print("🎉 ALL TESTS PASSED! The password expiry calculation fix has been applied.")
        print("\nThe fix should resolve the 'unable to calculate expiry' issue by:")
        print("  1. Properly handling timezone-aware datetime objects")
        print("  2. Using timezone-aware now() when timezone info is available")
        print("  3. Falling back to naive datetime when no timezone info")
        print("  4. Providing better error messages for missing pwdLastSet")
        print("  5. Applying fixes consistently in all code paths")
    else:
        print("❌ SOME TESTS FAILED! The password expiry calculation fix may not be complete.")
    print("=" * 60)
    
    sys.exit(0 if (test1_passed and test2_passed and test3_passed) else 1)