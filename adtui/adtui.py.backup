import configparser
import os
from datetime import datetime, timedelta
from ldap3 import Server, Connection, ALL, MODIFY_DELETE, MODIFY_REPLACE
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Tree, Static, Input, Footer, ListView, ListItem, Label, Button, TextArea
from textual.binding import Binding
from textual.screen import ModalScreen
import getpass
from functools import lru_cache

from adtree import ADTree
from widgets.details_pane import DetailsPane

# Load configuration
config = configparser.ConfigParser()
config.read('config.ini')

# Configuration
LDAP_SERVER = config['ldap']['server']
DOMAIN = config['ldap']['domain']
BASE_DN = config['ldap']['base_dn']
USE_SSL = config.getboolean('ldap', 'use_ssl', fallback=False)
LAST_USER_FILE = 'last_user.txt'

last_user = ''
if os.path.exists(LAST_USER_FILE):
    with open(LAST_USER_FILE, 'r') as f:
        last_user = f.read().strip()

def get_ldap_connection(username, password):
    """Create and return an Active Directory connection using simple bind."""
    bind_dn = f"{username}@{DOMAIN}"
    port = 636 if USE_SSL else 389
    server = Server(LDAP_SERVER, port=port, use_ssl=USE_SSL, get_info=ALL)
    try:
        return Connection(server, user=bind_dn, password=password, auto_bind=True)
    except Exception as e:
        print(f"Failed to connect: {e}")
        raise

class SearchResultsPane(ListView):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.conn = None

    def populate(self, results, conn=None):
        self.clear()
        self.conn = conn
        for result in results:
            item = ListItem(Label(result["label"]))
            item.text = result["label"]
            item.data = result['dn']
            self.append(item)


