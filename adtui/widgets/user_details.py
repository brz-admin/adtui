from textual.widgets import Static, TabbedContent, TabPane, Static as StaticWidget, Label, Button, Input, ListView, ListItem
from textual.containers import ScrollableContainer, Vertical, Horizontal
from textual.app import ComposeResult
from datetime import datetime, timedelta
from ldap3 import MODIFY_REPLACE, MODIFY_ADD, MODIFY_DELETE

class UserDetailsPane(Static):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user_dn = None
        self.conn = None
        self.entry = None
        self.member_of = []
        self.raw_attributes = {}

    def update_user_details(self, user_dn, conn):
        """Load and display user details."""
        print(f"update_user_details called with DN: {user_dn}")
        self.user_dn = user_dn
        self.conn = conn
        self.load_user_details()
        print(f"load_user_details completed. Entry: {self.entry is not None}")

    def load_user_details(self):
        """Fetch user details from LDAP."""
        print(f"load_user_details: Searching for {self.user_dn}")
        try:
            self.conn.search(
                self.user_dn,
                '(objectClass=*)',
                search_scope='BASE',
                attributes=['*']
            )
            print(f"Search completed. Entries found: {len(self.conn.entries)}")
            if self.conn.entries:
                self.entry = self.conn.entries[0]
                # Extract member of groups (just the CN)
                if hasattr(self.entry, 'memberOf') and self.entry.memberOf:
                    self.member_of = [
                        {
                            'name': dn.split(',')[0].split('=')[1],
                            'dn': dn
                        }
                        for dn in self.entry.memberOf.values
                    ]
                else:
                    self.member_of = []
                
                # Store raw attributes
                if hasattr(self.entry, 'entry_attributes'):
                    self.raw_attributes = dict(self.entry.entry_attributes)
        except Exception as e:
            print(f"Error loading user details: {e}")
            import traceback
            traceback.print_exc()

    def refresh_display(self):
        """Refresh the displayed content."""
        if not self.entry:
            return "[red]Error loading user details[/red]"
        
        # Build the display content
        return self._build_content()

    def _build_content(self):
        """Build the content string for display."""
        print(f"_build_content called. Entry exists: {self.entry is not None}")
        if not self.entry:
            print("No entry found, returning 'No user data'")
            return "No user data"
        
        # General Information
        cn = str(self.entry.cn.value) if hasattr(self.entry, 'cn') else "N/A"
        sam = str(self.entry.sAMAccountName.value) if hasattr(self.entry, 'sAMAccountName') else "N/A"
        display_name = str(self.entry.displayName.value) if hasattr(self.entry, 'displayName') else "N/A"
        mail = str(self.entry.mail.value) if hasattr(self.entry, 'mail') else "N/A"
        profile_path = str(self.entry.profilePath.value) if hasattr(self.entry, 'profilePath') else "N/A"
        home_dir = str(self.entry.homeDirectory.value) if hasattr(self.entry, 'homeDirectory') else "N/A"
        
        # Account status
        uac = int(self.entry.userAccountControl.value) if hasattr(self.entry, 'userAccountControl') else 0
        is_disabled = (uac & 0x0002) != 0
        is_locked = (uac & 0x0010) != 0
        password_never_expires = (uac & 0x10000) != 0
        
        # Password last set and expiry calculation
        pwd_last_set = "N/A"
        pwd_last_set_dt = None
        pwd_expiry_warning = ""
        
        if hasattr(self.entry, 'pwdLastSet') and self.entry.pwdLastSet.value:
            try:
                # Convert Windows FILETIME to datetime
                filetime = int(self.entry.pwdLastSet.value)
                if filetime > 0:
                    pwd_last_set_dt = datetime(1601, 1, 1) + timedelta(microseconds=filetime / 10)
                    pwd_last_set = pwd_last_set_dt.strftime('%Y-%m-%d %H:%M:%S')
                    
                    # Calculate password expiry (default domain policy is typically 42 days)
                    # This should ideally be fetched from domain policy
                    if not password_never_expires:
                        max_pwd_age_days = 42  # Default, should be from domain policy
                        pwd_expires = pwd_last_set_dt + timedelta(days=max_pwd_age_days)
                        days_until_expiry = (pwd_expires - datetime.now()).days
                        
                        if days_until_expiry < 0:
                            pwd_expiry_warning = f"[red bold]⚠ PASSWORD EXPIRED {abs(days_until_expiry)} days ago![/red bold]"
                        elif days_until_expiry <= 7:
                            pwd_expiry_warning = f"[yellow bold]⚠ Password expires in {days_until_expiry} days![/yellow bold]"
                        elif days_until_expiry <= 14:
                            pwd_expiry_warning = f"[yellow]⚠ Password expires in {days_until_expiry} days[/yellow]"
            except:
                pwd_last_set = str(self.entry.pwdLastSet.value)
        
        # Account expiry
        account_expiry_warning = ""
        if hasattr(self.entry, 'accountExpires') and self.entry.accountExpires.value:
            try:
                account_expires_filetime = int(self.entry.accountExpires.value)
                # 0 or 9223372036854775807 (0x7FFFFFFFFFFFFFFF) means never expires
                if account_expires_filetime not in [0, 9223372036854775807]:
                    account_expires_dt = datetime(1601, 1, 1) + timedelta(microseconds=account_expires_filetime / 10)
                    days_until_account_expiry = (account_expires_dt - datetime.now()).days
                    
                    if days_until_account_expiry < 0:
                        account_expiry_warning = f"[red bold]⚠ ACCOUNT EXPIRED {abs(days_until_account_expiry)} days ago![/red bold]"
                    elif days_until_account_expiry <= 7:
                        account_expiry_warning = f"[yellow bold]⚠ Account expires in {days_until_account_expiry} days![/yellow bold]"
                    elif days_until_account_expiry <= 30:
                        account_expiry_warning = f"[yellow]⚠ Account expires in {days_until_account_expiry} days[/yellow]"
            except:
                pass
        
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
Disabled: {'[red]Yes[/red]' if is_disabled else '[green]No[/green]'}
Locked: {'[red]Yes[/red]' if is_locked else '[green]No[/green]'}
Password Never Expires: {'Yes' if password_never_expires else 'No'}
Password Last Set: {pwd_last_set}

