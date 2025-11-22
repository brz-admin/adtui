from textual.widgets import Static, TabbedContent, TabPane
from textual.containers import ScrollableContainer
from textual.app import ComposeResult
from .group_details import GroupDetailsPane
from .user_details import UserDetailsPane

class DetailsPane(Static):
    """Main details pane that switches between different object types."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_dn = None
        self.current_conn = None
        self.current_type = None
        self.user_details = None
        self.group_details = None

    def update_content(self, item_label, dn=None, conn=None):
        """Update the details pane based on the selected object type."""
        if not item_label:
            self.update("Select an item to view details.")
            return

        if not dn or not conn:
            self.update(f"Details for: {item_label}\n\n[Select an object to view details]")
            return
        
        self.current_dn = dn
        self.current_conn = conn
        
        # Determine object type and display appropriate details
        if "👥" in item_label:  # Group
            self.current_type = "group"
            self._show_group_details(dn, conn)
        elif "👤" in item_label:  # User
            self.current_type = "user"
            self._show_user_details(dn, conn)
        elif "💻" in item_label:  # Computer
            self.current_type = "computer"
            self._show_computer_details(item_label, dn, conn)
        else:
            self.current_type = None
            self.update(f"Details for: {item_label}\n\n[Unsupported object type]")

    def _show_user_details(self, dn, conn):
        """Display user details with tabs."""
        self.user_details = UserDetailsPane()
        self.user_details.update_user_details(dn, conn)
        
        # Create tabbed interface
        content = f"""[bold cyan]USER DETAILS[/bold cyan]

{self.user_details._build_content()}
"""
        self.update(content)

    def _show_group_details(self, dn, conn):
        """Display group details."""
        self.group_details = GroupDetailsPane()
        self.group_details.update_group_details(dn, conn)
        
        content = f"{self.group_details._build_content()}"
        self.update(content)

    def _show_computer_details(self, label, dn, conn):
        """Display basic computer details."""
        try:
            conn.search(dn, '(objectClass=*)', attributes=['*'])
            if conn.entries:
                entry = conn.entries[0]
                
                cn = str(entry.cn.value) if hasattr(entry, 'cn') else "N/A"
                os_name = str(entry.operatingSystem.value) if hasattr(entry, 'operatingSystem') else "N/A"
                os_version = str(entry.operatingSystemVersion.value) if hasattr(entry, 'operatingSystemVersion') else "N/A"
                dns_hostname = str(entry.dNSHostName.value) if hasattr(entry, 'dNSHostName') else "N/A"
                
                content = f"""[bold cyan]Computer Details[/bold cyan]

[bold]General Information:[/bold]
Computer Name: {cn}
DNS Hostname: {dns_hostname}
Operating System: {os_name}
OS Version: {os_version}
DN: {dn}

[dim]Computer object details[/dim]
"""
                self.update(content)
            else:
                self.update(f"Details for: {label}\n\n[Could not load details]")
        except Exception as e:
            self.update(f"Details for: {label}\n\n[red]Error: {e}[/red]")

    def refresh(self):
        """Refresh the current details view."""
        if self.current_type == "user" and self.user_details:
            self.user_details.load_user_details()
            self._show_user_details(self.current_dn, self.current_conn)
        elif self.current_type == "group" and self.group_details:
            self.group_details.load_group_details()
            self._show_group_details(self.current_dn, self.current_conn)