class ADTUI(App):
    CSS_PATH = "styles.tcss"
    BINDINGS = [
        Binding("escape", "quit", "Quit", show=True),
        Binding(":", "command_mode", "Command", show=True),
        Binding("/", "search_mode", "Search", show=True),
        Binding("r", "refresh_ou", "Refresh OU", show=True),
        Binding("t", "test_search", "test", show=True),
    ]

    def action_test_search(self):
        """Populate test search results."""
        self.populate_test_search_results()

    def __init__(self, username, password):
        super().__init__()
        self.conn = get_ldap_connection(username, password)
        self.adtree = ADTree(self.conn, BASE_DN)
        self.details = DetailsPane(id="details-pane")
        self.search_results_pane = SearchResultsPane(id="search-results-pane")
        self.command_mode = False
        self.base_dn = BASE_DN
        self.current_selected_dn = None
        self.current_selected_label = None
        self.pending_delete_dn = None
        self.pending_move_dn = None
        self.pending_move_target = None
        self.autocomplete_mode = False
        self.ou_cache = {}  # Cache for OU paths
        self.operation_history = []  # Track operations for undo
        self.max_history = 50  # Maximum operations to track

    def compose(self) -> ComposeResult:
        with Horizontal():
            with Vertical():
                yield self.adtree
            with Vertical():
                yield self.details
                yield self.search_results_pane
        yield Input(placeholder=": command/search", id="command-input")
        yield Footer()

    def on_mount(self):
        cmd_input = self.query_one("#command-input", Input)
        cmd_input.visible = False

    def on_input_changed(self, event: Input.Changed):
        """Handle input changes and provide autocomplete for move commands."""
        if self.command_mode and event.input.id == "command-input":
            value = event.value
            
            # Check if this is a move command and provide autocomplete
            if value.startswith(":m ") or value.startswith(":move "):
                prefix_len = 3 if value.startswith(":m ") else 6
                path_input = value[prefix_len:]
                self.show_path_autocomplete(path_input)
            elif self.autocomplete_mode:
                # Exit autocomplete mode if command changes
                self.autocomplete_mode = False
                self.search_results_pane.clear()

    def action_command_mode(self):
        """Enter command mode with : prefix."""
        self.command_mode = True
        cmd_input = self.query_one("#command-input", Input)
        cmd_input.visible = True
        cmd_input.focus()
        # Set value after focus to avoid selection issue
        self.set_timer(0.01, lambda: self._set_command_prefix(":"))

    def action_search_mode(self):
        """Enter search mode with / prefix (vim-style)."""
        self.command_mode = True
        cmd_input = self.query_one("#command-input", Input)
        cmd_input.placeholder = "Search..."
        cmd_input.visible = True
        cmd_input.focus()
        # Set value after focus to avoid selection issue
        self.set_timer(0.01, lambda: self._set_search_prefix())

    def _set_command_prefix(self, prefix: str):
        """Set the command prefix and move cursor to end."""
        cmd_input = self.query_one("#command-input", Input)
        cmd_input.value = prefix
        cmd_input.cursor_position = len(prefix)

    def _set_search_prefix(self):
        """Set the search prefix and move cursor to end."""
        cmd_input = self.query_one("#command-input", Input)
        cmd_input.value = "/"
        cmd_input.cursor_position = 1

    def action_refresh_ou(self):
        """Refresh the currently selected OU."""
        self.adtree.refresh_current_ou()

    def on_tree_node_selected(self, event: Tree.NodeSelected):
        """Show details when an object is selected."""
        node = event.node
        self.current_selected_dn = node.data
        self.current_selected_label = node.label
        self.details.update_content(node.label, node.data, self.conn)

    def on_list_view_highlighted(self, event: ListView.Highlighted):
        """Show details when a search result is selected."""
        if event.list_view.id == "search-results-pane":
            item = event.item
            self.current_selected_dn = item.data
            self.current_selected_label = item.text
            self.details.update_content(item.text, item.data, self.conn)

    def on_input_submitted(self, event: Input.Submitted):
        """Handle command/search input."""
        if self.command_mode:
            cmd = event.value.strip()
            
            # Handle search with / (vim-style)
            if cmd.startswith("/"):
                query = cmd[1:].strip()
                if query:
                    self.search_ad(query)
                else:
                    self.notify("Search query is empty", severity="warning")
            # Handle search with :s command
            elif cmd.startswith(":s "):
                query = cmd[3:]
                self.search_ad(query)
            elif cmd.startswith("s "):
                query = cmd[2:]
                self.search_ad(query)
            # Handle delete command (many variations)
            elif cmd in [":delete", ":del", ":d", "delete", "del", "d"]:
                self.handle_delete_command()
            # Handle OU creation
            elif cmd.startswith(":mkou ") or cmd.startswith(":createou "):
                prefix_len = 6 if cmd.startswith(":mkou ") else 10
                ou_path = cmd[prefix_len:].strip()
                self.handle_create_ou_command(ou_path)
            # Handle recycle bin operations
            elif cmd == ":recycle" or cmd == ":rb":
                self.show_recycle_bin()
            elif cmd.startswith(":restore "):
                restore_cn = cmd[9:].strip()
                self.handle_restore_command(restore_cn)
            # Handle undo
            elif cmd == ":undo" or cmd == ":u":
                self.handle_undo_command()
            # Handle move command with various prefixes
            elif cmd.startswith(":move ") or cmd.startswith(":m "):
                prefix_len = 6 if cmd.startswith(":move ") else 3
                target_path = cmd[prefix_len:].strip()
                target_dn = self.convert_path_to_dn(target_path)
                self.handle_move_command(target_dn)
            elif cmd.startswith(":mv "):
                target_path = cmd[4:].strip()
                target_dn = self.convert_path_to_dn(target_path)
                self.handle_move_command(target_dn)
            elif cmd.startswith("move ") or cmd.startswith("m "):
                prefix_len = 5 if cmd.startswith("move ") else 2
                target_path = cmd[prefix_len:].strip()
                target_dn = self.convert_path_to_dn(target_path)
                self.handle_move_command(target_dn)
            elif cmd.startswith("mv "):
                target_path = cmd[3:].strip()
                target_dn = self.convert_path_to_dn(target_path)
                self.handle_move_command(target_dn)
            # Handle help command
            elif cmd == ":help" or cmd == "help":
                self.show_help()
            # Unknown command
            elif cmd.startswith(":") and len(cmd) > 1:
                self.notify(f"Unknown command: {cmd}", severity="warning")
            elif cmd == ":" or cmd == "/":
                pass  # Empty command, just close
            else:
                if cmd:
                    self.notify(f"Unknown command: {cmd}", severity="warning")
            
            # Clear and hide input
            cmd_input = self.query_one("#command-input", Input)
            cmd_input.value = ""
            cmd_input.visible = False
            self.command_mode = False
            self.autocomplete_mode = False

    def search_ad(self, query):
        """Search Active Directory by cn or sAMAccountName."""
        try:
            self.conn.search(
                self.base_dn,
                f'(&(|(cn=*{query}*)(sAMAccountName=*{query}*))(|(objectClass=user)(objectClass=computer)(objectClass=group)))',
                attributes=['cn', 'objectClass', 'sAMAccountName']
            )
            results = []
            for entry in self.conn.entries:
                cn = str(entry['cn']) if 'cn' in entry else "Unknown"
                obj_classes = [str(cls).lower() for cls in entry['objectClass']]
                if 'user' in obj_classes and 'computer' not in obj_classes:
                    label = f"👤 {cn}"
                elif 'computer' in obj_classes:
                    label = f"💻 {cn}"
                elif 'group' in obj_classes:
                    label = f"👥 {cn}"
                else:
                    label = f"📄 {cn}"
                results.append({'label': label, 'dn': entry.entry_dn})
            self.search_results_pane.populate(results)
            self.search_results_pane.styles.display = "block"
        except Exception as e:
            print(f"Error searching AD: {e}")

    def populate_test_search_results(self):
        """Populate the search results pane with test data."""
        test_results = [
            {"label": "👤 Test User 1", "dn": "cn=Test User 1,ou=Users,dc=example,dc=com"},
            {"label": "💻 Test Computer 1", "dn": "cn=Test Computer 1,ou=Computers,dc=example,dc=com"},
            {"label": "👥 Test Group 1", "dn": "cn=Test Group 1,ou=Groups,dc=example,dc=com"},
        ]
        self.search_results_pane.populate(test_results)

    def handle_delete_command(self):
        """Handle delete command with confirmation."""
        if not self.current_selected_dn:
            self.notify("No object selected. Select an object first.", severity="warning")
            return
        
        # Store the DN for deletion after confirmation
        self.pending_delete_dn = self.current_selected_dn
        
        # Show confirmation dialog
        self.push_screen(
            ConfirmDeleteScreen(self.current_selected_label, self.current_selected_dn),
            self.handle_delete_confirmation
        )

    def handle_delete_confirmation(self, confirmed: bool):
        """Handle the delete confirmation result."""
        if confirmed and self.pending_delete_dn:
            self.delete_object(self.pending_delete_dn)
        else:
            self.notify("Delete cancelled", severity="information")
        self.pending_delete_dn = None

    def delete_object(self, dn):
        """Delete an AD object."""
        try:
            # Store in history before deleting
            self.add_to_history('delete', {'dn': dn, 'label': self.current_selected_label})
            
            result = self.conn.delete(dn)
            if result:
                self.notify(f"Successfully deleted object. Use :recycle to restore if needed.", severity="information")
                self.current_selected_dn = None
                self.current_selected_label = None
                self.details.update_content(None)
                # Refresh the tree
                self.action_refresh_ou()
            else:
                error_msg = self.conn.result.get('message', 'Unknown error')
                self.notify(f"Failed to delete: {error_msg}", severity="error")
        except Exception as e:
            self.notify(f"Error deleting object: {e}", severity="error")

    def get_human_readable_path(self, dn: str) -> str:
        """Convert DN to human-readable path without DC components.
        
        Example: cn=User,ou=IT,ou=Departments,dc=example,dc=com -> Departments/IT
        """
        if not dn:
            return ""
        
        parts = dn.split(',')
        ou_parts = []
        
        for part in parts:
            part = part.strip()
            if part.lower().startswith('ou='):
                ou_parts.append(part[3:])
            elif part.lower().startswith('dc='):
                # Skip DC components
                continue
        
        # Reverse to get top-down path
        ou_parts.reverse()
        return '/'.join(ou_parts) if ou_parts else ""

    def show_path_autocomplete(self, partial_path: str):
        """Show autocomplete suggestions for OU paths."""
        self.autocomplete_mode = True
        
        # Get current partial path components
        path_parts = [p.strip() for p in partial_path.split('/') if p.strip()]
        
        # Build the search base (where to search for next level OUs)
        if path_parts:
            # Search within the current path
            current_parts = path_parts[:-1]  # All but the last (incomplete) part
            search_prefix = path_parts[-1].lower() if path_parts else ""  # What user is typing
            
            if current_parts:
                # Build DN from completed path parts
                reversed_parts = list(reversed(current_parts))
                search_base = ','.join([f"ou={part}" for part in reversed_parts]) + ',' + self.base_dn
            else:
                search_base = self.base_dn
        else:
            search_base = self.base_dn
            search_prefix = ""
        
        # Search for OUs at this level
        try:
            self.conn.search(
                search_base,
                '(objectClass=organizationalUnit)',
                search_scope='LEVEL',
                attributes=['ou'],
                size_limit=50
            )
            
            suggestions = []
            for entry in self.conn.entries:
                ou_name = str(entry.ou.value) if hasattr(entry, 'ou') else None
                if ou_name:
                    # Filter by prefix if user is typing
                    if not search_prefix or ou_name.lower().startswith(search_prefix):
                        # Build the full path for display
                        if path_parts and len(path_parts) > 1:
                            full_path = '/'.join(path_parts[:-1]) + '/' + ou_name
                        else:
                            full_path = ou_name
                        
                        suggestions.append({
                            'label': f"📁 {full_path}",
                            'dn': entry.entry_dn,
                            'path': full_path
                        })
            
            # Show suggestions in search results pane
            if suggestions:
                self.search_results_pane.populate(suggestions, self.conn)
                # Override the normal selection behavior for autocomplete
                self.search_results_pane.styles.display = "block"
            else:
                self.search_results_pane.clear()
        
        except Exception as e:
            # Silently fail autocomplete on errors
            pass

    def on_list_view_selected(self, event: ListView.Selected):
        """Handle selection from autocomplete suggestions."""
        if self.autocomplete_mode and event.list_view.id == "search-results-pane":
            # User selected an autocomplete suggestion
            item = event.item
            if hasattr(item, 'data'):
                # Get the path from the label
                label = item.text
                if '📁' in label:
                    path = label.replace('📁 ', '').strip()
                    
                    # Update the input with the selected path
                    cmd_input = self.query_one("#command-input", Input)
                    cmd_input.value = f":m {path}/"
                    cmd_input.cursor_position = len(cmd_input.value)
                    cmd_input.focus()
                    
                    # Continue showing autocomplete for next level
                    self.show_path_autocomplete(path + '/')

    def convert_path_to_dn(self, path: str) -> str:
        """Convert human-readable path to full DN.
        
        Example: Departments/IT -> ou=IT,ou=Departments,dc=example,dc=com
        Or if full DN is provided, return as-is
        """
        # If it looks like a full DN already, return it
        if '=' in path and ('ou=' in path.lower() or 'cn=' in path.lower()):
            return path
        
        # Clean up the path
        path = path.strip().strip('/')
        
        if not path:
            return self.base_dn
        
        # Split by / and reverse to get DN order
        parts = [p.strip() for p in path.split('/') if p.strip()]
        parts.reverse()
        
        # Build the DN
        ou_parts = [f"ou={part}" for part in parts]
        
        # Append base DN
        full_dn = ','.join(ou_parts) + ',' + self.base_dn
        
        return full_dn

    def handle_move_command(self, target_ou):
        """Handle move command."""
        if not self.current_selected_dn:
            self.notify("No object selected. Select an object first.", severity="warning")
            return
        
        if not target_ou:
            self.notify("Target OU not specified. Usage: :m <path>", severity="warning")
            return
        
        # Validate the target DN exists
        try:
            self.conn.search(target_ou, '(objectClass=organizationalUnit)', search_scope='BASE', attributes=['ou'])
            if not self.conn.entries:
                self.notify(f"Target OU not found: {target_ou}", severity="error")
                return
        except Exception as e:
            self.notify(f"Invalid target OU: {e}", severity="error")
            return
        
        # Store the move operation details
        self.pending_move_dn = self.current_selected_dn
        self.pending_move_target = target_ou
        
        # Show confirmation dialog
        self.push_screen(
            ConfirmMoveScreen(self.current_selected_label, self.current_selected_dn, target_ou),
            self.handle_move_confirmation
        )

    def handle_move_confirmation(self, confirmed: bool):
        """Handle the move confirmation result."""
        if confirmed and self.pending_move_dn and self.pending_move_target:
            self.move_object(self.pending_move_dn, self.pending_move_target)
        else:
            self.notify("Move cancelled", severity="information")
        self.pending_move_dn = None
        self.pending_move_target = None

    def move_object(self, dn, target_ou):
        """Move an AD object to a new OU."""
        try:
            # Extract the RDN (relative distinguished name) from the full DN
            rdn = dn.split(',')[0]
            
            # Get original parent for undo functionality
            original_parent = ','.join(dn.split(',')[1:])
            
            # Perform the move operation
            result = self.conn.modify_dn(dn, rdn, new_superior=target_ou)
            
            if result:
                new_dn = f"{rdn},{target_ou}"
                self.notify(f"Successfully moved object to {target_ou}", severity="information")
                
                # Add to history for undo
                self.add_to_history('move', {
                    'object': rdn,
                    'original_parent': original_parent,
                    'new_dn': new_dn
                })
                
                self.current_selected_dn = new_dn
                # Refresh the details pane with the new DN
                if self.current_selected_label:
                    self.details.update_content(self.current_selected_label, new_dn, self.conn)
                # Refresh the tree
                self.action_refresh_ou()
            else:
                error_msg = self.conn.result.get('message', 'Unknown error')
                self.notify(f"Failed to move: {error_msg}", severity="error")
        except Exception as e:
            self.notify(f"Error moving object: {e}", severity="error")

    def add_to_history(self, operation_type: str, details: dict):
        """Add operation to history for potential undo."""
        self.operation_history.append({
            'type': operation_type,
            'details': details,
            'timestamp': datetime.now()
        })
        # Keep only last max_history operations
        if len(self.operation_history) > self.max_history:
            self.operation_history.pop(0)

    def handle_create_ou_command(self, ou_path: str):
        """Handle OU creation command."""
        if not ou_path:
            self.notify("OU path not specified. Usage: :mkou <path>", severity="warning")
            return
        
        # Show creation dialog
        self.push_screen(
            CreateOUScreen(ou_path),
            self.handle_create_ou_confirmation
        )

    def handle_create_ou_confirmation(self, result):
        """Handle OU creation confirmation."""
        if result:
            ou_path, description = result
            self.create_ou(ou_path, description)

    def create_ou(self, path: str, description: str = ""):
        """Create a new OU."""
        try:
            # Convert path to DN
            full_dn = self.convert_path_to_dn(path)
            
            # Extract OU name from path
            ou_name = path.split('/')[-1].strip()
            
            # Get parent DN
            parts = full_dn.split(',', 1)
            parent_dn = parts[1] if len(parts) > 1 else self.base_dn
            
            # Create the OU
            ou_dn = f"ou={ou_name},{parent_dn}"
            
            attributes = {
                'objectClass': ['top', 'organizationalUnit'],
                'ou': ou_name
            }
            
            if description:
                attributes['description'] = description
            
            result = self.conn.add(ou_dn, attributes=attributes)
            
            if result:
                self.notify(f"Successfully created OU: {ou_name}", severity="information")
                self.add_to_history('create_ou', {'dn': ou_dn, 'name': ou_name})
                self.action_refresh_ou()
            else:
                error_msg = self.conn.result.get('message', 'Unknown error')
                self.notify(f"Failed to create OU: {error_msg}", severity="error")
        except Exception as e:
            self.notify(f"Error creating OU: {e}", severity="error")

    def show_recycle_bin(self):
        """Show deleted objects from AD Recycle Bin."""
        try:
            # Search for deleted objects
            deleted_objects_dn = f"CN=Deleted Objects,{self.base_dn}"
            
            self.conn.search(
                deleted_objects_dn,
                '(isDeleted=TRUE)',
                search_scope='SUBTREE',
                attributes=['cn', 'objectClass', 'whenChanged', 'isDeleted'],
                controls=[('1.2.840.113556.1.4.417', True, None)]  # Show deleted objects control
            )
            
            if self.conn.entries:
                results = []
                for entry in self.conn.entries:
                    cn = str(entry.cn.value) if hasattr(entry, 'cn') else "Unknown"
                    obj_classes = [str(cls).lower() for cls in entry.objectClass] if hasattr(entry, 'objectClass') else []
                    when_deleted = str(entry.whenChanged.value) if hasattr(entry, 'whenChanged') else "Unknown"
                    
                    if 'user' in obj_classes:
                        icon = "👤"
                    elif 'group' in obj_classes:
                        icon = "👥"
                    elif 'computer' in obj_classes:
                        icon = "💻"
                    elif 'organizationalunit' in obj_classes:
                        icon = "📁"
                    else:
                        icon = "📄"
                    
                    results.append({
                        'label': f"{icon} [Deleted] {cn} ({when_deleted})",
                        'dn': entry.entry_dn
                    })
                
                self.search_results_pane.populate(results)
                self.notify(f"Found {len(results)} deleted objects. Use :restore <name> to restore.", severity="information")
            else:
                self.notify("No deleted objects found in Recycle Bin", severity="information")
                
        except Exception as e:
            self.notify(f"Error accessing Recycle Bin: {e}. Ensure AD Recycle Bin is enabled.", severity="error")

    def handle_restore_command(self, cn: str):
        """Handle restore command for deleted objects."""
        if not cn:
            self.notify("Object name not specified. Usage: :restore <name>", severity="warning")
            return
        
        # Search for the deleted object
        try:
            deleted_objects_dn = f"CN=Deleted Objects,{self.base_dn}"
            
            self.conn.search(
                deleted_objects_dn,
                f'(&(isDeleted=TRUE)(cn={cn}*))',
                search_scope='SUBTREE',
                attributes=['*'],
                controls=[('1.2.840.113556.1.4.417', True, None)]
            )
            
            if self.conn.entries:
                if len(self.conn.entries) > 1:
                    self.notify(f"Multiple objects found matching '{cn}'. Be more specific.", severity="warning")
                    return
                
                deleted_entry = self.conn.entries[0]
                self.push_screen(
                    ConfirmRestoreScreen(cn, deleted_entry.entry_dn),
                    lambda confirmed: self.restore_object(deleted_entry.entry_dn) if confirmed else None
                )
            else:
                self.notify(f"No deleted object found matching '{cn}'", severity="warning")
        except Exception as e:
            self.notify(f"Error searching for deleted object: {e}", severity="error")

    def restore_object(self, deleted_dn: str):
        """Restore a deleted object from Recycle Bin."""
        try:
            # Remove isDeleted attribute and restore
            # This is complex and requires specific AD permissions
            # Simplified version:
            result = self.conn.modify(deleted_dn, {
                'isDeleted': [(MODIFY_DELETE, [])],
                'distinguishedName': [(MODIFY_REPLACE, [deleted_dn.replace('\\0ADEL:', '')])]
            })
            
            if result:
                self.notify("Successfully restored object", severity="information")
                self.action_refresh_ou()
            else:
                # AD Recycle Bin restore is complex - notify user
                self.notify("Restore failed. Use PowerShell: Restore-ADObject cmdlet for complex restores.", severity="error")
        except Exception as e:
            self.notify(f"Error restoring object: {e}. Use PowerShell Restore-ADObject cmdlet.", severity="error")

    def handle_undo_command(self):
        """Handle undo of last operation."""
        if not self.operation_history:
            self.notify("No operations to undo", severity="information")
            return
        
        last_op = self.operation_history[-1]
        
        if last_op['type'] == 'delete':
            # Can't truly undo delete without recycle bin
            self.notify("Cannot undo delete. Check :recycle for deleted objects.", severity="warning")
        elif last_op['type'] == 'create_ou':
            # Can undo OU creation by deleting it
            self.push_screen(
                ConfirmUndoScreen(f"Delete OU: {last_op['details']['name']}"),
                lambda confirmed: self.undo_create_ou(last_op) if confirmed else None
            )
        elif last_op['type'] == 'move':
            # Can undo move by moving back
            self.push_screen(
                ConfirmUndoScreen(f"Move back: {last_op['details']['object']}"),
                lambda confirmed: self.undo_move(last_op) if confirmed else None
            )
        else:
            self.notify(f"Cannot undo operation type: {last_op['type']}", severity="warning")

    def undo_create_ou(self, operation: dict):
        """Undo OU creation by deleting it."""
        try:
            ou_dn = operation['details']['dn']
            result = self.conn.delete(ou_dn)
            if result:
                self.notify("Successfully undid OU creation", severity="information")
                self.operation_history.pop()
                self.action_refresh_ou()
            else:
                self.notify(f"Failed to undo: {self.conn.result.get('message')}", severity="error")
        except Exception as e:
            self.notify(f"Error undoing operation: {e}", severity="error")

    def undo_move(self, operation: dict):
        """Undo move operation by moving back."""
        try:
            current_dn = operation['details']['new_dn']
            original_parent = operation['details']['original_parent']
            rdn = current_dn.split(',')[0]
            
            result = self.conn.modify_dn(current_dn, rdn, new_superior=original_parent)
            if result:
                self.notify("Successfully undid move operation", severity="information")
                self.operation_history.pop()
                self.action_refresh_ou()
            else:
                self.notify(f"Failed to undo: {self.conn.result.get('message')}", severity="error")
        except Exception as e:
            self.notify(f"Error undoing operation: {e}", severity="error")

    def show_help(self):
        """Show help information."""
        help_text = """[bold cyan]Available Commands:[/bold cyan]

[bold]Search & Navigation:[/bold]
/<query>         - Search (vim-style)
:s <query>       - Search for objects by cn or sAMAccountName

[bold]Object Management:[/bold]
:d, :del         - Delete the currently selected object
:m <path>        - Move to path with autocomplete
:move <path>     - Same as :m

[bold]OU Management:[/bold]
:mkou <path>     - Create new OU at path
:createou <path> - Same as :mkou

[bold]Recovery & History:[/bold]
:recycle, :rb    - Show AD Recycle Bin contents
:restore <name>  - Restore deleted object
:undo, :u        - Undo last operation

[bold]Other:[/bold]
:help            - Show this help message

[bold]Keyboard Shortcuts:[/bold]
/                - Open search (vim-style)
:                - Enter command mode
r                - Refresh current OU
Esc              - Quit application

[bold cyan]Move with Autocomplete:[/bold cyan]
Type :m and start typing a path:
  :m User[autocomplete shows suggestions]
  :m Users/[shows subdirectories]

Click suggestions or keep typing:
  :m Users/IT/Developers
  :m Ch Charleville/Pole 1/

Full LDAP DN also works:
  :m ou=IT,ou=Users,dc=example,dc=com
"""
        self.notify(help_text, timeout=15)

