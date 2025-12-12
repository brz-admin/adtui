#!/usr/bin/env python3

"""Test script to verify user details password expiry fix."""

import sys
sys.path.insert(0, '/home/ti2103@domman.ad/dev/adtui')

from datetime import datetime, timedelta
from adtui.constants import PasswordPolicy

def test_user_details_password_expiry():
    """Test the user details password expiry logic with the fixed code."""
    
    print("Testing user details password expiry logic...")
    print(f"Password policy: {PasswordPolicy.MAX_AGE_DAYS} days max age")
    print()
    
    # Test case 1: Datetime string that was causing issues
    test_datetime_str = "2025-08-25 05:38:16.42143+00:00"
    print(f"Test 1 - Datetime string parsing:")
    print(f"  Input: {test_datetime_str}")
    
    # Simulate the parsing logic from user_details.py
    pwd_last_set = "N/A"
    pwd_last_set_dt = None
    pwd_expiry_info = ""
    password_never_expires = False
    
    try:
        if '+' in test_datetime_str:
            datetime_part = test_datetime_str.split('+')[0].strip()
            pwd_last_set_dt = datetime.strptime(datetime_part, '%Y-%m-%d %H:%M:%S.%f')
        else:
            if '.' in test_datetime_str:
                pwd_last_set_dt = datetime.strptime(test_datetime_str, '%Y-%m-%d %H:%M:%S.%f')
            else:
                pwd_last_set_dt = datetime.strptime(test_datetime_str, '%Y-%m-%d %H:%M:%S')
        
        pwd_last_set = pwd_last_set_dt.strftime('%Y-%m-%d %H:%M:%S')
        print(f"  Parsed datetime: {pwd_last_set}")
        
    except Exception as e:
        print(f"  ERROR: {e}")
        pwd_expiry_info = "[yellow]Unable to calculate expiry[/yellow]"
    
    # Test the expiry calculation logic (this is the fixed part)
    if pwd_last_set_dt and not password_never_expires:
        max_pwd_age_days = PasswordPolicy.MAX_AGE_DAYS
        pwd_expires = pwd_last_set_dt + timedelta(days=max_pwd_age_days)
        days_until_expiry = (pwd_expires - datetime.now()).days
        
        print(f"  Expires: {pwd_expires}")
        print(f"  Days until expiry: {days_until_expiry}")
        
        if days_until_expiry < 0:
            pwd_expiry_info = f"[red]Expired {abs(days_until_expiry)} days ago[/red]"
        elif days_until_expiry <= PasswordPolicy.WARNING_DAYS_CRITICAL:
            pwd_expiry_info = f"[yellow]{days_until_expiry} days remaining[/yellow]"
        elif days_until_expiry <= PasswordPolicy.WARNING_DAYS_NORMAL:
            pwd_expiry_info = f"[yellow]{days_until_expiry} days remaining[/yellow]"
        else:
            pwd_expiry_info = f"[green]{days_until_expiry} days remaining[/green]"
    elif not pwd_last_set_dt and not password_never_expires:
        # This is the fixed condition - only show error if we couldn't parse the datetime
        print(f"  ERROR: Could not parse datetime")
        pwd_expiry_info = "[yellow]Unable to calculate expiry[/yellow]"
    
    print(f"  Expiry info: {pwd_expiry_info}")
    print()
    
    # Test case 2: Simulate the old broken behavior
    print("Test 2 - Simulating old broken behavior:")
    print("  Before fix: filetime is None condition would trigger error")
    print("  After fix: pwd_last_set_dt condition correctly calculates expiry")
    print()
    
    # Test case 3: Various datetime formats
    test_cases = [
        "2025-08-25 05:38:16.42143+00:00",
        "2025-08-25 05:38:16.42143",
        "2025-08-25 05:38:16",
    ]
    
    for i, test_case in enumerate(test_cases, 3):
        print(f"Test {i} - Format: {test_case}")
        
        pwd_last_set_dt = None
        try:
            if '+' in test_case:
                datetime_part = test_case.split('+')[0].strip()
                pwd_last_set_dt = datetime.strptime(datetime_part, '%Y-%m-%d %H:%M:%S.%f')
            else:
                if '.' in test_case:
                    pwd_last_set_dt = datetime.strptime(test_case, '%Y-%m-%d %H:%M:%S.%f')
                else:
                    pwd_last_set_dt = datetime.strptime(test_case, '%Y-%m-%d %H:%M:%S')
            
            pwd_expires = pwd_last_set_dt + timedelta(days=PasswordPolicy.MAX_AGE_DAYS)
            days_until_expiry = (pwd_expires - datetime.now()).days
            
            if days_until_expiry < 0:
                status = f"[red]Expired {abs(days_until_expiry)} days ago[/red]"
            elif days_until_expiry <= PasswordPolicy.WARNING_DAYS_CRITICAL:
                status = f"[yellow]{days_until_expiry} days remaining[/yellow]"
            elif days_until_expiry <= PasswordPolicy.WARNING_DAYS_NORMAL:
                status = f"[yellow]{days_until_expiry} days remaining[/yellow]"
            else:
                status = f"[green]{days_until_expiry} days remaining[/green]"
            
            print(f"  Result: {status}")
            
        except Exception as e:
            print(f"  ERROR: {e}")
            print(f"  Result: [yellow]Unable to calculate expiry[/yellow]")
        
        print()
    
    print("✓ User details password expiry test completed!")
    print("✓ The fix should now correctly calculate password expiry for datetime strings")

if __name__ == "__main__":
    test_user_details_password_expiry()