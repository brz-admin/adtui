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
from commands import CommandHandler
from ui.dialogs import ConfirmDeleteDialog, ConfirmMoveDialog, ConfirmRestoreDialog, ConfirmUndoDialog, CreateOUDialog
from constants import Severity, MESSAGES

# Load configuration
config = configparser.ConfigParser()
config.read('config.ini')

LDAP_SERVER = config['ldap']['server']
DOMAIN = config['ldap']['domain']
BASE_DN = config['ldap']['base_dn']
USE_SSL = config.getboolean('ldap', 'use_ssl', fallback=False)
LAST_USER_FILE = 'last_user.txt'

last_user = ''
if os.path.exists(LAST_USER_FILE):
    with open(LAST_USER_FILE, 'r') as f:
        last_user = f.read().strip()


def get_ldap_connection(username: str, password: str) -> Connection:
    """Create and return an Active Directory connection.
    
    Args:
        username: AD username
        password: AD password
        
    Returns:
        Active LDAP connection
        
    Raises:
        Exception: If connection fails
    """
    bind_dn = f"{username}@{DOMAIN}"
    port = 636 if USE_SSL else 389
    server = Server(LDAP_SERVER, port=port, use_ssl=USE_SSL, get_info=ALL)
    try:
        return Connection(server, user=bind_dn, password=password, auto_bind=True)
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


