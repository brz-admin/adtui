"""ADTUI - Active Directory Terminal UI - Refactored Version."""

import logging
import os
import subprocess
import sys
from typing import Optional

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Static, Input, Footer, ListView, ListItem, Label, Tree
from textual.binding import Binding

# Configure logging
logger = logging.getLogger(__name__)

try:
    from .adtree import ADTree
    from .widgets.details_pane import DetailsPane
    from .services import LDAPService, HistoryService, PathService
    from .services.config_service import ConfigService, ADConfig
    from .services.connection_manager import ConnectionManager, ConnectionState
    from .commands import CommandHandler
    from .ui.dialogs import (
        ConfirmDeleteDialog,
        ConfirmMoveDialog,
        ConfirmRestoreDialog,
        ConfirmUndoDialog,
        CreateOUDialog,
        ADSelectionDialog,
        LoginDialog,
    )
except ImportError:
    # Fallback for direct execution
    from adtree import ADTree
    from widgets.details_pane import DetailsPane
    from services import LDAPService, HistoryService, PathService
    from services.config_service import ConfigService, ADConfig
    from services.connection_manager import ConnectionManager, ConnectionState
    from commands import CommandHandler
    from .ui.dialogs import (
        ConfirmDeleteDialog,
        ConfirmMoveDialog,
        ConfirmRestoreDialog,
        ConfirmUndoDialog,
        CreateOUDialog,
        ADSelectionDialog,
        LoginDialog,
    )
from .constants import Severity, MESSAGES

# Configuration will be loaded after AD selection
LAST_USER_FILE = "last_user.txt"

last_user = ""
if os.path.exists(LAST_USER_FILE):
    with open(LAST_USER_FILE, "r") as f:
        last_user = f.read().strip()


def create_connection_manager(
    username: str, password: str, ad_config: ADConfig
) -> ConnectionManager:
    """Create and return a connection manager for Active Directory.

    Args:
        username: AD username
        password: AD password
        ad_config: AD configuration object

    Returns:
        Connection manager instance

    Raises:
        Exception: If connection fails
    """
    # For password operations, AD requires SSL/TLS
    if not ad_config.use_ssl:
        logger.warning(
            "Password operations require SSL/TLS. Enable use_ssl in config.ini"
        )

    # Create connection manager with retry settings from config
    manager = ConnectionManager(
        ad_config=ad_config,
        username=username,
        password=password,
        max_retries=ad_config.max_retries,
        initial_retry_delay=ad_config.initial_retry_delay,
        max_retry_delay=ad_config.max_retry_delay,
        health_check_interval=ad_config.health_check_interval,
    )

    if not ad_config.use_ssl:
        logger.info("Connected without SSL. Password operations will be disabled.")

    return manager


