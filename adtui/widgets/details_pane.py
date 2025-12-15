from textual.widgets import Static, TabbedContent, TabPane
from textual.containers import ScrollableContainer
from textual.app import ComposeResult
from textual.binding import Binding
from .group_details import GroupDetailsPane
from .user_details import UserDetailsPane
import sys

class DetailsPane(Static):
    """Main details pane that switches between different object types."""
    
    DEFAULT_CSS = """
    DetailsPane {
        overflow-y: auto;
        overflow-x: hidden;
    }
    """
    
    BINDINGS = [
        Binding("a", "view_attributes", "Attributes", show=True),
        Binding("g", "manage_groups", "Groups", show=True),
        Binding("p", "set_password", "Password", show=True),
    ]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.can_focus = True
        self.current_dn = None
        self.current_connection_manager = None
        self.current_type = None
        self.current_label = None
        self.user_details = None
        self.group_details = None

    def update_content(self, item_label, dn=None, connection_manager=None):
        """Update the details pane based on the selected object type."""
        if not item_label:
            self.update("Select an item to view details.")
            return

        if not dn or not connection_manager:
            self.update(f"Details for: {item_label}\n\n[Select an object to view details]")
            return
        
        self.current_dn = dn
        self.current_connection_manager = connection_manager
        self.current_label = item_label
        
        # Determine object type and display appropriate details
        if "👥" in item_label:  # Group
            self.current_type = "group"
            self._show_group_details(dn, connection_manager)
        elif "👤" in item_label:  # User
            self.current_type = "user"
            self._show_user_details(dn, connection_manager)
        elif "💻" in item_label:  # Computer
            self.current_type = "computer"
            self._show_computer_details(item_label, dn, connection_manager)
        elif "📁" in item_label:  # OU (Organizational Unit)
            self.current_type = "ou"
            self._show_ou_details(item_label, dn, connection_manager)
        else:
            self.current_type = None
            self.update(f"Details for: {item_label}\n\n[Unsupported object type]")

    
    def action_set_password(self):
        """Handle set password action."""
        if not self.current_dn:
            self.app.notify("No object selected", severity="warning")
            return
        
        if self.current_type == "user":
            from ui.dialogs import SetPasswordDialog
            self.app.push_screen(SetPasswordDialog(self.current_dn, self.current_connection_manager))
        else:
            self.app.notify("Password setting only available for users", severity="warning")
    
    def action_manage_groups(self):
        """Handle group management action."""
        if not self.current_dn:
            self.app.notify("No object selected", severity="warning")
            return
        
        if self.current_type == "user":
            from ui.dialogs import ManageGroupsDialog
            self.app.push_screen(ManageGroupsDialog(self.current_dn, self.current_connection_manager, self.user_details, self.app.base_dn))
        elif self.current_type == "group":
            from ui.dialogs import ManageGroupMembersDialog
            self.app.push_screen(ManageGroupMembersDialog(self.current_dn, self.current_connection_manager, self.group_details))
        else:
            self.app.notify("Group management not supported for this object type", severity="warning")
    
    def action_view_attributes(self):
        """Handle view all attributes action - opens editable dialog."""
        if not self.current_dn:
            self.app.notify("No object selected", severity="warning")
            return
        
        from ui.dialogs import EditAttributesDialog
        self.app.push_screen(EditAttributesDialog(self.current_dn, self.current_connection_manager))

    def _show_user_details(self, dn, connection_manager):
        """Display user details with tabs."""
        try:
            
            
            
            if hasattr(connection_manager, 'get_state'):
                state = connection_manager.get_state()
                
            
            self.user_details = UserDetailsPane()
            self.user_details.update_user_details(dn, connection_manager)
            
            
            
            # Get the content
            content = self.user_details._build_content()
            
            self.update(content)
        except Exception as e:
            
            self.update(f"[bold cyan]USER DETAILS[/bold cyan]\n\n[red]Error loading user details: {e}[/red]")
            import traceback
            traceback.print_exc()

    def _show_group_details(self, dn, connection_manager):
        """Display group details."""
        try:
            self.group_details = GroupDetailsPane()
            self.group_details.update_group_details(dn, connection_manager)
            
            content = self.group_details._build_content()
            self.update(content)
        except Exception as e:
            self.update(f"[bold cyan]GROUP DETAILS[/bold cyan]\n\n[red]Error loading group details: {e}[/red]")
            import traceback
            traceback.print_exc()

    def _show_computer_details(self, label, dn, connection_manager):
        """Display basic computer details."""
        try:
            def search_computer_op(conn):
                conn.search(dn, '(objectClass=*)', attributes=['*'])
                return conn.entries
            
            entries = connection_manager.execute_with_retry(search_computer_op)
            if entries:
                entry = entries[0]
                
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

    def _show_ou_details(self, label, dn, connection_manager):
        """Display OU (Organizational Unit) details."""
        try:
            def search_ou_op(conn):
                conn.search(dn, '(objectClass=*)', search_scope='BASE', attributes=['*'])
                return conn.entries
            
            entries = connection_manager.execute_with_retry(search_ou_op)
            if entries:
                entry = entries[0]
                
                ou_name = str(entry.ou.value) if hasattr(entry, 'ou') else "N/A"
                description = str(entry.description.value) if hasattr(entry, 'description') else "N/A"
                when_created = str(entry.whenCreated.value) if hasattr(entry, 'whenCreated') else "N/A"
                when_changed = str(entry.whenChanged.value) if hasattr(entry, 'whenChanged') else "N/A"
                
                # Count child objects
                def count_children_op(conn):
                    conn.search(dn, '(objectClass=*)', search_scope='LEVEL', attributes=['objectClass'])
                    return len(conn.entries)
                
                child_count = connection_manager.execute_with_retry(count_children_op)
                
                content = f"""[bold cyan]Organizational Unit Details[/bold cyan]

[bold]General Information:[/bold]
OU Name: {ou_name}
Description: {description}
DN: {dn}

[bold]Statistics:[/bold]
Direct Children: {child_count}

[bold]Timestamps:[/bold]
Created: {when_created}
Last Modified: {when_changed}

[dim]Select users, groups, or computers within this OU to view their details[/dim]
"""
                self.update(content)
            else:
                self.update(f"Details for: {label}\n\n[Could not load OU details]")
        except Exception as e:
            self.update(f"Details for: {label}\n\n[red]Error: {e}[/red]")

    def refresh_details(self):
        """Refresh the current details view."""
        if self.current_type == "user" and self.user_details:
            self.user_details.load_user_details()
            self._show_user_details(self.current_dn, self.current_connection_manager)
        elif self.current_type == "group" and self.group_details:
            self.group_details.load_group_details()
            self._show_group_details(self.current_dn, self.current_connection_manager)
        elif self.current_type == "ou":
            self._show_ou_details(self.current_selected_label, self.current_dn, self.current_connection_manager)