[bold]Member Of ({len(self.member_of)} groups):[/bold]
"""
        
        if self.member_of:
            for group in self.member_of:
                content += f"  • {group['name']}\n"
        else:
            content += "  No group memberships\n"
        
        content += "\n[dim]Press 'a' to edit attributes | 'g' to manage groups | 'p' to set password[/dim]"
        
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

    def modify_attribute(self, attribute, value):
        """Modify a user attribute."""
        try:
            self.conn.modify(self.user_dn, {attribute: [(MODIFY_REPLACE, [value])]})
            if self.conn.result['result'] == 0:
                print(f"Successfully updated {attribute}")
                self.load_user_details()
                return True
            else:
                print(f"Failed to update {attribute}: {self.conn.result['message']}")
                return False
        except Exception as e:
            print(f"Error updating {attribute}: {e}")
            return False

    def add_to_group(self, group_dn):
        """Add user to a group."""
        try:
            self.conn.modify(group_dn, {'member': [(MODIFY_ADD, [self.user_dn])]})
            if self.conn.result['result'] == 0:
                print("Successfully joined group")
                self.load_user_details()
                return True
            else:
                print(f"Failed to join group: {self.conn.result['message']}")
                return False
        except Exception as e:
            print(f"Error joining group: {e}")
            return False

    def remove_from_group(self, group_dn):
        """Remove user from a group."""
        try:
            self.conn.modify(group_dn, {'member': [(MODIFY_DELETE, [self.user_dn])]})
            if self.conn.result['result'] == 0:
                print("Successfully left group")
                self.load_user_details()
                return True
            else:
                print(f"Failed to leave group: {self.conn.result['message']}")
                return False
        except Exception as e:
            print(f"Error leaving group: {e}")
            return False

