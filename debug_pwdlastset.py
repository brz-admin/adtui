#!/usr/bin/env python3

"""Debug script to understand pwdLastSet parsing issues."""

import sys
sys.path.insert(0, '/home/ti2103@domman.ad/dev/adtui')

from datetime import datetime, timedelta
from adtui.constants import PasswordPolicy

def test_pwdlastset_scenarios():
    """Test various pwdLastSet scenarios to understand the issue."""
    
    print("Testing pwdLastSet scenarios...")
    print()
    
    # Test different types of pwdLastSet values that might come from AD
    test_cases = [
        # Case 1: Normal datetime string (this was working in our test)
        "2025-08-25 05:38:16.42143+00:00",
        
        # Case 2: Datetime string without timezone
        "2025-08-25 05:38:16.42143",
        
        # Case 3: Simple datetime string
        "2025-08-25 05:38:16",
        
        # Case 4: Windows FILETIME (large integer)
        133258368164214300,
        
        # Case 5: String representation of FILETIME
        "133258368164214300",
        
        # Case 6: Zero (means must change at next logon)
        0,
        
        # Case 7: String "0"
        "0",
        
        # Case 8: Empty string
        "",
        
        # Case 9: None
        None,
        
        # Case 10: Other numeric values
        1,
        -1,
    ]
    
    for i, test_value in enumerate(test_cases, 1):
        print(f"Test {i}: {repr(test_value)} (type: {type(test_value)})")
        
        # Check if the value would pass the initial condition
        has_pwdlastset = True
        has_value = bool(test_value) if test_value is not None else False
        
        print(f"  hasattr check: {has_pwdlastset}")
        print(f"  value check: {has_value}")
        print(f"  Would enter parsing block: {has_pwdlastset and has_value}")
        
        if has_pwdlastset and has_value:
            try:
                pwd_last_set_value = test_value
                filetime = None
                pwd_last_set_dt = None
                
                # Simulate the parsing logic
                if isinstance(pwd_last_set_value, str):
                    if pwd_last_set_value == "0":
                        filetime = 0
                        print(f"  → String '0' detected: filetime = {filetime}")
                    else:
                        # Parse datetime string
                        try:
                            if '+' in pwd_last_set_value:
                                datetime_part = pwd_last_set_value.split('+')[0].strip()
                                pwd_last_set_dt = datetime.strptime(datetime_part, '%Y-%m-%d %H:%M:%S.%f')
                            else:
                                if '.' in pwd_last_set_value:
                                    pwd_last_set_dt = datetime.strptime(pwd_last_set_value, '%Y-%m-%d %H:%M:%S.%f')
                                else:
                                    pwd_last_set_dt = datetime.strptime(pwd_last_set_value, '%Y-%m-%d %H:%M:%S')
                            
                            print(f"  → Parsed as datetime: {pwd_last_set_dt}")
                            
                        except ValueError as ve:
                            # Fallback: try to convert to int
                            try:
                                filetime = int(pwd_last_set_value)
                                print(f"  → Fallback to int: {filetime}")
                            except ValueError:
                                print(f"  → ERROR: Cannot parse: {ve}")
                                
                elif isinstance(pwd_last_set_value, int):
                    filetime = pwd_last_set_value
                    print(f"  → Integer detected: filetime = {filetime}")
                    
                    if filetime == 0:
                        print(f"  → Special case: Must change at next logon")
                    elif filetime > 0:
                        # Convert FILETIME to datetime
                        pwd_last_set_dt = datetime(1601, 1, 1) + timedelta(microseconds=filetime / 10)
                        print(f"  → Converted FILETIME to datetime: {pwd_last_set_dt}")
                
                # Test expiry calculation
                if pwd_last_set_dt:
                    pwd_expires = pwd_last_set_dt + timedelta(days=PasswordPolicy.MAX_AGE_DAYS)
                    days_until_expiry = (pwd_expires - datetime.now()).days
                    print(f"  → Expiry calculation: {days_until_expiry} days remaining")
                elif filetime is not None:
                    if filetime == 0:
                        print(f"  → Expiry info: Must change at next logon")
                    else:
                        print(f"  → Would convert FILETIME to datetime for expiry calculation")
                        
                
            except Exception as e:
                print(f"  → EXCEPTION: {e}")
                print(f"  → Would show: Unable to calculate expiry")
        else:
            if not has_pwdlastset:
                print(f"  → Would show: Password expiry unknown (no pwdLastSet attribute)")
            else:
                print(f"  → Would show: Password expiry unknown (empty/falsy value)")
        
        print()

if __name__ == "__main__":
    test_pwdlastset_scenarios()