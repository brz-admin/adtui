"""ADTUI - Active Directory Terminal UI - Refactored Version."""

import configparser
import os
import getpass
from typing import Optional

from ldap3 import Server, Connection, ALL
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Tree, Static, Input, Footer, ListView, ListItem, Label
from textual.binding import Binding

from adtree import ADTree
from widgets.details_pane import DetailsPane
from services import LDAPService, HistoryService, PathService
from services.config_service import ConfigService, ADConfig
from commands import CommandHandler
from ui.dialogs import ConfirmDeleteDialog, ConfirmMoveDialog, ConfirmRestoreDialog, ConfirmUndoDialog, CreateOUDialog, ADSelectionDialog, LoginDialog
from constants import Severity, MESSAGES

# Configuration will be loaded after AD selection
LAST_USER_FILE = 'last_user.txt'

last_user = ''
if os.path.exists(LAST_USER_FILE):
    with open(LAST_USER_FILE, 'r') as f:
        last_user = f.read().strip()


def get_ldap_connection(username: str, password: str, ad_config: ADConfig) -> Connection:
    """Create and return an Active Directory connection.
    
    Args:
        username: AD username
        password: AD password
        ad_config: AD configuration object
        
    Returns:
        Active LDAP connection
        
    Raises:
        Exception: If connection fails
    """
    bind_dn = f"{username}@{ad_config.domain}"
    port = 636 if ad_config.use_ssl else 389
    server = Server(ad_config.server, port=port, use_ssl=ad_config.use_ssl, get_info=ALL)
    try:
        # For password operations, AD requires SSL/TLS
        if not ad_config.use_ssl:
            print("WARNING: Password operations require SSL/TLS. Enable use_ssl in config.ini")
        
        conn = Connection(server, user=bind_dn, password=password, auto_bind=True)
        
        # Test if we can perform password operations
        if ad_config.use_ssl:
            # Connection is ready for password operations
            pass
        else:
            print("INFO: Connected without SSL. Password operations will be disabled.")
        
        return conn
    except Exception as e:
        print(f"Failed to connect: {e}")
        raise