class ConfirmDeleteScreen(ModalScreen[bool]):
    """Screen with a dialog to confirm deletion."""

    def __init__(self, label: str, dn: str):
        super().__init__()
        self.label = label
        self.dn = dn

    def compose(self) -> ComposeResult:
        yield Vertical(
            Static(f"[bold red]Confirm Deletion[/bold red]\n\nAre you sure you want to delete:\n\n{self.label}\n\nDN: {self.dn}\n\nThis action cannot be undone!", id="question"),
            Horizontal(
                Button("Delete", variant="error", id="delete"),
                Button("Cancel", variant="primary", id="cancel"),
                id="dialog-buttons"
            ),
            id="dialog"
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "delete":
            self.dismiss(True)
        else:
            self.dismiss(False)


class CreateOUScreen(ModalScreen):
    """Screen to create a new OU."""

    def __init__(self, path: str):
        super().__init__()
        self.path = path

    def compose(self) -> ComposeResult:
        yield Vertical(
            Static(f"[bold green]Create New OU[/bold green]\n\nPath: {self.path}\n", id="question"),
            Input(placeholder="Description (optional)", id="ou-description"),
            Horizontal(
                Button("Create", variant="success", id="create"),
                Button("Cancel", variant="primary", id="cancel"),
                id="dialog-buttons"
            ),
            id="dialog"
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "create":
            description_input = self.query_one("#ou-description", Input)
            self.dismiss((self.path, description_input.value))
        else:
            self.dismiss(None)


class ConfirmRestoreScreen(ModalScreen[bool]):
    """Screen to confirm restore operation."""

    def __init__(self, name: str, dn: str):
        super().__init__()
        self.name = name
        self.dn = dn

    def compose(self) -> ComposeResult:
        yield Vertical(
            Static(f"[bold cyan]Restore Deleted Object[/bold cyan]\n\nRestore: {self.name}\n\nDN: {self.dn}\n\nConfirm?", id="question"),
            Horizontal(
                Button("Restore", variant="success", id="restore"),
                Button("Cancel", variant="primary", id="cancel"),
                id="dialog-buttons"
            ),
            id="dialog"
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "restore":
            self.dismiss(True)
        else:
            self.dismiss(False)


class ConfirmUndoScreen(ModalScreen[bool]):
    """Screen to confirm undo operation."""

    def __init__(self, message: str):
        super().__init__()
        self.message = message

    def compose(self) -> ComposeResult:
        yield Vertical(
            Static(f"[bold yellow]Undo Last Operation[/bold yellow]\n\n{self.message}\n\nConfirm?", id="question"),
            Horizontal(
                Button("Undo", variant="warning", id="undo"),
                Button("Cancel", variant="primary", id="cancel"),
                id="dialog-buttons"
            ),
            id="dialog"
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "undo":
            self.dismiss(True)
        else:
            self.dismiss(False)


class ConfirmMoveScreen(ModalScreen[bool]):
    """Screen with a dialog to confirm move operation."""

    def __init__(self, label: str, dn: str, target: str):
        super().__init__()
        self.label = label
        self.dn = dn
        self.target = target

    def compose(self) -> ComposeResult:
        yield Vertical(
            Static(f"[bold yellow]Confirm Move[/bold yellow]\n\nMove object:\n{self.label}\n\nFrom: {self.dn}\n\nTo: {self.target}\n\nConfirm?", id="question"),
            Horizontal(
                Button("Move", variant="success", id="move"),
                Button("Cancel", variant="primary", id="cancel"),
                id="dialog-buttons"
            ),
            id="dialog"
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "move":
            self.dismiss(True)
        else:
            self.dismiss(False)


if __name__ == "__main__":
    print(f"Active Directory TUI - Domain: {DOMAIN}")
    username = input(f"Username [{last_user}]: ") or last_user
    password = getpass.getpass("Password: ")
    with open(LAST_USER_FILE, 'w') as f:
        f.write(username)
    try:
        app = ADTUI(username, password)
        app.run()
    except Exception as e:
        print(f"Failed to connect: {e}")

