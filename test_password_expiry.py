#!/usr/bin/env python3

"""Test script to verify password expiry calculation fix."""

import sys
sys.path.insert(0, '/home/ti2103@domman.ad/dev/adtui')

from datetime import datetime, timedelta
from adtui.constants import PasswordPolicy

def test_password_expiry_calculation():
    """Test password expiry calculation with various scenarios."""
    
    print("Testing password expiry calculation...")
    print(f"Password policy: {PasswordPolicy.MAX_AGE_DAYS} days max age")
    print(f"Critical warning: {PasswordPolicy.WARNING_DAYS_CRITICAL} days")
    print(f"Normal warning: {PasswordPolicy.WARNING_DAYS_NORMAL} days")
    print()
    
    # Test case 1: Password set recently (should show green)
    pwd_last_set = datetime.now() - timedelta(days=10)
    pwd_expires = pwd_last_set + timedelta(days=PasswordPolicy.MAX_AGE_DAYS)
    days_until_expiry = (pwd_expires - datetime.now()).days
    
    print(f"Test 1 - Recent password:")
    print(f"  Last set: {pwd_last_set}")
    print(f"  Expires: {pwd_expires}")
    print(f"  Days until expiry: {days_until_expiry}")
    
    if days_until_expiry > PasswordPolicy.WARNING_DAYS_NORMAL:
        status = f"[green]{days_until_expiry} days remaining[/green]"
    elif days_until_expiry <= PasswordPolicy.WARNING_DAYS_CRITICAL:
        status = f"[yellow bold]⚠ Password expires in {days_until_expiry} days![/yellow bold]"
    else:
        status = f"[yellow]⚠ Password expires in {days_until_expiry} days[/yellow]"
    print(f"  Status: {status}")
    print()
    
    # Test case 2: Password about to expire (should show critical warning)
    pwd_last_set = datetime.now() - timedelta(days=PasswordPolicy.MAX_AGE_DAYS - 5)
    pwd_expires = pwd_last_set + timedelta(days=PasswordPolicy.MAX_AGE_DAYS)
    days_until_expiry = (pwd_expires - datetime.now()).days
    
    print(f"Test 2 - About to expire:")
    print(f"  Last set: {pwd_last_set}")
    print(f"  Expires: {pwd_expires}")
    print(f"  Days until expiry: {days_until_expiry}")
    
    if days_until_expiry < 0:
        status = f"[red bold]⚠ PASSWORD EXPIRED {abs(days_until_expiry)} days ago![/red bold]"
    elif days_until_expiry <= PasswordPolicy.WARNING_DAYS_CRITICAL:
        status = f"[yellow bold]⚠ Password expires in {days_until_expiry} days![/yellow bold]"
    elif days_until_expiry <= PasswordPolicy.WARNING_DAYS_NORMAL:
        status = f"[yellow]⚠ Password expires in {days_until_expiry} days[/yellow]"
    else:
        status = f"[green]{days_until_expiry} days remaining[/green]"
    print(f"  Status: {status}")
    print()
    
    # Test case 3: Expired password (should show red)
    pwd_last_set = datetime.now() - timedelta(days=PasswordPolicy.MAX_AGE_DAYS + 10)
    pwd_expires = pwd_last_set + timedelta(days=PasswordPolicy.MAX_AGE_DAYS)
    days_until_expiry = (pwd_expires - datetime.now()).days
    
    print(f"Test 3 - Expired password:")
    print(f"  Last set: {pwd_last_set}")
    print(f"  Expires: {pwd_expires}")
    print(f"  Days until expiry: {days_until_expiry}")
    
    if days_until_expiry < 0:
        status = f"[red bold]⚠ PASSWORD EXPIRED {abs(days_until_expiry)} days ago![/red bold]"
    elif days_until_expiry <= PasswordPolicy.WARNING_DAYS_CRITICAL:
        status = f"[yellow bold]⚠ Password expires in {days_until_expiry} days![/yellow bold]"
    elif days_until_expiry <= PasswordPolicy.WARNING_DAYS_NORMAL:
        status = f"[yellow]⚠ Password expires in {days_until_expiry} days[/yellow]"
    else:
        status = f"[green]{days_until_expiry} days remaining[/green]"
    print(f"  Status: {status}")
    print()
    
    # Test case 4: Parse datetime string like the one causing issues
    test_datetime_str = "2025-08-25 05:38:16.42143+00:00"
    print(f"Test 4 - Parse datetime string:")
    print(f"  Input: {test_datetime_str}")
    
    try:
        if '+' in test_datetime_str:
            datetime_part = test_datetime_str.split('+')[0].strip()
            pwd_last_set_dt = datetime.strptime(datetime_part, '%Y-%m-%d %H:%M:%S.%f')
        else:
            if '.' in test_datetime_str:
                pwd_last_set_dt = datetime.strptime(test_datetime_str, '%Y-%m-%d %H:%M:%S.%f')
            else:
                pwd_last_set_dt = datetime.strptime(test_datetime_str, '%Y-%m-%d %H:%M:%S')
        
        print(f"  Parsed datetime: {pwd_last_set_dt}")
        
        # Calculate expiry
        pwd_expires = pwd_last_set_dt + timedelta(days=PasswordPolicy.MAX_AGE_DAYS)
        days_until_expiry = (pwd_expires - datetime.now()).days
        print(f"  Expires: {pwd_expires}")
        print(f"  Days until expiry: {days_until_expiry}")
        
        if days_until_expiry < 0:
            status = f"[red bold]⚠ PASSWORD EXPIRED {abs(days_until_expiry)} days ago![/red bold]"
        elif days_until_expiry <= PasswordPolicy.WARNING_DAYS_CRITICAL:
            status = f"[yellow bold]⚠ Password expires in {days_until_expiry} days![/yellow bold]"
        elif days_until_expiry <= PasswordPolicy.WARNING_DAYS_NORMAL:
            status = f"[yellow]⚠ Password expires in {days_until_expiry} days[/yellow]"
        else:
            status = f"[green]{days_until_expiry} days remaining[/green]"
        print(f"  Status: {status}")
        
    except Exception as e:
        print(f"  ERROR: {e}")
        print(f"  Status: [yellow]Unable to calculate expiry[/yellow]")
    
    print("\n✓ Password expiry calculation test completed!")

if __name__ == "__main__":
    test_password_expiry_calculation()