class SearchResultsPane(ListView):
    """ListView for displaying search results."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.conn = None

    def populate(self, results, conn=None):
        """Populate the search results pane.
        
        Args:
            results: List of result dictionaries with 'label' and 'dn'
            conn: Optional LDAP connection
        """
        self.clear()
        self.conn = conn
        for result in results:
            item = ListItem(Label(result["label"]))
            item.text = result["label"]
            item.data = result['dn']
            self.append(item)
        
        # Auto-highlight first item
        if len(results) > 0:
            self.index = 0


class ADTUI(App):
    """Main Active Directory TUI Application."""
    
    CSS_PATH = "styles.tcss"
    BINDINGS = [
        Binding(":", "command_mode", "Command", show=True),
        Binding("/", "search_mode", "Search", show=True),
        Binding("r", "refresh_ou", "Refresh OU", show=True),
        Binding("c", "create_user", "Create User", show=True),
        # User-specific commands - hidden from footer but still functional
        Binding("a", "edit_attributes", "Attributes", show=False),
        Binding("g", "manage_groups", "Groups", show=False),
        Binding("p", "set_password", "Password", show=False),
        Binding("C", "copy_user", "Copy User", show=False),
        Binding("d", "delete_object", "Delete", show=False),
        Binding("escape", "cancel_command", "Cancel", show=False),
        Binding("tab", "cycle_focus", "Cycle Focus", show=False),
    ]

    def __init__(self, username: Optional[str] = None, password: Optional[str] = None, ad_config: Optional[ADConfig] = None):
        """Initialize the application.
        
        Args:
            username: AD username (optional for deferred login)
            password: AD password (optional for deferred login)
            ad_config: AD configuration (optional for deferred login)
        """
        super().__init__()
        
        self.ad_config = ad_config
        
        # Only establish connection if credentials are provided
        if username is not None and password is not None and ad_config is not None:
            self.base_dn = ad_config.base_dn
            self.conn = get_ldap_connection(username, password, ad_config)
            self._initialize_services()
        else:
            self.conn = None
            self.ldap_service = None
            self.history_service = None
            self.path_service = None
            self.command_handler = None
            # Create placeholder widgets
            from adtree import ADTree
            self.base_dn = ad_config.base_dn if ad_config else ""
            self.adtree = ADTree(None, self.base_dn)
            self.details = DetailsPane(id="details-pane")
            self.search_results_pane = SearchResultsPane(id="search-results-pane")
        
        # State management
        self.command_mode = False
        self.autocomplete_mode = False
        
        # Current selection
        self.current_selected_dn: Optional[str] = None
        self.current_selected_label: Optional[str] = None
    
    def _initialize_services(self):
        """Initialize services after connection is established."""
        # Initialize services
        self.ldap_service = LDAPService(self.conn, self.base_dn)
        self.history_service = HistoryService(max_size=50)
        self.path_service = PathService(self.base_dn)
        
        # Initialize command handler
        self.command_handler = CommandHandler(self)
        
        # Initialize widgets
        self.adtree = ADTree(self.conn, self.base_dn)
        self.details = DetailsPane(id="details-pane")
        self.search_results_pane = SearchResultsPane(id="search-results-pane")
        
        # Pending operations
        self.pending_delete_dn: Optional[str] = None
        self.pending_move_dn: Optional[str] = None
        self.pending_move_target: Optional[str] = None

    def compose(self) -> ComposeResult:
        """Compose the UI layout."""
        with Horizontal():
            with Vertical():
                yield self.adtree
            with Vertical():
                yield self.details
                yield self.search_results_pane
        yield Footer()
        yield Input(placeholder=": command/search", id="command-input")

    def on_mount(self):
        """Handle mount event."""
        cmd_input = self.query_one("#command-input", Input)
        cmd_input.visible = False
        self._update_footer()
        
        # Expand tree to show root level on startup with delay to ensure initialization
        self.set_timer(0.5, self._expand_tree_on_startup)

    # ==================== Command Mode Actions ====================
    
    def action_command_mode(self):
        """Enter command mode with : prefix."""
        self.command_mode = True
        cmd_input = self.query_one("#command-input", Input)
        cmd_input.visible = True
        cmd_input.focus()
        self.set_timer(0.01, lambda: self._set_input_prefix(":"))

    def action_search_mode(self):
        """Enter search mode with / prefix (vim-style)."""
        self.command_mode = True
        cmd_input = self.query_one("#command-input", Input)
        cmd_input.placeholder = "Search..."
        cmd_input.visible = True
        cmd_input.focus()
        self.set_timer(0.01, lambda: self._set_input_prefix("/"))

    def action_refresh_ou(self):
        """Refresh the currently selected OU."""
        self.adtree.refresh_current_ou()
    
    def refresh_specific_ou(self, ou_dn: str):
        """Refresh a specific OU by DN."""
        # Find the tree node for this OU and refresh it
        self.adtree.refresh_ou_by_dn(ou_dn)
    
    def action_cancel_command(self):
        """Cancel command mode and hide input."""
        if self.command_mode:
            cmd_input = self.query_one("#command-input", Input)
            cmd_input.value = ""
            cmd_input.visible = False
            self.command_mode = False
            self.autocomplete_mode = False
            # Hide search results if visible
            self.search_results_pane.styles.display = "none"
            # Return focus to tree
            self.adtree.focus()
    
    def action_cycle_focus(self):
        """Cycle focus between widgets."""
        # In autocomplete mode, tab between input and results
        if self.autocomplete_mode:
            focused = self.focused
            cmd_input = self.query_one("#command-input", Input)
            
            # If currently on input or not on results, go to results
            if focused == cmd_input or focused != self.search_results_pane:
                if self.search_results_pane.styles.display == "block":
                    self.search_results_pane.focus()
            else:
                # Go back to input
                cmd_input.focus()
        else:
            # Normal tab behavior
            self.focus_next()
    
    def action_edit_attributes(self):
        """Edit attributes of selected object."""
        if not self.current_selected_dn:
            self.notify("No object selected", severity="warning")
            return
        from ui.dialogs import EditAttributesDialog
        self.push_screen(EditAttributesDialog(self.current_selected_dn, self.conn))
    
    def action_manage_groups(self):
        """Manage groups for selected object."""
        if not self.current_selected_dn:
            self.notify("No object selected", severity="warning")
            return
        
        # Determine object type
        if self.current_selected_label and "👤" in str(self.current_selected_label):
            from ui.dialogs import ManageGroupsDialog
            # Need to load user details first
            from widgets.user_details import UserDetailsPane
            user_details = UserDetailsPane()
            user_details.update_user_details(self.current_selected_dn, self.conn)
            self.push_screen(ManageGroupsDialog(self.current_selected_dn, self.conn, user_details, self.base_dn))
        elif self.current_selected_label and "👥" in str(self.current_selected_label):
            from ui.dialogs import ManageGroupMembersDialog
            from widgets.group_details import GroupDetailsPane
            group_details = GroupDetailsPane()
            group_details.update_group_details(self.current_selected_dn, self.conn)
            self.push_screen(ManageGroupMembersDialog(self.current_selected_dn, self.conn, group_details))
        else:
            self.notify("Group management only available for users and groups", severity="warning")
    
    def action_set_password(self):
        """Set password for selected user."""
        if not self.current_selected_dn:
            self.notify("No object selected", severity="warning")
            return
        
        if self.current_selected_label and "👤" in str(self.current_selected_label):
            from ui.dialogs import SetPasswordDialog
            self.push_screen(SetPasswordDialog(self.current_selected_dn, self.conn))
        else:
            self.notify("Password setting only available for users", severity="warning")

    def action_delete_object(self):
        """Delete selected object."""
        if not self.current_selected_dn:
            self.notify("No object selected", severity="warning")
            return
        
        # Show confirmation dialog
        self.push_screen(
            ConfirmDeleteDialog(str(self.current_selected_label) if self.current_selected_label else "", 
                              self.current_selected_dn),
            self.handle_delete_confirmation
        )

    def _set_input_prefix(self, prefix: str):
        """Set the input prefix and move cursor to end."""
        cmd_input = self.query_one("#command-input", Input)
        cmd_input.value = prefix
        cmd_input.cursor_position = len(prefix)

    def _update_footer(self):
        """Update footer display based on current selection."""
        # User-specific commands are now hidden from footer by default
        # They remain functional and visible in details pane when appropriate
        pass

    # ==================== Input Handling ====================

    def on_input_changed(self, event: Input.Changed):
        """Handle input changes for autocomplete."""
        if self.command_mode and event.input.id == "command-input":
            value = event.value
            
            if value.startswith(":m ") or value.startswith(":move "):
                prefix_len = 3 if value.startswith(":m ") else 6
                path_input = value[prefix_len:]
                # Trigger autocomplete if ends with / or has content
                if path_input.endswith('/') or len(path_input) >= 1:
                    self.show_path_autocomplete(path_input)
            elif self.autocomplete_mode:
                self.autocomplete_mode = False
                self.search_results_pane.styles.display = "none"

    def on_input_submitted(self, event: Input.Submitted):
        """Handle command submission."""
        if self.command_mode:
            cmd = event.value.strip()
            
            # Execute command via handler
            self.command_handler.execute(cmd)
            
            # Cleanup
            cmd_input = self.query_one("#command-input", Input)
            cmd_input.value = ""
            cmd_input.visible = False
            self.command_mode = False
            self.autocomplete_mode = False

    # ==================== Selection Handlers ====================

    def on_tree_node_selected(self, event: Tree.NodeSelected):
        """Handle tree node selection."""
        node = event.node
        print(f"\n*** TREE NODE SELECTED ***")
        print(f"Node label: {node.label}")
        print(f"Node data (DN): {node.data}")
        print(f"Label type: {type(node.label)}")
        self.current_selected_dn = node.data
        self.current_selected_label = node.label
        print(f"Calling details.update_content...")
        self.details.update_content(node.label, node.data, self.conn)
        self._update_footer()
        print(f"*** TREE NODE SELECTED END ***\n")

    def on_list_view_highlighted(self, event: ListView.Highlighted):
        """Handle list view highlighting."""
        if event.list_view.id == "search-results-pane" and not self.autocomplete_mode:
            item = event.item
            if hasattr(item, 'data') and item.data:
                self.current_selected_dn = item.data
                self.current_selected_label = item.text
                self.details.update_content(item.text, item.data, self.conn)
                self._update_footer()

    def on_list_view_selected(self, event: ListView.Selected):
        """Handle list view selection (Enter key)."""
        if event.list_view.id == "search-results-pane":
            item = event.item
            if hasattr(item, 'data'):
                if self.autocomplete_mode:
                    # Autocomplete: complete the path
                    label = item.text
                    if '📁' in label:
                        # Extract path, preserving spaces
                        path = label.replace('📁 ', '').strip()
                        cmd_input = self.query_one("#command-input", Input)
                        # Always end with / to show next level
                        if not path.endswith('/'):
                            path = path + '/'
                        cmd_input.value = f":m {path}"
                        cmd_input.cursor_position = len(cmd_input.value)
                        # Trigger next autocomplete
                        self.show_path_autocomplete(path)
                        # Keep focus on search results so user can continue navigating
                        self.set_timer(0.05, lambda: self.search_results_pane.focus())
                else:
                    # Search result: show details and expand tree
                    self.current_selected_dn = item.data
                    self.current_selected_label = item.text
                    self.details.update_content(item.text, item.data, self.conn)
                    # Hide search results first
                    self.search_results_pane.styles.display = "none"
                    # Expand tree with slightly longer delay to ensure UI is ready
                    self.set_timer(0.2, lambda: self.expand_tree_to_dn(item.data))
                    # Return focus to tree after expansion
                    self.set_timer(0.4, lambda: self.adtree.focus())

    # ==================== Tree Navigation ====================
    
    def expand_tree_to_dn(self, dn: str) -> None:
        """Expand the tree to show the given DN.
        
        Args:
            dn: The Distinguished Name to navigate to
        """
        if not dn:
            return
        
        try:
            # Parse DN into components (skip the object itself, get parent path)
            dn_parts = dn.split(',')
            
            # Find OUs in the path (skip first part which is the object)
            ou_path = []
            for part in dn_parts[1:]:
                if part.lower().startswith('ou='):
                    ou_name = part.split('=', 1)[1]
                    ou_path.append(ou_name)
            
            # Reverse to get from root to leaf
            ou_path.reverse()
            
            # Start from the base DN node (first child of root)
            if not self.adtree.root.children:
                self.notify("Tree not loaded yet", severity="warning")
                return
            
            current_node = self.adtree.root.children[0]  # Base DN node
            
            # If no OU path, object is directly under base DN
            if not ou_path:
                # Just expand the base DN and select the object
                if not current_node.is_expanded:
                    current_node.expand()
                self.adtree.ensure_node_loaded(current_node)
                self._select_object_in_tree(current_node, dn)
                return
            
            # Navigate through each OU in the path
            for ou_name in ou_path:
                # Expand current node if not expanded
                if not current_node.is_expanded:
                    current_node.expand()
                
                # Ensure node contents are loaded synchronously
                self.adtree.ensure_node_loaded(current_node)
                
                # Find the child with this OU name
                found = False
                for child in current_node.children:
                    child_label = str(child.label)
                    # Remove emoji and extra spaces
                    clean_label = child_label.replace('📁', '').strip()
                    # Case-insensitive comparison
                    if clean_label.lower() == ou_name.lower():
                        current_node = child
                        found = True
                        break
                
                if not found:
                    # Can't navigate further - OU not found in tree
                    self.notify(f"Could not find OU '{ou_name}' in tree", severity="warning")
                    return
            
            # Expand the final OU to show its contents
            if current_node and current_node != self.adtree.root:
                if not current_node.is_expanded:
                    current_node.expand()
                    # Ensure final node is loaded
                    self.adtree.ensure_node_loaded(current_node)
                    # Add delay for tree to render after expansion
                    self.set_timer(0.2, lambda: self._select_object_in_tree(current_node, dn))
                else:
                    # Select object in the final OU with small delay
                    self.set_timer(0.1, lambda: self._select_object_in_tree(current_node, dn))
        
        except Exception as e:
            self.notify(f"Could not expand tree to DN: {e}", severity="warning")
    
    def _select_object_in_tree(self, parent_node, target_dn: str) -> None:
        """Select the specific object in the tree.
        
        Args:
            parent_node: The parent OU node
            target_dn: The target object's DN
        """
        try:
            # Look for the object in the parent's children
            found = False
            for child in parent_node.children:
                if hasattr(child, 'data') and child.data == target_dn:
                    # Select node first
                    self.adtree.select_node(child)
                    # Focus tree to ensure cursor is on selected node
                    self.adtree.focus()
                    found = True
                    break
            
            # If object not found, it might be because the OU wasn't fully loaded
            if not found:
                # Try to reload the OU and search again
                if hasattr(parent_node, 'data') and parent_node.data:
                    # Clear the loaded flag to force reload
                    if parent_node.data in self.adtree.loaded_ous:
                        self.adtree.loaded_ous.remove(parent_node.data)
                    
                    # Reload the OU
                    self.adtree.ensure_node_loaded(parent_node)
                    
                    # Try finding the object again
                    for child in parent_node.children:
                        if hasattr(child, 'data') and child.data == target_dn:
                            # Select node first
                            self.adtree.select_node(child)
                            # Focus tree to ensure cursor is on selected node
                            self.adtree.focus()
                            found = True
                            break
                
                if not found:
                    # Object still not found - notify user
                    self.notify("Object found but not visible in tree", severity="information")
        
        except Exception as e:
            self.notify(f"Could not select object in tree: {e}", severity="warning")
    
    def _expand_tree_on_startup(self) -> None:
        """Expand tree to show root level on startup."""
        try:
            if self.adtree and self.adtree.conn and self.adtree.root and self.adtree.root.children:
                root_node = self.adtree.root.children[0]  # Base DN node
                # Ensure root node is expanded and loaded
                if not root_node.is_expanded:
                    root_node.expand()
                    self.adtree.ensure_node_loaded(root_node)
        except Exception as e:
            # Silently fail - tree expansion is a nice-to-have feature
            pass
    
    # ==================== Autocomplete ====================

    def show_path_autocomplete(self, partial_path: str):
        """Show autocomplete suggestions for paths."""
        self.autocomplete_mode = True
        
        # Handle case where path ends with / - show all children
        if partial_path.endswith('/'):
            path_parts = [p.strip() for p in partial_path.rstrip('/').split('/') if p.strip()]
            search_prefix = ""
        else:
            path_parts = [p.strip() for p in partial_path.split('/') if p.strip()]
            search_prefix = path_parts[-1].lower() if path_parts else ""
            path_parts = path_parts[:-1]  # Remove last part for search base
        
        # Determine search base
        if path_parts:
            search_base = self.path_service.path_to_dn('/'.join(path_parts)) if self.path_service else self.base_dn
        else:
            search_base = self.base_dn
        
        try:
            ous = self.ldap_service.search_ous(search_base, search_prefix, limit=50)
            
            suggestions = []
            for ou in ous:
                if path_parts:
                    full_path = '/'.join(path_parts) + '/' + ou['name']
                else:
                    full_path = ou['name']
                
                suggestions.append({
                    'label': f"📁 {full_path}",
                    'dn': ou['dn'],
                    'path': full_path
                })
            
            if suggestions:
                self.search_results_pane.populate(suggestions, self.conn)
                self.search_results_pane.styles.display = "block"
                # Auto focus if requested
                if len(suggestions) == 1 and not search_prefix:
                    # If only one result and we're at /, could auto-select
                    pass
            else:
                self.search_results_pane.clear()
                self.search_results_pane.styles.display = "none"
        except Exception as e:
            print(f"Autocomplete error: {e}")
            pass

    # ==================== Delete Operations ====================

    def handle_delete_confirmation(self, confirmed: bool):
        """Handle delete confirmation result."""
        if confirmed and self.pending_delete_dn:
            self.delete_object(self.pending_delete_dn)
        else:
            self.notify(MESSAGES['DELETE_CANCELLED'], severity=Severity.INFORMATION.value)
        self.pending_delete_dn = None

    def delete_object(self, dn: str):
        """Delete an AD object."""
        # Add to history
        self.history_service.add('delete', {'dn': dn, 'label': self.current_selected_label})
        
        # Get parent OU before deletion for refresh
        parent_ou = self.path_service.get_parent_dn(dn) if self.path_service else None
        
        # Perform delete
        success, message = self.ldap_service.delete_object(dn)
        
        if success:
            self.notify(message, severity=Severity.INFORMATION.value)
            self.current_selected_dn = None
            self.current_selected_label = None
            self.details.update_content(None)
            self._update_footer()
            
            # Refresh the parent OU to show the deletion
            if parent_ou:
                self.refresh_specific_ou(parent_ou)
            else:
                self.action_refresh_ou()  # Fallback to current selection
        else:
            self.notify(message, severity=Severity.ERROR.value)

    # ==================== Move Operations ====================

    def handle_move_confirmation(self, confirmed: bool):
        """Handle move confirmation result."""
        if confirmed and self.pending_move_dn and self.pending_move_target:
            self.move_object(self.pending_move_dn, self.pending_move_target)
        else:
            self.notify(MESSAGES['MOVE_CANCELLED'], severity=Severity.INFORMATION.value)
        self.pending_move_dn = None
        self.pending_move_target = None

    def move_object(self, dn: str, target_ou: str):
        """Move an AD object."""
        original_parent = self.path_service.get_parent_dn(dn)
        
        success, message, new_dn = self.ldap_service.move_object(dn, target_ou)
        
        if success:
            self.notify(message, severity=Severity.INFORMATION.value)
            
            # Add to history
            self.history_service.add('move', {
                'object': self.path_service.get_rdn(dn),
                'original_parent': original_parent,
                'new_dn': new_dn
            })
            
            self.current_selected_dn = new_dn
            if self.current_selected_label:
                self.details.update_content(self.current_selected_label, new_dn, self.conn)
            self.action_refresh_ou()
        else:
            self.notify(message, severity=Severity.ERROR.value)

    # ==================== OU Creation ====================

    def handle_create_ou_confirmation(self, result):
        """Handle OU creation confirmation."""
        if result:
            if len(result) == 3:
                # New mode: (ou_name, parent_dn, description)
                ou_name, parent_dn, description = result
                self.create_ou_in_parent(ou_name, parent_dn, description)
            else:
                # Legacy mode: (path, description)
                ou_path, description = result
                self.create_ou(ou_path, description)

    def create_ou_in_parent(self, ou_name: str, parent_dn: str, description: str = ""):
        """Create a new OU in specified parent."""
        success, message = self.ldap_service.create_ou(ou_name, parent_dn, description)
        
        if success:
            self.notify(message, severity=Severity.INFORMATION.value)
            self.history_service.add('create_ou', {'dn': f"ou={ou_name},{parent_dn}", 'name': ou_name})
            self.action_refresh_ou()
        else:
            self.notify(message, severity=Severity.ERROR.value)

    def create_ou(self, path: str, description: str = ""):
        """Create a new OU (legacy method)."""
        full_dn = self.path_service.path_to_dn(path)
        ou_name = self.path_service.extract_ou_name_from_path(path)
        parent_dn = self.path_service.get_parent_dn(full_dn)
        
        success, message = self.ldap_service.create_ou(ou_name, parent_dn, description)
        
        if success:
            self.notify(message, severity=Severity.INFORMATION.value)
            self.history_service.add('create_ou', {'dn': f"ou={ou_name},{parent_dn}", 'name': ou_name})
            self.action_refresh_ou()
        else:
            self.notify(message, severity=Severity.ERROR.value)

    # ==================== Restore Operations ====================

    def restore_object(self, deleted_dn: str):
        """Restore a deleted object."""
        success, message = self.ldap_service.restore_object(deleted_dn)
        
        if success:
            self.notify(message, severity=Severity.INFORMATION.value)
            self.action_refresh_ou()
        else:
            self.notify(message, severity=Severity.ERROR.value)

    # ==================== Undo Operations ====================

    def undo_create_ou(self, operation):
        """Undo OU creation."""
        ou_dn = operation.details['dn']
        success, message = self.ldap_service.delete_object(ou_dn)
        
        if success:
            self.notify(MESSAGES['UNDO_SUCCESS'], severity=Severity.INFORMATION.value)
            self.history_service.pop_last()
            self.action_refresh_ou()
        else:
            self.notify(f"Failed to undo: {message}", severity=Severity.ERROR.value)

    def undo_move(self, operation):
        """Undo move operation."""
        current_dn = operation.details['new_dn']
        original_parent = operation.details['original_parent']
        
        success, message, _ = self.ldap_service.move_object(current_dn, original_parent)
        
        if success:
            self.notify(MESSAGES['UNDO_SUCCESS'], severity=Severity.INFORMATION.value)
            self.history_service.pop_last()
            self.action_refresh_ou()
        else:
            self.notify(f"Failed to undo: {message}", severity=Severity.ERROR.value)



    def handle_unlock_confirmation(self, confirmed: bool):
        """Handle unlock confirmation result."""
        if confirmed and self.current_selected_dn:
            try:
                success, message = self.ldap_service.unlock_user_account(self.current_selected_dn)
                if success:
                    self.notify(message, severity=Severity.INFORMATION.value)
                    # Refresh the current view
                    self.refresh_current_view()
                else:
                    self.notify(message, severity=Severity.ERROR.value)
            except Exception as e:
                self.notify(f"Error unlocking account: {e}", severity=Severity.ERROR.value)

    def handle_create_user_confirmation(self, result):
        """Handle create user confirmation result."""
        if result and result.get('success'):
            # Add to history for undo
            self.history_service.add('create_user', {
                'user_dn': result['user_dn'],
                'full_name': result['full_name'],
                'samaccount': result['samaccount']
            })
            
            # Refresh tree to show new user
            self.action_refresh_ou()
            
            # Navigate to and select new user
            self.set_timer(0.5, lambda: self.expand_tree_to_dn(result['user_dn']))
        elif result:
            # User cancelled dialog
            pass

    def handle_copy_user_confirmation(self, result):
        """Handle copy user confirmation result."""
        if result and result.get('success'):
            # Add to history for undo
            self.history_service.add('copy_user', {
                'user_dn': result['user_dn'],
                'full_name': result['full_name'],
                'samaccount': result['samaccount']
            })
            
            # Refresh tree to show new user
            self.action_refresh_ou()
            
            # Navigate to and select new user
            self.set_timer(0.5, lambda: self.expand_tree_to_dn(result['user_dn']))
        elif result:
            # User cancelled dialog
            pass

    def undo_create_user(self, operation):
        """Undo create user operation."""
        try:
            user_dn = operation.details['user_dn']
            success, message = self.ldap_service.delete_object(user_dn)
            
            if success:
                self.notify(f"Undid: Created user {operation.details['full_name']}", 
                           severity=Severity.INFORMATION.value)
                self.action_refresh_ou()
            else:
                self.notify(f"Failed to undo create user: {message}", 
                           severity=Severity.ERROR.value)
        except Exception as e:
            self.notify(f"Error undoing create user: {e}", severity=Severity.ERROR.value)

    def undo_copy_user(self, operation):
        """Undo copy user operation."""
        try:
            user_dn = operation.details['user_dn']
            success, message = self.ldap_service.delete_object(user_dn)
            
            if success:
                self.notify(f"Undid: Copied user {operation.details['full_name']}", 
                           severity=Severity.INFORMATION.value)
                self.action_refresh_ou()
            else:
                self.notify(f"Failed to undo copy user: {message}", 
                           severity=Severity.ERROR.value)
        except Exception as e:
            self.notify(f"Error undoing copy user: {e}", severity=Severity.ERROR.value)

    def action_create_user(self):
        """Create new user account."""
        from ui.dialogs import CreateUserDialog
        
        # Use current selected OU or base DN
        target_ou = self._get_current_ou()
        if not target_ou:
            target_ou = self.ldap_service.base_dn if self.ldap_service else self.base_dn
        
        self.push_screen(CreateUserDialog(target_ou, self.ldap_service), 
                       self.handle_create_user_confirmation)

    def action_copy_user(self):
        """Copy existing user account."""
        from ui.dialogs import CopyUserDialog
        
        if not self.current_selected_dn:
            self.notify("No user selected to copy", severity=Severity.WARNING.value)
            return
        
        # Check if selected object is a user
        if not self._is_user_object(self.current_selected_dn):
            self.notify("Selected object is not a user", severity=Severity.WARNING.value)
            return
        
        # Use current selected OU as target
        target_ou = self._get_current_ou()
        if not target_ou:
            target_ou = self.ldap_service.base_dn if self.ldap_service else self.base_dn
        
        self.push_screen(CopyUserDialog(self.current_selected_dn, 
                                    str(self.current_selected_label) if self.current_selected_label else "", 
                                    target_ou, 
                                    self.ldap_service),
                       self.handle_copy_user_confirmation)

    def _get_current_ou(self) -> str:
        """Get currently selected OU DN."""
        if self.current_selected_dn:
            # Check if current selection is an OU
            if self.current_selected_label and "📁" in str(self.current_selected_label):
                return self.current_selected_dn
            else:
                # Get parent OU of selected object
                dn_parts = self.current_selected_dn.split(',')
                if len(dn_parts) > 1:
                    return ','.join(dn_parts[1:])
        
        # Fallback to base DN
        return self.ldap_service.base_dn if self.ldap_service else self.base_dn

    def _is_user_object(self, dn: str) -> bool:
        """Check if DN represents a user object."""
        try:
            self.ldap_service.conn.search(
                dn,
                '(objectClass=*)',
                search_scope='BASE',
                attributes=['objectClass']
            )
            if self.ldap_service.conn.entries:
                obj_classes = [str(cls).lower() for cls in self.ldap_service.conn.entries[0].objectClass]
                return 'user' in obj_classes and 'computer' not in obj_classes
            return False
        except:
            return False

    def refresh_current_view(self):
        """Refresh the currently displayed view."""
        if hasattr(self.details, "current_widget") and self.details.current_widget:
            # Refresh user details if showing
            if hasattr(self.details.current_widget, "load_user_details"):
                self.details.current_widget.load_user_details()
        else:
            # Otherwise refresh the tree
            self.action_refresh_ou()

def main():
    """Main entry point for application."""
    # Load configuration
    try:
        config_service = ConfigService()
    except Exception as e:
        print(f"Failed to load configuration: {e}")
        return
    
    # Validate configuration
    is_valid, issues = config_service.validate_config()
    if not is_valid:
        print("Configuration errors:")
        for issue in issues:
            print(f"  - {issue}")
        return
    
    # Global variables to store login results
    selected_domain = None
    login_credentials = None
    
    # Create a simple app for the login flow
    class LoginFlowApp(App):
        CSS = """
        Screen {
            layout: grid;
            grid-size: 1 1;
            background: $background;
        }
        
        Static {
            text-align: center;
            content-align: center middle;
        }
        """
        
        def compose(self) -> ComposeResult:
            ascii_art = """[bold cyan]┏━┃┏━   ━┏┛┃ ┃┛[/bold cyan]
