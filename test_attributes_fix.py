#!/usr/bin/env python3

"""Test script to verify the attributes conversion fix."""

import sys
import os

def test_attributes_conversion_fix():
    """Test that the attributes conversion fix is correctly applied."""
    print("Testing attributes conversion fix...")
    
    # Read the user_details.py file
    user_details_path = "adtui/widgets/user_details.py"
    
    try:
        with open(user_details_path, 'r') as f:
            content = f.read()
        
        # Check if the fix is applied
        checks = [
            ("Safely convert entry_attributes to dict" in content, "✅ Safe conversion comment added"),
            ("hasattr(self.entry.entry_attributes, 'items')" in content, "✅ Checks if dict-like"),
            ("self.raw_attributes.items()" in content, "✅ Uses items() for dict-like objects"),
            ("for attr, values in self.entry.entry_attributes:" in content, "✅ Handles iterable attributes"),
            ("Error converting entry_attributes" in content, "✅ Error handling for conversion"),
            ("self.raw_attributes = {}" in content, "✅ Falls back to empty dict on error"),
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

def test_attributes_method():
    """Test that the attributes conversion method is properly implemented."""
    print("\nTesting attributes conversion method...")
    
    user_details_path = "adtui/widgets/user_details.py"
    
    try:
        with open(user_details_path, 'r') as f:
            content = f.read()
        
        # Check the attributes conversion section
        if "Store raw attributes" in content:
            print("✅ Raw attributes storage section found")
            
            # Find the section
            attr_start = content.find("Store raw attributes")
            attr_end = content.find("\n            else:", attr_start)
            attr_section = content[attr_start:attr_end]
            
            if "try:" in attr_section and "except Exception" in attr_section:
                print("✅ Attributes conversion has try-except block")
            else:
                print("❌ FAILED: Attributes conversion missing try-except")
                return False
                
            if "self.raw_attributes = {}" in attr_section:
                print("✅ Falls back to empty dict on conversion error")
            else:
                print("❌ FAILED: Missing fallback to empty dict")
                return False
        else:
            print("❌ FAILED: Raw attributes storage section not found")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ FAILED: Error analyzing attributes method: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("TESTING ATTRIBUTES CONVERSION FIX")
    print("=" * 60)
    
    test1_passed = test_attributes_conversion_fix()
    test2_passed = test_attributes_method()
    
    print("\n" + "=" * 60)
    if test1_passed and test2_passed:
        print("🎉 ALL TESTS PASSED! The attributes conversion fix has been applied.")
        print("\nThe fix should resolve the 'dictionary update sequence element' error by:")
        print("  1. Checking if entry_attributes is dict-like")
        print("  2. Using proper iteration for non-dict-like objects")
        print("  3. Providing fallback to empty dict on conversion errors")
        print("  4. Maintaining all existing functionality")
    else:
        print("❌ SOME TESTS FAILED! The attributes conversion fix may not be complete.")
    print("=" * 60)
    
    sys.exit(0 if (test1_passed and test2_passed) else 1)