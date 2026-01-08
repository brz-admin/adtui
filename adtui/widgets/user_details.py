"""User details pane widget for displaying AD user information."""

import logging
import os
import sys
from datetime import datetime, timedelta
from typing import Optional, Tuple, Any

from textual.widgets import Static
from ldap3 import MODIFY_REPLACE, MODIFY_ADD, MODIFY_DELETE

# Add parent directory to path to import constants
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from constants import PasswordPolicy, UserAccountControl

logger = logging.getLogger(__name__)


class UserDetailsPane(Static):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user_dn = None
        self.connection_manager = None
        self.entry = None
        self.member_of = []
        self.raw_attributes = {}
        self.load_error = None

    def update_user_details(self, user_dn, connection_manager):
        """Load and display user details."""

        self.user_dn = user_dn
        self.connection_manager = connection_manager
        self.load_error = None  # Clear any previous error
        self.load_user_details()

        if not self.entry:
            logger.debug("No entry found after load_user_details for %s", user_dn)

    def load_user_details(self) -> None:
        """Fetch user details from LDAP."""

        try:

            def search_user_op(conn):
                conn.search(
                    self.user_dn,
                    "(objectClass=*)",
                    search_scope="BASE",
                    attributes=["*"],
                )
                return conn.entries

            entries = self.connection_manager.execute_with_retry(search_user_op)

            if entries:
                self.entry = entries[0]

                # Extract member of groups (just the CN)
                if hasattr(self.entry, "memberOf") and self.entry.memberOf:
                    self.member_of = [
                        {"name": dn.split(",")[0].split("=")[1], "dn": dn}
                        for dn in self.entry.memberOf.values
                    ]
                else:
                    self.member_of = []

                # Store raw attributes
                if hasattr(self.entry, "entry_attributes"):
                    try:
                        # Safely convert entry_attributes to dict
                        if hasattr(self.entry.entry_attributes, "items"):
                            # If it's already dict-like
                            self.raw_attributes = dict(
                                self.entry.entry_attributes.items()
                            )
                        else:
                            # Try direct conversion, handle potential errors
                            self.raw_attributes = {}
                            for attr, values in self.entry.entry_attributes:
                                self.raw_attributes[attr] = values
                    except Exception as e:
                        logger.warning("Failed to convert entry_attributes: %s", e)
                        self.raw_attributes = {}
            else:
                logger.debug("No entries found in search results for %s", self.user_dn)
                self.entry = None
        except Exception as e:
            logger.error("Error loading user details for %s: %s", self.user_dn, e)

            # Set entry to None but also store the error message for display
            self.entry = None
            self.load_error = str(e)

            # Re-raise authentication errors so they can be handled by connection manager
            error_msg = str(e)
            if (
                "Authentication failed" in error_msg
                or "authentication" in error_msg.lower()
            ):
                logger.debug("Re-raising authentication error for proper handling")
                raise  # Re-raise to allow connection manager to handle it

    def refresh_display(self):
        """Refresh the displayed content."""
        if not self.entry:
            return "[red]Error loading user details[/red]"

        # Build the display content
        return self._build_content()

    def _build_content(self) -> str:
        """Build the content string for display."""

        if not self.entry:
            if hasattr(self, "load_error") and self.load_error:
                return f"[red]Error loading user details: {self.load_error}[/red]"
            else:
                logger.debug("No entry found, returning 'No user data'")
                return "No user data"

        # General Information
        cn = str(self.entry.cn.value) if hasattr(self.entry, "cn") else "N/A"
        sam = (
            str(self.entry.sAMAccountName.value)
            if hasattr(self.entry, "sAMAccountName")
            else "N/A"
        )
        display_name = (
            str(self.entry.displayName.value)
            if hasattr(self.entry, "displayName")
            else "N/A"
        )
        mail = str(self.entry.mail.value) if hasattr(self.entry, "mail") else "N/A"
        profile_path = (
            str(self.entry.profilePath.value)
            if hasattr(self.entry, "profilePath")
            else "N/A"
        )
        home_dir = (
            str(self.entry.homeDirectory.value)
            if hasattr(self.entry, "homeDirectory")
            else "N/A"
        )

        # Account status
        uac = (
            int(self.entry.userAccountControl.value)
            if hasattr(self.entry, "userAccountControl")
            else 0
        )
        is_disabled = (uac & 0x0002) != 0
        is_locked = (uac & 0x0010) != 0
        password_never_expires = (uac & 0x10000) != 0

        # Password last set and expiry calculation
        pwd_last_set = "N/A"
        pwd_last_set_dt = None
        pwd_expiry_warning = ""
        pwd_expiry_info = ""

        if hasattr(self.entry, "pwdLastSet") and self.entry.pwdLastSet.value:
            try:
                # Handle different data types for pwdLastSet
                pwd_last_set_value = self.entry.pwdLastSet.value

                # Initialize variables
                filetime = None
                pwd_last_set_dt = None

                if isinstance(pwd_last_set_value, str):
                    if pwd_last_set_value == "0":
                        filetime = 0
                    else:
                        # Parse datetime string format: "2025-08-25 05:38:16.421434+00:00"
                        try:
                            from datetime import datetime as dt

                            # Handle timezone-aware datetime strings
                            if "+" in pwd_last_set_value:
                                # Split timezone part
                                datetime_part = pwd_last_set_value.split("+")[0].strip()
                                pwd_last_set_dt = dt.strptime(
                                    datetime_part, "%Y-%m-%d %H:%M:%S.%f"
                                )
                            else:
                                # Handle format without timezone
                                if "." in pwd_last_set_value:
                                    pwd_last_set_dt = dt.strptime(
                                        pwd_last_set_value, "%Y-%m-%d %H:%M:%S.%f"
                                    )
                                else:
                                    pwd_last_set_dt = dt.strptime(
                                        pwd_last_set_value, "%Y-%m-%d %H:%M:%S"
                                    )

                            pwd_last_set = pwd_last_set_dt.strftime("%Y-%m-%d %H:%M:%S")
                            filetime = None  # We don't need filetime conversion

                        except ValueError as ve:
                            # Fallback: try to convert to int if it's actually a numeric string
                            try:
                                filetime = int(pwd_last_set_value)
                            except ValueError:
                                raise Exception(
                                    f"Cannot parse pwdLastSet value: {pwd_last_set_value}"
                                )

                elif isinstance(pwd_last_set_value, int):
                    # Handle Windows FILETIME integer format
                    filetime = pwd_last_set_value
                else:
                    # Try to convert to int if it's numeric
                    try:
                        filetime = int(pwd_last_set_value)
                    except (ValueError, TypeError):
                        raise Exception(
                            f"Unsupported pwdLastSet type: {type(pwd_last_set_value)}"
                        )

                if filetime == 0:
                    # pwdLastSet = 0 means "user must change password at next logon"
                    pwd_last_set = "Must change at next logon"
                    if not password_never_expires:
                        pwd_expiry_warning = (
                            "[red bold]⚠ PASSWORD MUST BE CHANGED![/red bold]"
                        )
                        pwd_expiry_info = "[red]Must change at next logon[/red]"
                elif filetime is not None and filetime > 0:
                    # Handle Windows FILETIME format
                    pwd_last_set_dt = datetime(1601, 1, 1) + timedelta(
                        microseconds=filetime / 10
                    )
                    pwd_last_set = pwd_last_set_dt.strftime("%Y-%m-%d %H:%M:%S")

                # Calculate password expiry if we have a valid datetime
                if pwd_last_set_dt and not password_never_expires:
                    max_pwd_age_days = PasswordPolicy.MAX_AGE_DAYS
                    pwd_expires = pwd_last_set_dt + timedelta(days=max_pwd_age_days)

                    # Handle timezone properly for days calculation
                    if pwd_last_set_dt.tzinfo is not None:
                        # If we have timezone info, use timezone-aware now()
                        now = datetime.now(pwd_last_set_dt.tzinfo)
                    else:
                        # If no timezone info, use naive datetime
                        now = datetime.now()

                    days_until_expiry = (pwd_expires - now).days

                    if days_until_expiry < 0:
                        pwd_expiry_warning = f"[red bold]⚠ PASSWORD EXPIRED {abs(days_until_expiry)} days ago![/red bold]"
                        pwd_expiry_info = (
                            f"[red]Expired {abs(days_until_expiry)} days ago[/red]"
                        )
                    elif days_until_expiry <= PasswordPolicy.WARNING_DAYS_CRITICAL:
                        pwd_expiry_warning = f"[yellow bold]⚠ Password expires in {days_until_expiry} days![/yellow bold]"
                        pwd_expiry_info = (
                            f"[yellow]{days_until_expiry} days remaining[/yellow]"
                        )
                    elif days_until_expiry <= PasswordPolicy.WARNING_DAYS_NORMAL:
                        pwd_expiry_warning = f"[yellow]⚠ Password expires in {days_until_expiry} days[/yellow]"
                        pwd_expiry_info = (
                            f"[yellow]{days_until_expiry} days remaining[/yellow]"
                        )
                    else:
                        pwd_expiry_info = (
                            f"[green]{days_until_expiry} days remaining[/green]"
                        )
                elif not pwd_last_set_dt and not password_never_expires:
                    # We have pwdLastSet but couldn't parse it properly

                    pwd_expiry_info = "[yellow]Unable to calculate expiry[/yellow]"
                elif (
                    not hasattr(self.entry, "pwdLastSet")
                    or not self.entry.pwdLastSet.value
                ):
                    # No pwdLastSet attribute at all
                    if not password_never_expires:
                        logger.debug(
                            "No pwdLastSet attribute found, cannot calculate expiry"
                        )
                        pwd_expiry_info = "[yellow]Password expiry unknown (no last set date)[/yellow]"
            except Exception as e:
                pwd_last_set_value = self.entry.pwdLastSet.value
                pwd_last_set = str(pwd_last_set_value)

                logger.debug("Error parsing pwdLastSet: %s", e)

                # Special handling for FILETIME strings that failed datetime parsing
                if isinstance(pwd_last_set_value, str) and pwd_last_set_value.isdigit():
                    try:
                        filetime = int(pwd_last_set_value)

                        if filetime > 0:
                            # Convert FILETIME to datetime
                            pwd_last_set_dt = datetime(1601, 1, 1) + timedelta(
                                microseconds=filetime / 10
                            )
                            pwd_last_set = pwd_last_set_dt.strftime("%Y-%m-%d %H:%M:%S")

                            # Calculate password expiry
                            if not password_never_expires:
                                max_pwd_age_days = PasswordPolicy.MAX_AGE_DAYS
                                pwd_expires = pwd_last_set_dt + timedelta(
                                    days=max_pwd_age_days
                                )

                                # Handle timezone properly for days calculation
                                if pwd_last_set_dt.tzinfo is not None:
                                    now = datetime.now(pwd_last_set_dt.tzinfo)
                                else:
                                    now = datetime.now()

                                days_until_expiry = (pwd_expires - now).days

                                if days_until_expiry < 0:
                                    pwd_expiry_warning = f"[red bold]⚠ PASSWORD EXPIRED {abs(days_until_expiry)} days ago![/red bold]"
                                    pwd_expiry_info = f"[red]Expired {abs(days_until_expiry)} days ago[/red]"
                                elif (
                                    days_until_expiry
                                    <= PasswordPolicy.WARNING_DAYS_CRITICAL
                                ):
                                    pwd_expiry_warning = f"[yellow bold]⚠ Password expires in {days_until_expiry} days![/yellow bold]"
                                    pwd_expiry_info = f"[yellow]{days_until_expiry} days remaining[/yellow]"
                                elif (
                                    days_until_expiry
                                    <= PasswordPolicy.WARNING_DAYS_NORMAL
                                ):
                                    pwd_expiry_warning = f"[yellow]⚠ Password expires in {days_until_expiry} days[/yellow]"
                                    pwd_expiry_info = f"[yellow]{days_until_expiry} days remaining[/yellow]"
                                else:
                                    pwd_expiry_info = f"[green]{days_until_expiry} days remaining[/green]"
                        elif filetime == 0:
                            logger.debug(
                                "FILETIME 0 detected: must change at next logon"
                            )
                            pwd_last_set = "Must change at next logon"
                            if not password_never_expires:
                                pwd_expiry_warning = (
                                    "[red bold]⚠ PASSWORD MUST BE CHANGED![/red bold]"
                                )
                                pwd_expiry_info = "[red]Must change at next logon[/red]"
                    except ValueError:
                        pass  # Fall through to unable to calculate

                # If we still don't have expiry info, show unable to calculate
                if (
                    not pwd_expiry_info
                    and not pwd_expiry_warning
                    and not password_never_expires
                ):
                    pwd_expiry_info = "[yellow]Unable to calculate expiry[/yellow]"
        else:
            # If password can expire but we can't get pwdLastSet, show that info
            if not password_never_expires:
                pwd_expiry_info = "[yellow]Password expiry unknown[/yellow]"

        # Account expiry
        account_expiry_warning = ""
        if hasattr(self.entry, "accountExpires") and self.entry.accountExpires.value:
            try:
                account_expires_filetime = int(self.entry.accountExpires.value)
                # 0 or 9223372036854775807 (0x7FFFFFFFFFFFFFFF) means never expires
                if account_expires_filetime not in [0, 9223372036854775807]:
                    account_expires_dt = datetime(1601, 1, 1) + timedelta(
                        microseconds=account_expires_filetime / 10
                    )
                    days_until_account_expiry = (
                        account_expires_dt - datetime.now()
                    ).days

                    if days_until_account_expiry < 0:
                        account_expiry_warning = f"[red bold]⚠ ACCOUNT EXPIRED {abs(days_until_account_expiry)} days ago![/red bold]"
                    elif days_until_account_expiry <= 7:
                        account_expiry_warning = f"[yellow bold]⚠ Account expires in {days_until_account_expiry} days![/yellow bold]"
                    elif days_until_account_expiry <= 30:
                        account_expiry_warning = f"[yellow]⚠ Account expires in {days_until_account_expiry} days[/yellow]"
            except Exception as e:
                logger.debug("Error parsing accountExpires: %s", e)

        # Build the content with alerts
        alerts = ""
        if pwd_expiry_warning:
            alerts += f"\n{pwd_expiry_warning}\n"
        if account_expiry_warning:
            alerts += f"\n{account_expiry_warning}\n"

        content = f"""[bold cyan]User Details[/bold cyan]{alerts}

[bold]General Information:[/bold]
Common Name: {cn}
Username (sAMAccountName): {sam}
Display Name: {display_name}
Email: {mail}
Profile Path: {profile_path}
Home Directory: {home_dir}

[bold]Account Status:[/bold]
Disabled: {"[red]Yes[/red]" if is_disabled else "[green]No[/green]"}
Locked: {"[red]Yes[/red]" if is_locked else "[green]No[/green]"}
Password Never Expires: {"Yes" if password_never_expires else "No"}
Password Last Set: {pwd_last_set}{" - " + pwd_expiry_info if pwd_expiry_info and not password_never_expires else ""}

[bold]Member Of ({len(self.member_of)} groups):[/bold]
"""

        if self.member_of:
            for group in self.member_of:
                content += f"  • {group['name']}\n"
        else:
            content += "  No group memberships\n"

        content += "\n[dim]Press 'a' to edit attributes | 'g' to manage groups | 'p' to set password | 'e' to enable account[/dim]"

        return content

    def get_raw_attributes_text(self):
        """Get formatted raw attributes."""
        if not self.raw_attributes:
            return "No attributes available"

        lines = ["[bold cyan]Raw LDAP Attributes[/bold cyan]\n"]
        for attr, values in sorted(self.raw_attributes.items()):
            if isinstance(values, list):
                if len(values) == 1:
                    lines.append(f"[bold]{attr}:[/bold] {values[0]}")
                else:
                    lines.append(f"[bold]{attr}:[/bold]")
                    for val in values:
                        lines.append(f"  • {val}")
            else:
                lines.append(f"[bold]{attr}:[/bold] {values}")

        return "\n".join(lines)

    def modify_attribute(self, attribute: str, value: Any) -> bool:
        """Modify a user attribute."""
        try:

            def modify_attr_op(conn):
                conn.modify(self.user_dn, {attribute: [(MODIFY_REPLACE, [value])]})
                return conn.result

            result = self.connection_manager.execute_with_retry(modify_attr_op)
            if result["result"] == 0:
                logger.info(
                    "Successfully modified attribute %s for user %s",
                    attribute,
                    self.user_dn,
                )
                self.load_user_details()
                return True
            else:
                logger.warning(
                    "Failed to modify attribute: %s",
                    result.get("description", "Unknown error"),
                )
                return False
        except Exception as e:
            logger.error("Error modifying attribute: %s", e)
            return False

    def add_to_group(self, group_dn: str) -> bool:
        """Add user to a group."""
        try:

            def add_to_group_op(conn):
                conn.modify(group_dn, {"member": [(MODIFY_ADD, [self.user_dn])]})
                return conn.result

            result = self.connection_manager.execute_with_retry(add_to_group_op)
            if result["result"] == 0:
                logger.info(
                    "Successfully added user %s to group %s", self.user_dn, group_dn
                )
                self.load_user_details()
                return True
            else:
                logger.warning(
                    "Failed to add to group: %s",
                    result.get("description", "Unknown error"),
                )
                return False
        except Exception as e:
            logger.error("Error adding user to group: %s", e)
            return False

    def remove_from_group(self, group_dn: str) -> bool:
        """Remove user from a group."""
        try:

            def remove_from_group_op(conn):
                conn.modify(group_dn, {"member": [(MODIFY_DELETE, [self.user_dn])]})
                return conn.result

            result = self.connection_manager.execute_with_retry(remove_from_group_op)
            if result["result"] == 0:
                logger.info(
                    "Successfully removed user %s from group %s", self.user_dn, group_dn
                )
                self.load_user_details()
                return True
            else:
                logger.warning(
                    "Failed to remove from group: %s",
                    result.get("description", "Unknown error"),
                )
                return False
        except Exception as e:
            logger.error("Error removing user from group: %s", e)
            return False

    def unlock_account(self):
        """Unlock the user account."""
        try:
            success, message = self._unlock_account_via_service()
            if success:
                self.load_user_details()  # Refresh the display
            return success
        except Exception as e:
            return False

    def _unlock_account_via_service(self) -> Tuple[bool, str]:
        """Unlock account using LDAP connection."""
        try:
            # Check if account is actually locked first
            if not self.is_account_locked():
                return False, "Account is not currently locked"

            # Unlock by clearing lockoutTime and resetting badPwdCount
            changes = {
                "lockoutTime": [(MODIFY_REPLACE, ["0"])],
                "badPwdCount": [(MODIFY_REPLACE, ["0"])],
            }

            def unlock_op(conn):
                conn.modify(self.user_dn, changes)
                return conn.result

            result = self.connection_manager.execute_with_retry(unlock_op)

            if result["result"] == 0:
                logger.info("Account successfully unlocked: %s", self.user_dn)
                return True, "Account successfully unlocked"
            else:
                logger.warning(
                    "Unlock failed: %s", result.get("message", "Unknown error")
                )
                return False, f"Unlock failed: {result.get('message', 'Unknown error')}"
        except Exception as e:
            logger.error("Error unlocking account: %s", e)
            return False, f"Error unlocking account: {e}"

    def is_account_locked(self) -> bool:
        """Check if account is currently locked."""
        if not self.entry:
            return False

        # Check lockoutTime attribute
        if hasattr(self.entry, "lockoutTime") and self.entry.lockoutTime.value:
            lockout_time = int(self.entry.lockoutTime.value)
            return lockout_time != 0

        return False

    def enable_account(self):
        """Enable the user account."""
        try:
            success, message = self._enable_account_via_service()
            if success:
                self.load_user_details()  # Refresh the display
            return success
        except Exception as e:
            return False

    def _enable_account_via_service(self) -> Tuple[bool, str]:
        """Enable account using LDAP service."""
        try:
            # Check if account is actually disabled first
            if not self.is_account_disabled():
                return False, "Account is not currently disabled"

            # Import LDAP service to use the enable method
            from services.ldap_service import LDAPService

            ldap_service = LDAPService(self.connection_manager, "")

            return ldap_service.enable_user_account(self.user_dn)
        except Exception as e:
            return False, f"Error enabling account: {e}"

    def is_account_disabled(self) -> bool:
        """Check if account is currently disabled."""
        if not self.entry:
            return False

        # Check userAccountControl attribute for ACCOUNTDISABLE flag (0x0002)
        if (
            hasattr(self.entry, "userAccountControl")
            and self.entry.userAccountControl.value
        ):
            uac = int(self.entry.userAccountControl.value)
            return (uac & 0x0002) != 0

        return False

    def disable_account(self):
        """Disable the user account."""
        try:
            success, message = self._disable_account_via_service()
            if success:
                self.load_user_details()  # Refresh the display
            return success
        except Exception as e:
            return False

    def _disable_account_via_service(self) -> Tuple[bool, str]:
        """Disable account using LDAP service."""
        try:
            # Check if account is actually enabled first
            if self.is_account_disabled():
                return False, "Account is already disabled"

            # Import LDAP service to use the disable method
            from services.ldap_service import LDAPService

            ldap_service = LDAPService(self.connection_manager, "")

            return ldap_service.disable_user_account(self.user_dn)
        except Exception as e:
            return False, f"Error disabling account: {e}"

        # Check userAccountControl attribute for ACCOUNTDISABLE flag (0x0002)
        if (
            hasattr(self.entry, "userAccountControl")
            and self.entry.userAccountControl.value
        ):
            uac = int(self.entry.userAccountControl.value)
            return (uac & 0x0002) != 0

        return False