[blue]  ┏━┃┃ ┃   ┃ ┃ ┃┃[/blue]  
[dark_blue]┛ ┛━━    ┛ ━━┛┛[/dark_blue]"""
            
            yield Static(f"{ascii_art}\n\n[bold cyan]Active Directory TUI[/bold cyan]\n")
        
        def on_mount(self) -> None:
            nonlocal selected_domain, login_credentials
            
            # Check if we need to show AD selection dialog
            if config_service.has_multiple_domains():
                # Show AD selection dialog first
                self.push_screen(ADSelectionDialog(config_service.ad_configs), self.handle_ad_selection)
            else:
                # Skip AD selection, use the default domain
                selected_domain = config_service.get_default_domain()
                self.show_login_dialog()
        
        def handle_ad_selection(self, domain):
            """Handle AD domain selection."""
            nonlocal selected_domain
            if domain:
                selected_domain = domain
                self.show_login_dialog()
            else:
                self.exit()
        
        def show_login_dialog(self):
            """Show the login dialog."""
            nonlocal login_credentials
            ad_config = config_service.get_config(selected_domain)
            self.push_screen(LoginDialog(last_user, ad_config.domain), self.handle_login_result)
        
        def handle_login_result(self, result):
            """Handle login result."""
            nonlocal login_credentials
            if result:
                username, password = result
                
                # Save username to file
                with open(LAST_USER_FILE, 'w') as f:
                    f.write(username)
                
                # Store credentials and exit login app
                login_credentials = (username, password)
                self.exit()
            else:
                self.exit()
        
        def on_key(self, event) -> None:
            if event.key == "escape":
                self.exit()
    
    # Run login flow app first
    login_app = LoginFlowApp()
    login_app.run()
    
    # After login app exits, check if we have credentials and start main app
    if login_credentials and selected_domain:
        # Clear the screen immediately to minimize CLI gap
        os.system('cls' if os.name == 'nt' else 'clear')
        
        username, password = login_credentials
        ad_config = config_service.get_config(selected_domain)
        
        try:
            # Create and run the main app with credentials and AD config
            app = ADTUI(username, password, ad_config)
            app.run()
        except Exception as e:
            print(f"Failed to start application: {e}")
    else:
        exit()


if __name__ == "__main__":
    main()