class SearchResultsPane(ListView):
    """ListView for displaying search results."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connection_manager = None

    def populate(self, results, connection_manager=None):
        """Populate the search results pane.

        Args:
            results: List of result dictionaries with 'label' and 'dn'
            connection_manager: Optional ConnectionManager instance
        """
        self.clear()
        self.connection_manager = connection_manager
        for result in results:
            item = ListItem(Label(result["label"]))
            item.text = result["label"]
            item.data = result["dn"]
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
        Binding("y", "copy_to_clipboard", "Copy Text", show=True),
        Binding("ctrl+c", "copy_selection", "Copy Selection", show=True),
        Binding("d", "delete_object", "Delete", show=False),
        Binding("u", "undo", "Undo", show=False),
        Binding("U", "unlock_user", "Unlock", show=False),
        Binding("?", "show_help", "Help", show=False),
        Binding("escape", "cancel_command", "Cancel", show=False),
        Binding("tab", "cycle_focus", "Cycle Focus", show=False),
    ]

    def __init__(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None,
        ad_config: Optional[ADConfig] = None,
    ):
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
            self.connection_manager = create_connection_manager(
                username, password, ad_config
            )
            # Set auth failure callback immediately so it's available even if initial connection fails
            self.connection_manager.set_auth_failure_callback(
                self._on_authentication_failure
            )
            self._initialize_services()
        else:
            self.connection_manager = None
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

        # Auth failure flag - used to signal main() to restart login flow
        self.auth_failed = False

        # Update check result (populated asynchronously)
        self._update_result = None

    def _initialize_services(self):
        """Initialize services after connection is established."""
        # Initialize services
        self.ldap_service = LDAPService(self.connection_manager, self.base_dn)
        self.history_service = HistoryService(max_size=50)
        self.path_service = PathService(self.base_dn)

        # Initialize command handler
        self.command_handler = CommandHandler(self)

        # Initialize widgets
        self.adtree = ADTree(self.connection_manager, self.base_dn)
        self.details = DetailsPane(id="details-pane")
        self.search_results_pane = SearchResultsPane(id="search-results-pane")

        # Pending operations
        self.pending_delete_dn: Optional[str] = None
        self.pending_move_dn: Optional[str] = None
        self.pending_move_target: Optional[str] = None
        self.pending_restore_dn: Optional[str] = None
        self.pending_restore_label: Optional[str] = None

        # Set up connection state monitoring
        self.connection_manager.add_state_change_callback(
            self._on_connection_state_change
        )

        # Set up authentication failure callback
        self.connection_manager.set_auth_failure_callback(
            self._on_authentication_failure
        )

    def compose(self) -> ComposeResult:
        """Compose the UI layout."""
        # Ensure all required attributes exist
        if not hasattr(self, "adtree") or self.adtree is None:
            from adtree import ADTree

            self.base_dn = getattr(self, "base_dn", "")
            self.adtree = ADTree(None, self.base_dn)

        if not hasattr(self, "details") or self.details is None:
            self.details = DetailsPane(id="details-pane")

        if not hasattr(self, "search_results_pane") or self.search_results_pane is None:
            self.search_results_pane = SearchResultsPane(id="search-results-pane")

        with Horizontal():
            with Vertical():
                yield self.adtree
            with Vertical():
                yield self.details
                yield self.search_results_pane
        yield Input(placeholder=": command/search", id="command-input")
        yield Footer()

    def on_mount(self):
        """Handle mount event."""
        cmd_input = self.query_one("#command-input", Input)
        cmd_input.visible = False
        self._update_footer()

        # Expand tree to show root level on startup with delay to ensure initialization
        self.set_timer(0.5, self._expand_tree_on_startup)
        # Also try to rebuild tree after a longer delay to ensure connection is ready
        self.set_timer(2.0, self._delayed_tree_rebuild)

        # Check for updates in background
        self._start_update_check()

    def _start_update_check(self):
        """Start background update check."""
        try:
            from .services.update_service import UpdateService

            update_service = UpdateService()
            update_service.check_for_update_async(self._on_update_check_complete)
        except Exception as e:
            logger.debug(f"Failed to start update check: {e}")

    def _on_update_check_complete(self, result):
        """Handle update check completion."""
        self._update_result = result

        if result.update_available:
            def show_notification():
                self.notify(
                    f"Update available: {result.current_version} -> {result.latest_version}. "
                    f"Use :update to upgrade.",
                    severity="information",
                    timeout=10,
                )
            # Use call_from_thread since this is from background thread
            self.call_from_thread(show_notification)

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
        from .ui.dialogs import EditAttributesDialog

        self.push_screen(
            EditAttributesDialog(self.current_selected_dn, self.connection_manager)
        )

    def action_manage_groups(self):
        """Manage groups for selected object."""
        if not self.current_selected_dn:
            self.notify("No object selected", severity="warning")
            return

        # Determine object type
        if self.current_selected_label and "👤" in str(self.current_selected_label):
            from .ui.dialogs import ManageGroupsDialog

            # Need to load user details first
            from widgets.user_details import UserDetailsPane

            user_details = UserDetailsPane()
            user_details.update_user_details(
                self.current_selected_dn, self.connection_manager
            )
            self.push_screen(
                ManageGroupsDialog(
                    self.current_selected_dn,
                    self.connection_manager,
                    user_details,
                    self.base_dn,
                )
            )
        elif self.current_selected_label and "👥" in str(self.current_selected_label):
            from .ui.dialogs import ManageGroupMembersDialog
            from widgets.group_details import GroupDetailsPane

            group_details = GroupDetailsPane()
            group_details.update_group_details(
                self.current_selected_dn, self.connection_manager
            )
            self.push_screen(
                ManageGroupMembersDialog(
                    self.current_selected_dn, self.connection_manager, group_details
                )
            )
        else:
            self.notify(
                "Group management only available for users and groups",
                severity="warning",
            )

    def action_set_password(self):
        """Set password for selected user."""
        if not self.current_selected_dn:
            self.notify("No object selected", severity="warning")
            return

        if self.current_selected_label and "👤" in str(self.current_selected_label):
            from .ui.dialogs import SetPasswordDialog

            self.push_screen(
                SetPasswordDialog(self.current_selected_dn, self.connection_manager)
            )
        else:
            self.notify("Password setting only available for users", severity="warning")

    def action_delete_object(self):
        """Delete selected object."""
        if not self.current_selected_dn:
            self.notify("No object selected", severity="warning")
            return

        # Store the DN to delete for confirmation callback
        self.pending_delete_dn = self.current_selected_dn

        # Show confirmation dialog
        self.push_screen(
            ConfirmDeleteDialog(
                str(self.current_selected_label) if self.current_selected_label else "",
                self.current_selected_dn,
            ),
            self.handle_delete_confirmation,
        )

    def action_undo(self):
        """Undo last operation."""
        if self.command_handler:
            self.command_handler.execute(":undo")

    def action_unlock_user(self):
        """Unlock selected user account."""
        if self.command_handler:
            self.command_handler.execute(":unlock")

    def action_show_help(self):
        """Show help."""
        if self.command_handler:
            self.command_handler.execute(":help")

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

    def _on_connection_state_change(
        self, state: ConnectionState, error: Optional[str] = None
    ):
        """Handle connection state changes.

        Args:
            state: New connection state
            error: Optional error message
        """

        # Use call_from_thread since this callback may be invoked from background threads
        def update_ui():
            if state == ConnectionState.CONNECTED:
                self.notify("Connected to Active Directory", severity="information")
                # Rebuild tree when connection is established
                if hasattr(self, "adtree") and self.adtree:
                    self.adtree.build_tree()
            elif state == ConnectionState.RECONNECTING:
                self.notify(f"Reconnecting to AD... {error or ''}", severity="warning")
            elif state == ConnectionState.FAILED:
                self.notify(
                    f"Connection failed: {error or 'Unknown error'}", severity="error"
                )

        self.call_from_thread(update_ui)

    def _on_authentication_failure(self):
        """Handle authentication failure - exit to restart login flow."""

        # Use call_from_thread since this may be called from connection manager's background thread
        def handle_auth_failure():
            try:
                # Set auth failure flag so main() knows to restart login
                self.auth_failed = True

                # Clear current connection and services
                self.connection_manager = None
                self.ldap_service = None
                self.history_service = None
                self.path_service = None
                self.command_handler = None

                # Reset tree to empty state
                if hasattr(self, "adtree") and self.adtree:
                    self.adtree = ADTree(None, self.base_dn)

                # Clear details pane
                if hasattr(self, "details") and self.details:
                    self.details.update_content("No connection", None, None)

                # Exit main app to trigger login restart in main script
                self.exit()

            except Exception as e:
                import traceback

                traceback.print_exc()

        self.call_from_thread(handle_auth_failure)

    # ==================== Input Handling ====================

    def on_input_changed(self, event: Input.Changed):
        """Handle input changes for autocomplete."""
        if self.command_mode and event.input.id == "command-input":
            value = event.value

            # Check for move commands: :m, :mv, :move
            if (
                value.startswith(":m ")
                or value.startswith(":mv ")
                or value.startswith(":move ")
            ):
                if value.startswith(":move "):
                    prefix_len = 6
                elif value.startswith(":mv "):
                    prefix_len = 4
                else:
                    prefix_len = 3
                path_input = value[prefix_len:]
                # Trigger autocomplete if ends with / or has content
                if path_input.endswith("/") or len(path_input) >= 1:
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
        self.current_selected_dn = node.data
        self.current_selected_label = node.label
        self.details.update_content(node.label, node.data, self.connection_manager)
        self._update_footer()

    def on_list_view_highlighted(self, event: ListView.Highlighted):
        """Handle list view highlighting."""
        if event.list_view.id == "search-results-pane" and not self.autocomplete_mode:
            item = event.item
            if hasattr(item, "data") and item.data:
                self.current_selected_dn = item.data
                self.current_selected_label = item.text
                self.details.update_content(
                    item.text, item.data, self.connection_manager
                )
                self._update_footer()

    def on_list_view_selected(self, event: ListView.Selected):
        """Handle list view selection (Enter key)."""
        if event.list_view.id == "search-results-pane":
            item = event.item
            if hasattr(item, "data"):
                if self.autocomplete_mode:
                    # Autocomplete: complete the path
                    label = item.text
                    if "📁" in label:
                        # Extract path, preserving spaces
                        path = label.replace("📁 ", "").strip()
                        cmd_input = self.query_one("#command-input", Input)
                        # Always end with / to show next level
                        if not path.endswith("/"):
                            path = path + "/"
                        cmd_input.value = f":m {path}"
                        cmd_input.cursor_position = len(cmd_input.value)
                        # Trigger next autocomplete
                        self.show_path_autocomplete(path)
                        # Keep focus on search results so user can continue navigating
                        self.set_timer(0.05, lambda: self.search_results_pane.focus())
                elif "[Deleted]" in str(item.text):
                    # Deleted object from recycle bin: offer to restore
                    self.pending_restore_dn = item.data
                    self.pending_restore_label = item.text
                    from .ui.dialogs import ConfirmRestoreDialog

                    self.push_screen(
                        ConfirmRestoreDialog(item.text, item.data),
                        self.handle_restore_confirmation,
                    )
                else:
                    # Search result: show details and expand tree
                    self.current_selected_dn = item.data
                    self.current_selected_label = item.text
                    self.details.update_content(
                        item.text, item.data, self.connection_manager
                    )
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
            dn_parts = dn.split(",")

            # Find OUs in the path (skip first part which is the object)
            ou_path = []
            for part in dn_parts[1:]:
                if part.lower().startswith("ou="):
                    ou_name = part.split("=", 1)[1]
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
                    clean_label = child_label.replace("📁", "").strip()
                    # Case-insensitive comparison
                    if clean_label.lower() == ou_name.lower():
                        current_node = child
                        found = True
                        break

                if not found:
                    # Can't navigate further - OU not found in tree
                    self.notify(
                        f"Could not find OU '{ou_name}' in tree", severity="warning"
                    )
                    return

            # Expand the final OU to show its contents
            if current_node and current_node != self.adtree.root:
                if not current_node.is_expanded:
                    current_node.expand()
                    # Ensure final node is loaded
                    self.adtree.ensure_node_loaded(current_node)
                    # Add delay for tree to render after expansion
                    self.set_timer(
                        0.2, lambda: self._select_object_in_tree(current_node, dn)
                    )
                else:
                    # Select object in the final OU with small delay
                    self.set_timer(
                        0.1, lambda: self._select_object_in_tree(current_node, dn)
                    )

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
                if hasattr(child, "data") and child.data == target_dn:
                    # Select node first
                    self.adtree.select_node(child)
                    # Focus tree to ensure cursor is on selected node
                    self.adtree.focus()
                    found = True
                    break

            # If object not found, it might be because the OU wasn't fully loaded
            if not found:
                # Try to reload the OU and search again
                if hasattr(parent_node, "data") and parent_node.data:
                    # Clear the loaded flag to force reload
                    if parent_node.data in self.adtree.loaded_ous:
                        self.adtree.loaded_ous.remove(parent_node.data)

                    # Reload the OU
                    self.adtree.ensure_node_loaded(parent_node)

                    # Try finding the object again
                    for child in parent_node.children:
                        if hasattr(child, "data") and child.data == target_dn:
                            # Select node first
                            self.adtree.select_node(child)
                            # Focus tree to ensure cursor is on selected node
                            self.adtree.focus()
                            found = True
                            break

                if not found:
                    # Object still not found - notify user
                    self.notify(
                        "Object found but not visible in tree", severity="information"
                    )

        except Exception as e:
            self.notify(f"Could not select object in tree: {e}", severity="warning")

    def _expand_tree_on_startup(self) -> None:
        """Expand tree to show root level on startup."""
        try:
            if (
                hasattr(self, "adtree")
                and self.adtree
                and hasattr(self.adtree, "connection_manager")
                and self.adtree.connection_manager
                and hasattr(self.adtree, "root")
                and self.adtree.root
                and hasattr(self.adtree.root, "children")
                and self.adtree.root.children
            ):
                root_node = self.adtree.root.children[0]  # Base DN node
                # Ensure root node is expanded and loaded
                if not root_node.is_expanded:
                    root_node.expand()
                    self.adtree.ensure_node_loaded(root_node)
        except Exception as e:
            # Silently fail - tree expansion is a nice-to-have feature
            pass

    def _delayed_tree_rebuild(self) -> None:
        """Rebuild tree after delay to ensure connection is ready."""
        try:
            if (
                hasattr(self, "adtree")
                and self.adtree
                and self.adtree.connection_manager
            ):
                self.adtree.build_tree()
        except Exception as e:
            import traceback

            traceback.print_exc()

    # ==================== Autocomplete ====================

    def show_path_autocomplete(self, partial_path: str):
        """Show autocomplete suggestions for paths."""
        self.autocomplete_mode = True

        # Handle case where path ends with / - show all children
        if partial_path.endswith("/"):
            path_parts = [
                p.strip() for p in partial_path.rstrip("/").split("/") if p.strip()
            ]
            search_prefix = ""
        else:
            path_parts = [p.strip() for p in partial_path.split("/") if p.strip()]
            search_prefix = path_parts[-1].lower() if path_parts else ""
            path_parts = path_parts[:-1]  # Remove last part for search base

        # Determine search base
        if path_parts:
            search_base = (
                self.path_service.path_to_dn("/".join(path_parts))
                if self.path_service
                else self.base_dn
            )
        else:
            search_base = self.base_dn

        try:
            ous = self.ldap_service.search_ous(search_base, search_prefix, limit=50)

            suggestions = []
            for ou in ous:
                if path_parts:
                    full_path = "/".join(path_parts) + "/" + ou["name"]
                else:
                    full_path = ou["name"]

                suggestions.append(
                    {"label": f"📁 {full_path}", "dn": ou["dn"], "path": full_path}
                )

            if suggestions:
                self.search_results_pane.populate(suggestions, self.connection_manager)
                self.search_results_pane.styles.display = "block"
                # Auto focus if requested
                if len(suggestions) == 1 and not search_prefix:
                    # If only one result and we're at /, could auto-select
                    pass
            else:
                self.search_results_pane.clear()
                self.search_results_pane.styles.display = "none"
        except Exception as e:
            pass

    # ==================== Delete Operations ====================

    def handle_delete_confirmation(self, confirmed: bool):
        """Handle delete confirmation result."""
        if confirmed and self.pending_delete_dn:
            self.delete_object(self.pending_delete_dn)
        else:
            self.notify(
                MESSAGES["DELETE_CANCELLED"], severity=Severity.INFORMATION.value
            )
        self.pending_delete_dn = None

    def delete_object(self, dn: str):
        """Delete an AD object."""
        # Add to history
        self.history_service.add(
            "delete", {"dn": dn, "label": self.current_selected_label}
        )

        # Perform delete
        success, message = self.ldap_service.delete_object(dn)

        if success:
            self.notify(message, severity=Severity.INFORMATION.value)
            # Clear current selection since the object was deleted
            self.current_selected_dn = None
            self.current_selected_label = None
            # Clear the details pane
            if hasattr(self, "details") and self.details:
                self.details.update_content("No selection", None, None)
            # Remove the deleted node from tree and select next appropriate node
            self.adtree.remove_node_by_dn(dn)
        else:
            self.notify(message, severity=Severity.ERROR.value)

    # ==================== Move Operations ====================

    def handle_move_confirmation(self, confirmed: bool):
        """Handle move confirmation result."""
        if confirmed and self.pending_move_dn and self.pending_move_target:
            self.move_object(self.pending_move_dn, self.pending_move_target)
        else:
            self.notify(MESSAGES["MOVE_CANCELLED"], severity=Severity.INFORMATION.value)
        self.pending_move_dn = None
        self.pending_move_target = None

    def move_object(self, dn: str, target_ou: str):
        """Move an AD object."""
        original_parent = self.path_service.get_parent_dn(dn)

        success, message, new_dn = self.ldap_service.move_object(dn, target_ou)

        if success:
            self.notify(message, severity=Severity.INFORMATION.value)

            # Add to history
            self.history_service.add(
                "move",
                {
                    "object": self.path_service.get_rdn(dn),
                    "original_parent": original_parent,
                    "new_dn": new_dn,
                },
            )

            self.current_selected_dn = new_dn
            if self.current_selected_label:
                self.details.update_content(
                    self.current_selected_label, new_dn, self.connection_manager
                )
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
            self.history_service.add(
                "create_ou", {"dn": f"ou={ou_name},{parent_dn}", "name": ou_name}
            )
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
            self.history_service.add(
                "create_ou", {"dn": f"ou={ou_name},{parent_dn}", "name": ou_name}
            )
            self.action_refresh_ou()
        else:
            self.notify(message, severity=Severity.ERROR.value)

    # ==================== Restore Operations ====================

    def handle_restore_confirmation(self, confirmed: bool):
        """Handle restore confirmation result."""
        if confirmed and self.pending_restore_dn:
            self.restore_object(self.pending_restore_dn)
            # Hide search results after restore
            self.search_results_pane.styles.display = "none"
        self.pending_restore_dn = None
        self.pending_restore_label = None

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
        ou_dn = operation.details["dn"]
        success, message = self.ldap_service.delete_object(ou_dn)

        if success:
            self.notify(MESSAGES["UNDO_SUCCESS"], severity=Severity.INFORMATION.value)
            self.history_service.pop_last()
            self.action_refresh_ou()
        else:
            self.notify(f"Failed to undo: {message}", severity=Severity.ERROR.value)

    def undo_move(self, operation):
        """Undo move operation."""
        current_dn = operation.details["new_dn"]
        original_parent = operation.details["original_parent"]

        success, message, _ = self.ldap_service.move_object(current_dn, original_parent)

        if success:
            self.notify(MESSAGES["UNDO_SUCCESS"], severity=Severity.INFORMATION.value)
            self.history_service.pop_last()
            self.action_refresh_ou()
        else:
            self.notify(f"Failed to undo: {message}", severity=Severity.ERROR.value)

    def handle_unlock_confirmation(self, confirmed: bool):
        """Handle unlock confirmation result."""
        if confirmed and self.current_selected_dn:
            try:
                success, message = self.ldap_service.unlock_user_account(
                    self.current_selected_dn
                )
                if success:
                    self.notify(message, severity=Severity.INFORMATION.value)
                    # Refresh the current view
                    self.refresh_current_view()
                else:
                    self.notify(message, severity=Severity.ERROR.value)
            except Exception as e:
                self.notify(
                    f"Error unlocking account: {e}", severity=Severity.ERROR.value
                )

    def handle_enable_confirmation(self, confirmed: bool):
        """Handle enable confirmation result."""
        if confirmed and self.current_selected_dn:
            try:
                success, message = self.ldap_service.enable_user_account(
                    self.current_selected_dn
                )
                if success:
                    self.notify(message, severity=Severity.INFORMATION.value)
                    # Refresh the current view
                    self.refresh_current_view()
                else:
                    self.notify(message, severity=Severity.ERROR.value)
            except Exception as e:
                self.notify(
                    f"Error enabling account: {e}", severity=Severity.ERROR.value
                )

    def handle_disable_confirmation(self, confirmed: bool):
        """Handle disable confirmation result."""
        if confirmed and self.current_selected_dn:
            try:
                success, message = self.ldap_service.disable_user_account(
                    self.current_selected_dn
                )
                if success:
                    self.notify(message, severity=Severity.INFORMATION.value)
                    # Refresh the current view
                    self.refresh_current_view()
                else:
                    self.notify(message, severity=Severity.ERROR.value)
            except Exception as e:
                self.notify(
                    f"Error disabling account: {e}", severity=Severity.ERROR.value
                )

    def handle_create_user_confirmation(self, result):
        """Handle create user confirmation result."""
        if result and result.get("success"):
            # Add to history for undo
            self.history_service.add(
                "create_user",
                {
                    "user_dn": result["user_dn"],
                    "full_name": result["full_name"],
                    "samaccount": result["samaccount"],
                },
            )

            # Refresh tree to show new user
            self.action_refresh_ou()

            # Navigate to and select new user
            self.set_timer(0.5, lambda: self.expand_tree_to_dn(result["user_dn"]))
        elif result:
            # User cancelled dialog
            pass

    def handle_copy_user_confirmation(self, result):
        """Handle copy user confirmation result."""
        if result and result.get("success"):
            # Add to history for undo
            self.history_service.add(
                "copy_user",
                {
                    "user_dn": result["user_dn"],
                    "full_name": result["full_name"],
                    "samaccount": result["samaccount"],
                },
            )

            # Refresh tree to show new user
            self.action_refresh_ou()

            # Navigate to and select new user
            self.set_timer(0.5, lambda: self.expand_tree_to_dn(result["user_dn"]))
        elif result:
            # User cancelled dialog
            pass

    def undo_create_user(self, operation):
        """Undo create user operation."""
        try:
            user_dn = operation.details["user_dn"]
            success, message = self.ldap_service.delete_object(user_dn)

            if success:
                self.notify(
                    f"Undid: Created user {operation.details['full_name']}",
                    severity=Severity.INFORMATION.value,
                )
                self.action_refresh_ou()
            else:
                self.notify(
                    f"Failed to undo create user: {message}",
                    severity=Severity.ERROR.value,
                )
        except Exception as e:
            self.notify(
                f"Error undoing create user: {e}", severity=Severity.ERROR.value
            )

    def undo_copy_user(self, operation):
        """Undo copy user operation."""
        try:
            user_dn = operation.details["user_dn"]
            success, message = self.ldap_service.delete_object(user_dn)

            if success:
                self.notify(
                    f"Undid: Copied user {operation.details['full_name']}",
                    severity=Severity.INFORMATION.value,
                )
                self.action_refresh_ou()
            else:
                self.notify(
                    f"Failed to undo copy user: {message}",
                    severity=Severity.ERROR.value,
                )
        except Exception as e:
            self.notify(f"Error undoing copy user: {e}", severity=Severity.ERROR.value)

    def action_create_user(self):
        """Create new user account."""
        from .ui.dialogs import CreateUserDialog

        # Use current selected OU or base DN
        target_ou = self._get_current_ou()
        if not target_ou:
            target_ou = self.ldap_service.base_dn if self.ldap_service else self.base_dn

        self.push_screen(
            CreateUserDialog(target_ou, self.ldap_service),
            self.handle_create_user_confirmation,
        )

    def action_copy_user(self):
        """Copy existing user account."""
        from .ui.dialogs import CopyUserDialog

        if not self.current_selected_dn:
            self.notify("No user selected to copy", severity=Severity.WARNING.value)
            return

        # Check if selected object is a user
        if not self._is_user_object(self.current_selected_dn):
            self.notify(
                "Selected object is not a user", severity=Severity.WARNING.value
            )
            return

        # Use current selected OU as target
        target_ou = self._get_current_ou()
        if not target_ou:
            target_ou = self.ldap_service.base_dn if self.ldap_service else self.base_dn

        self.push_screen(
            CopyUserDialog(
                self.current_selected_dn,
                str(self.current_selected_label) if self.current_selected_label else "",
                target_ou,
                self.ldap_service,
            ),
            self.handle_copy_user_confirmation,
        )

    def action_copy_to_clipboard(self):
        """Copy selected text or object DN to clipboard."""
        # Check if details pane has selected text
        if hasattr(self, 'details') and hasattr(self.details, 'get_last_selected_text'):
            selected_text = self.details.get_last_selected_text()
            if selected_text:
                self._copy_to_system_clipboard(selected_text, "selection")
                self.details.clear_last_selected_text()
                return

        # Fall back to copying DN if no text selection
        if not self.current_selected_dn:
            self.notify("No object selected to copy", severity="warning")
            return

        self._copy_to_system_clipboard(self.current_selected_dn, "DN")

    def action_copy_selection(self):
        """Copy currently selected text to clipboard (Ctrl+C)."""
        # Try to get text selection from terminal
        # Note: This is a fallback since TUI apps can't directly access terminal selection
        # Users should use their terminal's native copy mechanism (Ctrl+Shift+C or right-click)
        self.notify(
            "Use terminal's copy function (Ctrl+Shift+C or right-click menu)",
            severity="information",
            timeout=3,
        )

    def _copy_to_system_clipboard(self, text: str, description: str):
        """Copy text to system clipboard with cross-platform support."""
        try:
            # Strip ANSI escape codes for clean copy
            import re

            ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
            clean_text = ansi_escape.sub("", text)

            # Remove excessive whitespace but keep newlines
            clean_text = "\n".join(
                line.strip() for line in clean_text.split("\n") if line.strip()
            )

            # Try different clipboard commands based on OS
            if sys.platform == "linux":
                # Try wl-copy first (Wayland), then xclip (X11)
                for cmd in ["wl-copy", "xclip -selection clipboard"]:
                    try:
                        subprocess.run(
                            cmd,
                            input=clean_text,
                            text=True,
                            check=True,
                            shell=True,
                            capture_output=True,
                        )
                        # Truncate long content for notification
                        display_text = (
                            clean_text[:50] + "..."
                            if len(clean_text) > 50
                            else clean_text
                        )
                        self.notify(
                            f"Copied {description}: {display_text}",
                            severity="information",
                        )
                        return
                    except (subprocess.CalledProcessError, FileNotFoundError):
                        continue
                # If neither works, try pbcopy (might be available)
                try:
                    subprocess.run(["pbcopy"], input=clean_text, text=True, check=True)
                    display_text = (
                        clean_text[:50] + "..." if len(clean_text) > 50 else clean_text
                    )
                    self.notify(
                        f"Copied {description}: {display_text}", severity="information"
                    )
                    return
                except (subprocess.CalledProcessError, FileNotFoundError):
                    pass
            elif sys.platform == "darwin":
                subprocess.run(["pbcopy"], input=clean_text, text=True, check=True)
                display_text = (
                    clean_text[:50] + "..." if len(clean_text) > 50 else clean_text
                )
                self.notify(
                    f"Copied {description}: {display_text}", severity="information"
                )
                return
            elif sys.platform == "win32":
                subprocess.run(
                    ["clip"], input=clean_text, text=True, check=True, shell=True
                )
                display_text = (
                    clean_text[:50] + "..." if len(clean_text) > 50 else clean_text
                )
                self.notify(
                    f"Copied {description}: {display_text}", severity="information"
                )
                return

            # If we get here, clipboard commands failed
            self.notify(
                "Clipboard not available. Install xclip or wl-copy on Linux.",
                severity="warning",
            )

        except Exception as e:
            self.notify(f"Failed to copy to clipboard: {e}", severity="error")

    def _get_current_ou(self) -> str:
        """Get currently selected OU DN."""
        if self.current_selected_dn:
            # Check if current selection is an OU
            if self.current_selected_label and "📁" in str(self.current_selected_label):
                return self.current_selected_dn
            else:
                # Get parent OU of selected object
                dn_parts = self.current_selected_dn.split(",")
                if len(dn_parts) > 1:
                    return ",".join(dn_parts[1:])

        # Fallback to base DN
        return self.ldap_service.base_dn if self.ldap_service else self.base_dn

    def _is_user_object(self, dn: str) -> bool:
        """Check if DN represents a user object."""
        try:
            self.ldap_service.conn.search(
                dn, "(objectClass=*)", search_scope="BASE", attributes=["objectClass"]
            )
            if self.ldap_service.conn.entries:
                obj_classes = [
                    str(cls).lower()
                    for cls in self.ldap_service.conn.entries[0].objectClass
                ]
                return "user" in obj_classes and "computer" not in obj_classes
            return False
        except Exception as e:
            logger.debug("Error checking if object is user: %s", e)
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


def run_setup_wizard() -> bool:
    """Run the interactive setup wizard to create config file.

    Returns:
        True if config was created successfully, False otherwise
    """
    import os
    from pathlib import Path
    from .services.platform_service import PlatformService

    config_dir = PlatformService.get_config_dir()
    config_file = config_dir / "config.ini"

    print("\n" + "=" * 60)
    print("   ADTUI - Active Directory Configuration Wizard")
    print("=" * 60 + "\n")

    if config_file.exists():
        print(f"Configuration file already exists at: {config_file}")
        response = input("Do you want to reconfigure? [y/N]: ").strip().lower()
        if response != "y":
            print("Keeping existing configuration.")
            return True
        # Backup existing config
        import shutil
        from datetime import datetime

        backup_name = f"config.ini.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.copy(config_file, config_dir / backup_name)
        print(f"Existing config backed up to: {backup_name}")

    # Create config directory
    config_dir.mkdir(parents=True, exist_ok=True)

    domains = []
    ad_configs = []

    while True:
        print(f"\n--- Active Directory #{len(domains) + 1} ---\n")

        # Domain name
        domain_name = input("Domain short name (e.g., CORP, DOMMAN): ").strip().upper()
        if not domain_name:
            print("Domain name cannot be empty.")
            continue

        # Server
        server = input("AD Server hostname (e.g., dc1.domain.com): ").strip()
        if not server:
            print("Server cannot be empty.")
            continue

        # Auto-detect base_dn from server name
        default_base_dn = ""
        if "." in server:
            parts = server.split(".")[1:]  # Skip hostname, keep domain parts
            default_base_dn = ",".join(f"DC={p}" for p in parts)

        if default_base_dn:
            base_dn = input(f"Base DN [{default_base_dn}]: ").strip()
            if not base_dn:
                base_dn = default_base_dn
        else:
            base_dn = input("Base DN (e.g., DC=domain,DC=com): ").strip()
            if not base_dn:
                print("Base DN cannot be empty.")
                continue

        # SSL
        use_ssl = input("Use SSL/TLS? [y/N]: ").strip().lower() == "y"

        domains.append(domain_name)
        ad_configs.append(
            {
                "domain": domain_name,
                "server": server,
                "base_dn": base_dn,
                "use_ssl": use_ssl,
            }
        )

        print(f"\n[OK] Added {domain_name} configuration")

        # Ask for another AD
        add_another = input("\nAdd another Active Directory? [y/N]: ").strip().lower()
        if add_another != "y":
            break

    # Write config file
    try:
        with open(config_file, "w") as f:
            f.write("# ADTUI Configuration\n")
            f.write("# Generated by setup wizard\n\n")
            f.write("[ad_domains]\n")
            f.write(f"domains = {', '.join(domains)}\n")

            for cfg in ad_configs:
                f.write(f"\n[ad_{cfg['domain']}]\n")
                f.write(f"server = {cfg['server']}\n")
                f.write(f"domain = {cfg['domain']}\n")
                f.write(f"base_dn = {cfg['base_dn']}\n")
                f.write(f"use_ssl = {'true' if cfg['use_ssl'] else 'false'}\n")
                f.write("max_retries = 5\n")
                f.write("initial_retry_delay = 1.0\n")
                f.write("max_retry_delay = 60.0\n")
                f.write("health_check_interval = 30.0\n")

            # Add legacy [ldap] section for backward compatibility
            first = ad_configs[0]
            f.write("\n# Legacy single AD support (for backward compatibility)\n")
            f.write("[ldap]\n")
            f.write(f"server = {first['server']}\n")
            f.write(f"domain = {first['domain']}\n")
            f.write(f"base_dn = {first['base_dn']}\n")
            f.write(f"use_ssl = {'true' if first['use_ssl'] else 'false'}\n")
            f.write("max_retries = 5\n")
            f.write("initial_retry_delay = 1.0\n")
            f.write("max_retry_delay = 60.0\n")
            f.write("health_check_interval = 30.0\n")

        print(f"\n[OK] Configuration saved to: {config_file}")
        if len(domains) > 1:
            print(
                f"[OK] Configured {len(domains)} Active Directory domains: {', '.join(domains)}"
            )
        print()
        return True

    except Exception as e:
        print(f"\n[ERROR] Failed to save configuration: {e}")
        return False


def _run_update(check_only: bool = False, quiet: bool = False) -> bool:
    """Run update check and optionally perform update.

    Args:
        check_only: If True, only check for updates without installing
        quiet: If True, suppress output unless update is available

    Returns:
        True if update was performed successfully or no update needed
    """
    from .services.update_service import UpdateService

    update_service = UpdateService()

    if not quiet:
        print("Checking for updates...")

    result = update_service.check_for_update(force=True)

    if result.error:
        if not quiet:
            print(f"Error checking for updates: {result.error}")
        return False

    if not result.update_available:
        if not quiet:
            print(f"ADTUI {result.current_version} is up to date.")
        return True

    print(f"Update available: {result.current_version} -> {result.latest_version}")

    if check_only:
        return True

    print("Installing update...")
    success, message = update_service.perform_update()

    if success:
        print(f"Update successful: {message}")
        print("Please restart ADTUI to use the new version.")
    else:
        print(f"Update failed: {message}")

    return success


def main():
    """Main entry point for application."""
    import argparse
    import os
    from pathlib import Path

    from . import __version__

    # Parse command-line arguments before starting Textual
    parser = argparse.ArgumentParser(
        description="ADTUI - Active Directory Terminal User Interface"
    )
    parser.add_argument(
        "--version", "-V",
        action="version",
        version=f"adtui {__version__}"
    )
    parser.add_argument(
        "--update", "-u",
        action="store_true",
        help="Check for updates and install if available, then exit"
    )
    parser.add_argument(
        "--check-update",
        action="store_true",
        help="Check for updates without installing, then exit"
    )
    parser.add_argument(
        "--no-auto-update",
        action="store_true",
        help="Skip automatic update check and installation at startup"
    )
    args = parser.parse_args()

    # Handle update flags
    if args.update:
        _run_update(check_only=False)
        return

    if args.check_update:
        _run_update(check_only=True)
        return

    # Auto-update before launching (default behavior)
    if not args.no_auto_update:
        try:
            from .services.update_service import UpdateService
            update_service = UpdateService()
            result = update_service.check_for_update()

            if result.update_available:
                print(f"Update available: {result.current_version} -> {result.latest_version}")
                print("Installing update...")

                success, message = update_service.perform_update()
                if success:
                    print(f"Update successful: {message}")
                    print("Please restart ADTUI to use the new version.")
                    return
                else:
                    print(f"Auto-update failed: {message}")
                    print("Continuing with current version...\n")
        except Exception as e:
            # Silently continue if update check fails
            pass

    # Check if config exists, if not run wizard
    from .services.platform_service import PlatformService

    config_paths = [
        PlatformService.get_config_dir() / "config.ini",
        Path.cwd() / "config.ini",
    ]
    # Add legacy Unix path only on non-Windows
    legacy_path = PlatformService.get_legacy_config_path("config.ini")
    if legacy_path:
        config_paths.insert(1, legacy_path)

    config_exists = any(p.exists() for p in config_paths)

    if not config_exists:
        print("No configuration file found.")
        if not run_setup_wizard():
            return

    # Load configuration
    try:
        config_service = ConfigService()
    except FileNotFoundError:
        # Config still not found, offer to run wizard
        response = (
            input("Would you like to run the setup wizard? [Y/n]: ").strip().lower()
        )
        if response != "n":
            if not run_setup_wizard():
                return
            # Try loading again
            try:
                config_service = ConfigService()
            except Exception as e:
                print(f"Failed to load configuration: {e}")
                return
        else:
            return
    except Exception as e:
        print(f"Error loading configuration: {e}")
        return

    # Validate configuration
    is_valid, issues = config_service.validate_config()
    if not is_valid:
        logger.error("Configuration errors:")
        for issue in issues:
            logger.error("  - %s", issue)
        return

    # Main loop to allow restarting login on auth failure
    while True:
        # Global variables to store login results
        selected_domain = None
        login_credentials = None
        user_cancelled = False

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
                ascii_art = f"""[bold cyan]┏━┃┏━   ━┏┛┃ ┃┛[/bold cyan]
