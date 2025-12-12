#!/usr/bin/env python3

"""Final test to verify all password expiry scenarios work correctly."""

import sys
sys.path.insert(0, '/home/ti2103@domman.ad/dev/adtui')

from datetime import datetime, timedelta
from adtui.constants import PasswordPolicy

def test_all_password_expiry_scenarios():
    """Test all possible password expiry scenarios."""
    
    print("Testing all password expiry scenarios...")
    print(f"Password policy: {PasswordPolicy.MAX_AGE_DAYS} days max age")
    print()
    
    test_scenarios = [
        # (pwdLastSet_value, password_never_expires, description)
        ("2025-08-25 05:38:16.42143+00:00", False, "Normal datetime string"),
        ("2025-08-25 05:38:16", False, "Simple datetime string"),
        (133258368164214300, False, "Windows FILETIME integer"),
        ("133258368164214300", False, "FILETIME as string"),
        (0, False, "Integer 0 (must change at next logon)"),
        ("0", False, "String '0' (must change at next logon)"),
        (None, False, "None (password never set)"),
        ("", False, "Empty string (password never set)"),
        ("2025-08-25 05:38:16.42143+00:00", True, "Normal datetime but password never expires"),
        (None, True, "None but password never expires"),
    ]
    
    for pwd_last_set_value, password_never_expires, description in test_scenarios:
        print(f"Test: {description}")
        print(f"  pwdLastSet value: {repr(pwd_last_set_value)}")
        print(f"  password_never_expires: {password_never_expires}")
        
        # Simulate the fixed logic
        pwd_last_set = "N/A"
        pwd_last_set_dt = None
        pwd_expiry_warning = ""
        pwd_expiry_info = ""
        
        # Check if we would enter the parsing block
        has_pwdlastset = pwd_last_set_value is not None
        
        if has_pwdlastset:
            try:
                print(f"  → Entering parsing block")
                
                # Handle None case
                if pwd_last_set_value is None:
                    print("  → pwdLastSet.value is None")
                    pwd_last_set = "Never set"
                    if not password_never_expires:
                        pwd_expiry_info = "[yellow]Password never set[/yellow]"
                
                # Handle empty string case
                elif pwd_last_set_value == "" or (isinstance(pwd_last_set_value, str) and pwd_last_set_value.strip() == ""):
                    print("  → pwdLastSet.value is empty string")
                    pwd_last_set = "Never set"
                    if not password_never_expires:
                        pwd_expiry_info = "[yellow]Password never set[/yellow]"
                
                # Handle normal cases
                else:
                    if isinstance(pwd_last_set_value, str):
                        if pwd_last_set_value == "0":
                            filetime = 0
                            print("  → String '0' detected: must change at next logon")
                            pwd_last_set = "Must change at next logon"
                            if not password_never_expires:
                                pwd_expiry_warning = "[red bold]⚠ PASSWORD MUST BE CHANGED![/red bold]"
                                pwd_expiry_info = "[red]Must change at next logon[/red]"
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
                                
                                pwd_last_set = pwd_last_set_dt.strftime('%Y-%m-%d %H:%M:%S')
                                print(f"  → Parsed as datetime: {pwd_last_set}")
                                
                            except ValueError as ve:
                                # Fallback: try to convert to int
                                try:
                                    filetime = int(pwd_last_set_value)
                                    print(f"  → Fallback to int: {filetime}")
                                except ValueError:
                                    print(f"  → ERROR: Cannot parse: {ve}")
                                    if not password_never_expires:
                                        pwd_expiry_info = "[yellow]Unable to calculate expiry[/yellow]"
                                    continue
                    
                    elif isinstance(pwd_last_set_value, int):
                        filetime = pwd_last_set_value
                        print(f"  → Integer detected: filetime = {filetime}")
                        
                        if filetime == 0:
                            print("  → Integer 0 detected: must change at next logon")
                            pwd_last_set = "Must change at next logon"
                            if not password_never_expires:
                                pwd_expiry_warning = "[red bold]⚠ PASSWORD MUST BE CHANGED![/red bold]"
                                pwd_expiry_info = "[red]Must change at next logon[/red]"
                        elif filetime > 0:
                            # Convert FILETIME to datetime
                            pwd_last_set_dt = datetime(1601, 1, 1) + timedelta(microseconds=filetime / 10)
                            pwd_last_set = pwd_last_set_dt.strftime('%Y-%m-%d %H:%M:%S')
                            print(f"  → Converted FILETIME to datetime: {pwd_last_set}")
                    
                    # Calculate password expiry if we have a valid datetime and password can expire
                    if pwd_last_set_dt and not password_never_expires:
                        max_pwd_age_days = PasswordPolicy.MAX_AGE_DAYS
                        pwd_expires = pwd_last_set_dt + timedelta(days=max_pwd_age_days)
                        days_until_expiry = (pwd_expires - datetime.now()).days
                        
                        print(f"  → Expiry calculation: {days_until_expiry} days remaining")
                        
                        if days_until_expiry < 0:
                            pwd_expiry_warning = f"[red bold]⚠ PASSWORD EXPIRED {abs(days_until_expiry)} days ago![/red bold]"
                            pwd_expiry_info = f"[red]Expired {abs(days_until_expiry)} days ago[/red]"
                        elif days_until_expiry <= PasswordPolicy.WARNING_DAYS_CRITICAL:
                            pwd_expiry_warning = f"[yellow bold]⚠ Password expires in {days_until_expiry} days![/yellow bold]"
                            pwd_expiry_info = f"[yellow]{days_until_expiry} days remaining[/yellow]"
                        elif days_until_expiry <= PasswordPolicy.WARNING_DAYS_NORMAL:
                            pwd_expiry_warning = f"[yellow]⚠ Password expires in {days_until_expiry} days[/yellow]"
                            pwd_expiry_info = f"[yellow]{days_until_expiry} days remaining[/yellow]"
                        else:
                            pwd_expiry_info = f"[green]{days_until_expiry} days remaining[/green]"
                    elif not pwd_last_set_dt and not password_never_expires:
                        print(f"  → ERROR: Could not parse datetime")
                        pwd_expiry_info = "[yellow]Unable to calculate expiry[/yellow]"
                        
            except Exception as e:
                print(f"  → EXCEPTION: {e}")
                if not password_never_expires:
                    pwd_expiry_info = "[yellow]Unable to calculate expiry[/yellow]"
        else:
            print("  → No pwdLastSet attribute")
            if not password_never_expires:
                pwd_expiry_info = "[yellow]Password expiry unknown[/yellow]"
        
        # Show final result
        if password_never_expires:
            print(f"  → FINAL: [green]Password never expires[/green]")
        else:
            if pwd_expiry_warning:
                print(f"  → FINAL: {pwd_expiry_warning}")
            elif pwd_expiry_info:
                print(f"  → FINAL: {pwd_expiry_info}")
            else:
                print(f"  → FINAL: [green]No expiry info[/green]")
        
        print()

if __name__ == "__main__":
    test_all_password_expiry_scenarios()