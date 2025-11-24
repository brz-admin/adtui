from textual.widgets import Static, Button, Input, ListView, ListItem, Label
from textual.containers import ScrollableContainer, Vertical
from textual.app import ComposeResult
from ldap3 import MODIFY_ADD, MODIFY_DELETE

class GroupDetailsPane(Static):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.group_dn = None
        self.conn = None
        self.entry = None
        self.members = []
        self.member_of = []

    def update_group_details(self, group_dn, conn):
        """Load and display group details."""
        print(f"update_group_details called with DN: {group_dn}")
        self.group_dn = group_dn
        self.conn = conn
        self.load_group_details()
        print(f"load_group_details completed. Entry: {self.entry is not None}")

    def load_group_details(self):
        """Fetch group members and memberOf from LDAP."""
        print(f"load_group_details: Searching for {self.group_dn}")
        try:
            self.conn.search(
                self.group_dn,
                '(objectClass=*)',
                search_scope='BASE',
                attributes=['cn', 'member', 'memberOf', 'description', 'groupType']
            )
            print(f"Search completed. Entries found: {len(self.conn.entries)}")
            if self.conn.entries:
                self.entry = self.conn.entries[0]
                
                # Extract members (just the CN)
                if hasattr(self.entry, 'member') and self.entry.member:
                    self.members = [
                        {
                            'name': dn.split(',')[0].split('=')[1],
                            'dn': dn
                        }
                        for dn in self.entry.member.values
                    ]
                else:
                    self.members = []
                
                # Extract memberOf groups (just the CN)
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
        except Exception as e:
            print(f"Error loading group details: {e}")
            import traceback
            traceback.print_exc()

    def refresh_display(self):
        """Refresh the displayed content."""
        if not self.entry:
            return "[red]Error loading group details[/red]"
        
        return self._build_content()

    def _build_content(self):
        """Build the content string for display."""
        print(f"_build_content called. Entry exists: {self.entry is not None}")
        if not self.entry:
            print("No entry found, returning 'No group data'")
            return "No group data"
        
        # General Information
        cn = str(self.entry.cn.value) if hasattr(self.entry, 'cn') else "N/A"
        description = str(self.entry.description.value) if hasattr(self.entry, 'description') else "N/A"
        
        # Group type
        group_type = "N/A"
        if hasattr(self.entry, 'groupType'):
            gt = int(self.entry.groupType.value)
            if gt & 0x00000002:
                group_type = "Global"
            elif gt & 0x00000004:
                group_type = "Domain Local"
            elif gt & 0x00000008:
                group_type = "Universal"
            if gt & 0x80000000:
                group_type += " Security Group"
            else:
                group_type += " Distribution Group"
        
        # Build content
        content = f"""[bold cyan]Group Details[/bold cyan]

[bold]General Information:[/bold]
Group Name: {cn}
Description: {description}
Group Type: {group_type}
DN: {self.group_dn}

[bold]Members ({len(self.members)}):[/bold]
"""
        
        if self.members:
            for member in self.members:
                content += f"  • {member['name']}\n"
        else:
            content += "  No members\n"
        
        content += f"\n[bold]Member Of ({len(self.member_of)} groups):[/bold]\n"
        
        if self.member_of:
            for group in self.member_of:
                content += f"  • {group['name']}\n"
        else:
            content += "  Not a member of any group\n"
        
        content += "\n[dim]Press 'g' to manage members | 'a' to view all attributes[/dim]"
        
        return content

    def add_member(self, member_dn):
        """Add a member to the group."""
        try:
            self.conn.modify(self.group_dn, {'member': [(MODIFY_ADD, [member_dn])]})
            if self.conn.result['result'] == 0:
                print("Successfully added member")
                self.load_group_details()
                return True
            else:
                print(f"Failed to add member: {self.conn.result['message']}")
                return False
        except Exception as e:
            print(f"Error adding member: {e}")
            return False

    def remove_member(self, member_dn):
        """Remove a member from the group."""
        try:
            self.conn.modify(self.group_dn, {'member': [(MODIFY_DELETE, [member_dn])]})
            if self.conn.result['result'] == 0:
                print("Successfully removed member")
                self.load_group_details()
                return True
            else:
                print(f"Failed to remove member: {self.conn.result['message']}")
                return False
        except Exception as e:
            print(f"Error removing member: {e}")
            return False

    def join_group(self, parent_group_dn):
        """Add this group to another group."""
        try:
            self.conn.modify(parent_group_dn, {'member': [(MODIFY_ADD, [self.group_dn])]})
            if self.conn.result['result'] == 0:
                print("Successfully joined group")
                self.load_group_details()
                return True
            else:
                print(f"Failed to join group: {self.conn.result['message']}")
                return False
        except Exception as e:
            print(f"Error joining group: {e}")
            return False

    def leave_group(self, parent_group_dn):
        """Remove this group from another group."""
        try:
            self.conn.modify(parent_group_dn, {'member': [(MODIFY_DELETE, [self.group_dn])]})
            if self.conn.result['result'] == 0:
                print("Successfully left group")
                self.load_group_details()
                return True
            else:
                print(f"Failed to leave group: {self.conn.result['message']}")
                return False
        except Exception as e:
            print(f"Error leaving group: {e}")
            return False