class ADTUI(App):
    """Main Active Directory TUI Application."""
    
    CSS_PATH = "styles.tcss"
    BINDINGS = [
        Binding(":", "command_mode", "Command", show=True),
        Binding("/", "search_mode", "Search", show=True),
        Binding("r", "refresh_ou", "Refresh OU", show=True),
        Binding("escape", "cancel_command", "Cancel", show=False),
    ]

    def __init__(self, username: str, password: str):
        """Initialize the application.
        
        Args:
            username: AD username
            password: AD password
        """
        super().__init__()
        
        # Establish connection
        self.conn = get_ldap_connection(username, password)
        
        # Initialize services
        self.ldap_service = LDAPService(self.conn, BASE_DN)
        self.history_service = HistoryService(max_size=50)
        self.path_service = PathService(BASE_DN)
        
        # Initialize command handler
        self.command_handler = CommandHandler(self)
        
        # Initialize widgets
        self.adtree = ADTree(self.conn, BASE_DN)
        self.details = DetailsPane(id="details-pane")
        self.search_results_pane = SearchResultsPane(id="search-results-pane")
        
        # State management
        self.command_mode = False
        self.autocomplete_mode = False
        self.base_dn = BASE_DN
        
        # Current selection
        self.current_selected_dn: Optional[str] = None
        self.current_selected_label: Optional[str] = None
        
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

    def _set_input_prefix(self, prefix: str):
        """Set the input prefix and move cursor to end."""
        cmd_input = self.query_one("#command-input", Input)
        cmd_input.value = prefix
        cmd_input.cursor_position = len(prefix)

    # ==================== Input Handling ====================

    def on_input_changed(self, event: Input.Changed):
        """Handle input changes for autocomplete."""
        if self.command_mode and event.input.id == "command-input":
            value = event.value
            
            if value.startswith(":m ") or value.startswith(":move "):
                prefix_len = 3 if value.startswith(":m ") else 6
                path_input = value[prefix_len:]
                self.show_path_autocomplete(path_input)
            elif self.autocomplete_mode:
                self.autocomplete_mode = False
                self.search_results_pane.clear()

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
        print(f"*** TREE NODE SELECTED END ***\n")

    def on_list_view_highlighted(self, event: ListView.Highlighted):
        """Handle list view highlighting."""
        if event.list_view.id == "search-results-pane" and not self.autocomplete_mode:
            item = event.item
            if hasattr(item, 'data') and item.data:
                self.current_selected_dn = item.data
                self.current_selected_label = item.text
                self.details.update_content(item.text, item.data, self.conn)
                # Try to expand tree to this location
                self.expand_tree_to_dn(item.data)

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
                        # Check if path ends with / to continue or complete
                        if path.endswith('/'):
                            cmd_input.value = f":m {path}"
                        else:
                            cmd_input.value = f":m {path}/"
                        cmd_input.cursor_position = len(cmd_input.value)
                        cmd_input.focus()
                        self.show_path_autocomplete(path + '/' if not path.endswith('/') else path)
                else:
                    # Search result: show details and expand tree
                    self.current_selected_dn = item.data
                    self.current_selected_label = item.text
                    self.details.update_content(item.text, item.data, self.conn)
                    self.expand_tree_to_dn(item.data)
                    # Hide search results and return focus to tree
                    self.search_results_pane.styles.display = "none"
                    self.adtree.focus()

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
            
            # Navigate through the tree
            current_node = self.adtree.root
            
            for ou_name in ou_path:
                # Expand current node if not expanded
                if not current_node.is_expanded:
                    current_node.expand()
                
                # Find the child with this OU name
                found = False
                for child in current_node.children:
                    child_label = str(child.label)
                    # Remove emoji and extra spaces
                    clean_label = child_label.replace('📁', '').strip()
                    if clean_label == ou_name or clean_label == f"{ou_name}":
                        current_node = child
                        found = True
                        break
                
                if not found:
                    # Can't navigate further
                    break
            
            # Expand the final OU to show its contents
            if current_node and current_node != self.adtree.root:
                if not current_node.is_expanded:
                    current_node.expand()
                    # Give it a moment to load
                    self.set_timer(0.2, lambda: self._select_object_in_tree(current_node, dn))
                else:
                    self._select_object_in_tree(current_node, dn)
        
        except Exception as e:
            # Silently fail - tree expansion is a nice-to-have feature
            print(f"Could not expand tree to DN: {e}")
    
    def _select_object_in_tree(self, parent_node, target_dn: str) -> None:
        """Select the specific object in the tree.
        
        Args:
            parent_node: The parent OU node
            target_dn: The target object's DN
        """
        try:
            # Look for the object in the parent's children
            for child in parent_node.children:
                if hasattr(child, 'data') and child.data == target_dn:
                    # Select this node
                    self.adtree.select_node(child)
                    # Scroll to make it visible
                    child.scroll_visible()
                    break
        except Exception as e:
            print(f"Could not select object in tree: {e}")
    
    # ==================== Autocomplete ====================

    def show_path_autocomplete(self, partial_path: str):
        """Show autocomplete suggestions for paths."""
        self.autocomplete_mode = True
        
        path_parts = [p.strip() for p in partial_path.split('/') if p.strip()]
        
        if path_parts:
            current_parts = path_parts[:-1]
            search_prefix = path_parts[-1].lower() if path_parts else ""
            
            if current_parts:
                search_base = self.path_service.path_to_dn('/'.join(current_parts))
            else:
                search_base = self.base_dn
        else:
            search_base = self.base_dn
            search_prefix = ""
        
        try:
            ous = self.ldap_service.search_ous(search_base, search_prefix, limit=50)
            
            suggestions = []
            for ou in ous:
                if path_parts and len(path_parts) > 1:
                    full_path = '/'.join(path_parts[:-1]) + '/' + ou['name']
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
            else:
                self.search_results_pane.clear()
        except Exception:
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
        
        # Perform delete
        success, message = self.ldap_service.delete_object(dn)
        
        if success:
            self.notify(message, severity=Severity.INFORMATION.value)
            self.current_selected_dn = None
            self.current_selected_label = None
            self.details.update_content(None)
            self.action_refresh_ou()
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
            ou_path, description = result
            self.create_ou(ou_path, description)

    def create_ou(self, path: str, description: str = ""):
        """Create a new OU."""
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


def main():
    """Main entry point for the application."""
    print(f"Active Directory TUI - Domain: {DOMAIN}")
    username = input(f"Username [{last_user}]: ") or last_user
    password = "REDACTED_PASSWORD" #getpass.getpass("Password: ")
    
    with open(LAST_USER_FILE, 'w') as f:
        f.write(username)
    
    try:
        app = ADTUI(username, password)
        app.run()
    except Exception as e:
        print(f"Failed to connect: {e}")


if __name__ == "__main__":
    main()