[blue]  ┏━┃┃ ┃   ┃ ┃ ┃┃[/blue]
[dark_blue]┛ ┛━━    ┛ ━━┛┛[/dark_blue]
              [dim]v{__version__}[/dim]"""

                yield Static(
                    f"{ascii_art}\n\n[bold cyan]Active Directory TUI[/bold cyan]\n"
                )

            def on_mount(self) -> None:
                nonlocal selected_domain, login_credentials

                # Check if we need to show AD selection dialog
                if config_service.has_multiple_domains():
                    # Show AD selection dialog first
                    self.push_screen(
                        ADSelectionDialog(config_service.ad_configs),
                        self.handle_ad_selection,
                    )
                else:
                    # Skip AD selection, use the default domain
                    selected_domain = config_service.get_default_domain()
                    self.show_login_dialog()

            def handle_ad_selection(self, domain):
                """Handle AD domain selection."""
                nonlocal selected_domain, user_cancelled
                if domain:
                    selected_domain = domain
                    self.show_login_dialog()
                else:
                    user_cancelled = True
                    self.exit()

            def show_login_dialog(self):
                """Show the login dialog."""
                nonlocal login_credentials
                ad_config = config_service.get_config(selected_domain)
                self.push_screen(
                    LoginDialog(last_user, ad_config.domain), self.handle_login_result
                )

            def handle_login_result(self, result):
                """Handle login result."""
                nonlocal login_credentials, user_cancelled
                if result:
                    username, password = result

                    # Save username to file
                    with open(LAST_USER_FILE, "w") as f:
                        f.write(username)

                    # Store credentials and exit login app
                    login_credentials = (username, password)
                    self.exit()
                else:
                    user_cancelled = True
                    self.exit()

            def on_key(self, event) -> None:
                nonlocal user_cancelled
                if event.key == "escape":
                    user_cancelled = True
                    self.exit()

        # Run login flow app first
        login_app = LoginFlowApp()
        login_app.run()

        # If user cancelled (escape or cancel button), exit completely
        if user_cancelled:
            return

        # After login app exits, check if we have credentials and start main app
        if login_credentials and selected_domain:
            # Clear the screen immediately to minimize CLI gap
            os.system("cls" if os.name == "nt" else "clear")

            username, password = login_credentials
            ad_config = config_service.get_config(selected_domain)

            try:
                # Create and run the main app with credentials and AD config
                app = ADTUI(username, password, ad_config)
                app.run()

                # Check if app exited due to auth failure (should restart login)
                # If app.auth_failed is True, continue loop to show login again
                if getattr(app, "auth_failed", False):
                    # Clear screen and show message before restarting login
                    os.system("cls" if os.name == "nt" else "clear")
                    logger.warning("Authentication failed. Please try again.")
                    continue
                else:
                    # Normal exit - break the loop
                    break
            except Exception as e:
                logger.error("Error running application: %s", e)
                break
        else:
            # No credentials provided, exit
            return


if __name__ == "__main__":
    main()
