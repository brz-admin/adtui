"""ADTUI - Active Directory Terminal UI - Refactored Version."""

import logging
import os
import re
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
    from .widgets.page_list_view import PageListView
    from .services import LDAPService, HistoryService, PathService, ADSession
    from .services.config_service import ConfigService, ADConfig
    from .services.connection_manager import ConnectionManager, ConnectionState
    from .commands import CommandHandler
    from .ui.dialogs import (
        ConfirmDeleteDialog,
        ConfirmForceDeleteDialog,
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
    from widgets.page_list_view import PageListView
    from services import LDAPService, HistoryService, PathService, ADSession
    from services.config_service import ConfigService, ADConfig
    from services.connection_manager import ConnectionManager, ConnectionState
    from commands import CommandHandler
    from .ui.dialogs import (
        ConfirmDeleteDialog,
        ConfirmForceDeleteDialog,
        ConfirmMoveDialog,
        ConfirmRestoreDialog,
        ConfirmUndoDialog,
        CreateOUDialog,
        ADSelectionDialog,
        LoginDialog,
    )
from .constants import Severity, MESSAGES

# Configuration will be loaded after AD selection
from .services.platform_service import PlatformService

_config_dir = PlatformService.get_config_dir()
_config_dir.mkdir(parents=True, exist_ok=True)
LAST_USER_FILE = str(_config_dir / "last_user.txt")

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


# ":m <path>", ":mv <path>", ":move <path>" (path may be empty)
_MOVE_RE = re.compile(r"^:(?P<cmd>m|mv|move)\s+(?P<path>.*)$", re.IGNORECASE)
# ":m", ":mv", ":move" before the space is typed
_MOVE_PREFIX_RE = re.compile(r"^:(m|mv|move)$", re.IGNORECASE)


class SearchResultsPane(PageListView):
    """ListView for displaying search results."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connection_manager = None
        # Session the displayed results come from
        self.session = None

    def populate(self, results, connection_manager=None, session=None):
        """Populate the search results pane.

        Args:
            results: List of result dictionaries with 'label' and 'dn'
            connection_manager: Optional ConnectionManager instance
            session: ADSession the results belong to
        """
        self.clear()
        self.connection_manager = connection_manager
        self.session = session
        for result in results:
            item = ListItem(Label(result["label"]))
            item.text = result["label"]
            item.data = result["dn"]
            # Optional extra payload (used by the move autocomplete)
            item.path = result.get("path")
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
        Binding("G", "create_group", "Create Group", show=False),
        # User-specific commands - hidden from footer but still functional
        Binding("a", "edit_attributes", "Attributes", show=False),
        Binding("g", "manage_groups", "Groups", show=False),
        Binding("p", "set_password", "Password", show=False),

        Binding("l", "edit_upn", "Logon (UPN)", show=False),
        Binding("C", "copy_user", "Copy User", show=False),
        Binding("y", "copy_to_clipboard", "Copy Text", show=True),
        Binding("ctrl+c", "copy_selection", "Copy Selection", show=True),
        Binding("d", "delete_object", "Delete", show=False),
        Binding("u", "undo", "Undo", show=False),
        Binding("e", "enable_disable_user", "Enable/Disable", show=False),
        Binding("U", "unlock_user", "Unlock", show=False),
        Binding("?", "show_help", "Help", show=False),
        Binding("escape", "cancel_command", "Cancel", show=False),
        # Priority so it beats the Screen's own tab binding; only active while
        # completing a path (see check_action), otherwise Tab cycles focus as usual
        Binding("tab", "cycle_focus", "Cycle Focus", show=False, priority=True),
        # Move autocomplete: pick a suggestion without leaving the input
        Binding("up", "ac_up", show=False, priority=True),
        Binding("down", "ac_down", show=False, priority=True),
        Binding("plus", "connect_ad", "Add AD", show=True, key_display="+"),
    ]

    def __init__(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None,
        ad_config: Optional[ADConfig] = None,
        config_service: Optional[ConfigService] = None,
    ):
        """Initialize the application.

        Args:
            username: AD username (optional for deferred login)
            password: AD password (optional for deferred login)
            ad_config: AD configuration (optional for deferred login)
            config_service: Loaded configuration, used by :connect to offer
                the other configured ADs
        """
        super().__init__()

        self.ad_config = ad_config
        self.config_service = config_service or getattr(self, "config_service", None)

        # Several ADs can be connected at once: one session per connection.
        # The "active" session is the one every action is performed with.
        self.sessions: list[ADSession] = []
        self.active_session: Optional[ADSession] = None

        # Widgets shared by all sessions
        self._placeholder_tree = ADTree(None, "")
        self.details = DetailsPane(id="details-pane")
        self.search_results_pane = SearchResultsPane(id="search-results-pane")
        self.command_handler = CommandHandler(self)

        # Pending operations
        self.pending_delete_dn: Optional[str] = None
        self.pending_force_delete_dn: Optional[str] = None
        self.pending_move_dn: Optional[str] = None
        self.pending_move_target: Optional[str] = None
        self.pending_restore_dn: Optional[str] = None
        self.pending_restore_label: Optional[str] = None

        # State management
        self.command_mode = False
        self.autocomplete_mode = False
        self._ac_timer = None
        self._ac_generation = 0

        # Current selection
        self.current_selected_dn: Optional[str] = None
        self.current_selected_label: Optional[str] = None

        # Auth failure flag - used to signal main() to restart login flow
        self.auth_failed = False

        # Update check result (populated asynchronously)
        self._update_result = None

        # Only establish connection if credentials are provided
        if username is not None and password is not None and ad_config is not None:
            manager = create_connection_manager(username, password, ad_config)
            self._register_session(ADSession(ad_config, username, manager))

    # ==================== Sessions (one per connected AD) ====================

    # Everything below proxies to the active session, so the rest of the code
    # keeps using self.ldap_service / self.connection_manager / ... and
    # automatically acts with the account of the AD the user is working in.

    @property
    def connection_manager(self):
        return self.active_session.connection_manager if self.active_session else None

    @property
    def ldap_service(self):
        return self.active_session.ldap_service if self.active_session else None

    @property
    def path_service(self):
        return self.active_session.path_service if self.active_session else None

    @property
    def history_service(self):
        return self.active_session.history_service if self.active_session else None

    @property
    def base_dn(self) -> str:
        if self.active_session:
            return self.active_session.base_dn
        return self.ad_config.base_dn if self.ad_config else ""

    @property
    def adtree(self):
        if self.active_session and self.active_session.adtree is not None:
            return self.active_session.adtree
        return self._placeholder_tree

    def _register_session(self, session: ADSession) -> ADSession:
        """Create the tree for a new session and start monitoring it.

        Safe to call before the app runs (tree is composed later) and from the
        UI thread while running (tree is mounted immediately).
        """
        session.adtree = ADTree(
            session.connection_manager, session.base_dn, session=session
        )
        self.sessions.append(session)
        self.active_session = session

        session.connection_manager.add_state_change_callback(
            lambda state, error=None, s=session: self._on_connection_state_change(
                s, state, error
            )
        )
        session.connection_manager.set_auth_failure_callback(
            lambda s=session: self._on_authentication_failure(s)
        )

        if self.is_running:
            self._mount_session_tree(session)
        return session

    def _mount_session_tree(self, session: ADSession) -> None:
        """Add a session's tree below the existing ones."""
        columns = self.query("#tree-column")
        if not columns:
            return  # layout not built yet: it will include this tree
        column = columns.first()
        if self._placeholder_tree.parent is not None:
            self._placeholder_tree.remove()
        column.mount(session.adtree)
        self._clear_selection()
        self._refresh_tree_styles()
        self.set_timer(0.5, lambda: self._expand_tree_on_startup(session))
        session.adtree.focus()

    def _make_tree_column(self) -> Vertical:
        """Build the left column holding one tree per session."""
        trees = [s.adtree for s in self.sessions if s.adtree is not None]
        column = Vertical(*(trees or [self._placeholder_tree]), id="tree-column")
        return column

    def _refresh_tree_styles(self) -> None:
        """Update tree titles and highlight the tree of the active session."""
        multi = len(self.sessions) > 1
        for session in self.sessions:
            tree = session.adtree
            if tree is None:
                continue
            tree.border_title = session.title
            tree.set_class(multi and session is self.active_session, "-active")
            tree.set_class(multi, "-multi")

    def _set_active_session(
        self, session: Optional[ADSession], clear_selection: bool = True
    ) -> None:
        """Make ``session`` the one actions are performed with.

        The current selection belongs to a single AD, so it is cleared when the
        active session changes (otherwise a DN of one AD could be acted upon
        with the account of the other).
        """
        if session is None or session is self.active_session:
            return
        self.active_session = session
        if clear_selection:
            self._clear_selection()
        self._refresh_tree_styles()

    def _clear_selection(self) -> None:
        self.current_selected_dn = None
        self.current_selected_label = None
        try:
            self.details.update_content("No selection", None, None)
        except Exception:
            pass

    def on_descendant_focus(self, event) -> None:
        """Working in a tree switches to the account that tree was opened with."""
        widget = event.widget
        if isinstance(widget, ADTree) and widget.session is not None:
            self._set_active_session(widget.session)

    def remove_session(self, session: ADSession) -> None:
        """Disconnect one AD and remove its tree."""
        if session not in self.sessions:
            return
        index = self.sessions.index(session)
        self.sessions.remove(session)
        session.close()
        if session.adtree is not None and session.adtree.parent is not None:
            session.adtree.remove()

        if self.search_results_pane.session is session:
            self.search_results_pane.clear()
            self.search_results_pane.session = None
            self.search_results_pane.styles.display = "none"

        if self.active_session is session:
            self.active_session = None
            if self.sessions:
                nxt = self.sessions[min(index, len(self.sessions) - 1)]
                self._clear_selection()
                self.active_session = nxt
                if nxt.adtree is not None:
                    nxt.adtree.focus()
        self._refresh_tree_styles()

    def _find_session(self, domain: str, username: str) -> Optional[ADSession]:
        for s in self.sessions:
            if s.name.lower() == domain.lower() and s.username.lower() == username.lower():
                return s
        return None

    def _get_config_service(self) -> Optional[ConfigService]:
        if self.config_service is None:
            try:
                self.config_service = ConfigService()
            except Exception as e:
                logger.error("Could not load configuration: %s", e)
        return self.config_service

    def compose(self) -> ComposeResult:
        """Compose the UI layout."""
        with Horizontal():
            yield self._make_tree_column()
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
        self._refresh_tree_styles()
        # Keyboard shortcuts only work outside the (hidden) command input
        self.adtree.focus()

        # Expand tree to show root level on startup with delay to ensure initialization
        self.set_timer(0.5, self._expand_tree_on_startup)
        # Also try to rebuild tree after a longer delay to ensure connection is ready
        self.set_timer(2.0, self._delayed_tree_rebuild)

        # Check for updates in background
        self._start_update_check()

        # After an update, tell the user what changed
        self.set_timer(0.8, self._show_whats_new)

    def _show_whats_new(self) -> None:
        """Show the (French) release notes once after an update."""
        try:
            from . import __version__
            from .services.whats_new import (
                WhatsNewTracker,
                format_notes,
                unseen_notes,
            )
            from .ui.dialogs import WhatsNewDialog

            tracker = WhatsNewTracker()
            entries = unseen_notes(__version__, tracker.load())
            tracker.save(__version__)
            if entries:
                self.push_screen(WhatsNewDialog(__version__, format_notes(entries)))
        except Exception as e:
            logger.debug("Could not show what's new: %s", e)

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
        # OUs may have been created/moved/deleted: refresh the move autocomplete list
        if self.active_session:
            self.active_session.ou_index.invalidate()
        tree = self.focused if isinstance(self.focused, ADTree) else self.adtree
        tree.refresh_current_ou()

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
            self._end_autocomplete()
            # Hide search results if visible
            self.search_results_pane.styles.display = "none"
            # Return focus to tree
            self.adtree.focus()

    def action_cycle_focus(self):
        """Tab: complete the highlighted suggestion in autocomplete, else cycle focus."""
        if self.autocomplete_mode:
            cmd_input = self.query_one("#command-input", Input)
            if self.focused is cmd_input:
                self._ac_complete_highlighted()
            else:
                # Focus ended up on the suggestions (mouse): back to typing
                cmd_input.focus()
        else:
            # Normal tab behavior
            self.focus_next()

    def check_action(self, action: str, parameters) -> Optional[bool]:
        """Up/Down only steer the suggestions while the move autocomplete is typing."""
        if action == "cycle_focus":
            return bool(self.autocomplete_mode and self.command_mode)
        if action in ("ac_up", "ac_down"):
            return bool(
                self.autocomplete_mode
                and self.command_mode
                and isinstance(self.focused, Input)
            )
        return super().check_action(action, parameters)

    def action_ac_up(self):
        self.search_results_pane.action_cursor_up()

    def action_ac_down(self):
        self.search_results_pane.action_cursor_down()

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

    def action_edit_upn(self):
        """Edit logon name (userPrincipalName) for selected user."""
        if not self.current_selected_dn:
            self.notify("No object selected", severity="warning")
            return

        if self.current_selected_label and "👤" in str(self.current_selected_label):
            from .ui.dialogs import EditUPNDialog

            # Need user details to get the current UPN
            from widgets.user_details import UserDetailsPane

            user_details = UserDetailsPane()
            user_details.update_user_details(
                self.current_selected_dn, self.connection_manager
            )

            current_upn = ""
            if user_details.entry and hasattr(
                user_details.entry, "userPrincipalName"
            ):
                value = user_details.entry.userPrincipalName.value
                if value:
                    current_upn = str(value)

            self.push_screen(
                EditUPNDialog(
                    self.current_selected_dn,
                    self.connection_manager,
                    current_upn,
                    self.base_dn,
                ),
                self.handle_upn_edit_result,
            )
        else:
            self.notify(
                "Logon name editing only available for users", severity="warning"
            )

    def handle_upn_edit_result(self, result):
        """Refresh details pane after editing the UPN."""
        if result and hasattr(self, "details") and self.details:
            self.details.refresh_details()

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
        self,
        session: ADSession,
        state: ConnectionState,
        error: Optional[str] = None,
    ):
        """Handle connection state changes of one session.

        Args:
            session: Session whose connection changed
            state: New connection state
            error: Optional error message
        """
        # With several ADs connected, say which one the message is about
        where = session.name if len(self.sessions) > 1 else "Active Directory"

        # Use call_from_thread since this callback may be invoked from background threads
        def update_ui():
            if session not in self.sessions:
                return
            if state == ConnectionState.CONNECTED:
                self.notify(f"Connected to {where}", severity="information")
                # Rebuild tree when connection is established
                if session.adtree is not None:
                    session.adtree.build_tree()
            elif state == ConnectionState.RECONNECTING:
                self.notify(
                    f"Reconnecting to {where}... {error or ''}", severity="warning"
                )
            elif state == ConnectionState.FAILED:
                self.notify(
                    f"{where}: connection failed: {error or 'Unknown error'}",
                    severity="error",
                )

        self.call_from_thread(update_ui)

    def _on_authentication_failure(self, session: Optional[ADSession] = None):
        """Authentication failed (called from the connection manager's thread)."""
        self.call_from_thread(self._handle_session_auth_failure, session)

    def _handle_session_auth_failure(self, session: Optional[ADSession] = None):
        """Handle authentication failure of a session (UI thread).

        With a single AD connected: exit to restart the login flow. With
        several, only the failing one is dropped and the others keep working.
        """
        try:
            if session is not None and len(self.sessions) > 1:
                name = session.title
                self.remove_session(session)
                self.notify(
                    f"Authentication failed for {name}: disconnected. "
                    "Use :connect to log in again.",
                    severity="error",
                    timeout=10,
                )
                return

            # Set auth failure flag so main() knows to restart login
            self.auth_failed = True

            for s in list(self.sessions):
                s.close()
            self.sessions.clear()
            self.active_session = None

            # Exit main app to trigger login restart in main script
            self.exit()

        except Exception:
            import traceback

            traceback.print_exc()

    # ==================== Input Handling ====================

    def on_input_changed(self, event: Input.Changed):
        """Handle input changes for autocomplete."""
        if self.command_mode and event.input.id == "command-input":
            match = _MOVE_RE.match(event.value)
            if match and self.active_session:
                self._request_autocomplete(match.group("path"))
            elif self.autocomplete_mode:
                self._end_autocomplete(hide_pane=True)
            else:
                # ":m" / ":mv" / ":move" typed so far: warm the OU list up so the
                # first suggestions are instant once the path is being typed
                if _MOVE_PREFIX_RE.match(event.value) and self.active_session:
                    self._ensure_ou_index(self.active_session)

    def on_input_submitted(self, event: Input.Submitted):
        """Handle command submission."""
        if self.command_mode:
            cmd = event.value.strip()

            match = _MOVE_RE.match(cmd)
            if match and self.active_session:
                # Resolve what was typed (or the highlighted suggestion) to a DN
                target = self._ac_resolve_target(match.group("path"))
                if target is None:
                    return  # message shown, keep the input open to fix the path
                cmd = f":{match.group('cmd')} {target}"

            if self.autocomplete_mode:
                self._end_autocomplete(hide_pane=True)

            # Cleanup first so command output (search results, dialogs) wins focus
            cmd_input = self.query_one("#command-input", Input)
            cmd_input.value = ""
            cmd_input.visible = False
            self.command_mode = False
            self.adtree.focus()

            # Execute command via handler
            self.command_handler.execute(cmd)

    # ==================== Selection Handlers ====================

    def on_tree_node_selected(self, event: Tree.NodeSelected):
        """Handle tree node selection."""
        tree = event.control
        if isinstance(tree, ADTree) and tree.session is not None:
            self._set_active_session(tree.session)
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
                # Results belong to the AD they were searched in
                self._set_active_session(
                    self.search_results_pane.session, clear_selection=False
                )
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
                    # Clicked/Entered a suggestion: complete it and keep typing
                    self._ac_complete_item(item)
                    self.query_one("#command-input", Input).focus()
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

    def _expand_tree_on_startup(self, session: Optional[ADSession] = None) -> None:
        """Expand tree(s) to show root level on startup."""
        for sess in [session] if session else list(self.sessions):
            try:
                tree = sess.adtree
                if tree is not None and tree.connection_manager and tree.root.children:
                    root_node = tree.root.children[0]  # Base DN node
                    # Ensure root node is expanded and loaded
                    if not root_node.is_expanded:
                        root_node.expand()
                        tree.ensure_node_loaded(root_node)
            except Exception:
                # Silently fail - tree expansion is a nice-to-have feature
                pass

    def _delayed_tree_rebuild(self) -> None:
        """Rebuild trees after delay to ensure connections are ready."""
        for sess in list(self.sessions):
            try:
                if sess.adtree is not None and sess.adtree.connection_manager:
                    sess.adtree.build_tree()
            except Exception:
                import traceback

                traceback.print_exc()

    # ==================== Autocomplete ====================

    # Hint shown in the border of the suggestion list while completing a path
    _AC_HINT = "Move to ▸ ↑↓ choose · Tab complete · Enter move · Esc cancel"

    def _ensure_ou_index(self, session: ADSession) -> None:
        """Load (or refresh) the session's OU list in the background."""
        index = session.ou_index
        if not index.needs_load:
            return

        def load():
            index.load(session.ldap_service.list_all_ou_dns)
            self.call_from_thread(self._on_ou_index_ready, session)

        self.run_worker(load, thread=True, group=f"ou-index-{session.id}")

    def _on_ou_index_ready(self, session: ADSession) -> None:
        """OU list arrived: refresh the suggestions for what is typed now."""
        if session.ou_index.last_error:
            self.notify(
                f"Could not list OUs of {session.name}: {session.ou_index.last_error}",
                severity="error",
            )
        if self.autocomplete_mode and session is self.active_session:
            match = _MOVE_RE.match(self.query_one("#command-input", Input).value)
            if match:
                self._show_suggestions(match.group("path"))

    def _request_autocomplete(self, text: str) -> None:
        """Typed text after :move changed: show matching OUs."""
        session = self.active_session
        if session is None:
            return
        self.autocomplete_mode = True
        self._ensure_ou_index(session)
        self._show_suggestions(text)

    def _show_suggestions(self, text: str) -> None:
        """Fill the list under the input with the OUs matching ``text``."""
        session = self.active_session
        pane = self.search_results_pane
        pane.add_class("autocomplete")
        pane.border_title = self._AC_HINT
        pane.styles.display = "block"

        index = session.ou_index
        if not index.is_loaded:
            message = (
                "Loading OUs…" if index.is_loading or index.needs_load else "No OU list"
            )
            pane.populate(
                [{"label": f"[dim]{message}[/dim]", "dn": None}], session=session
            )
            return

        entries = index.search(text, limit=50)
        suggestions = [
            {
                "label": "📁 " + self._highlight_match(e.path, text),
                "dn": e.dn,
                "path": e.path,
            }
            for e in entries
        ]
        if not suggestions:
            if text.rstrip().endswith("/") and index.find(text):
                msg = "No sub-OUs here · Enter moves to this OU"
            else:
                msg = "No matching OU"
            suggestions = [{"label": f"[dim]{msg}[/dim]", "dn": None}]
        pane.populate(suggestions, session=session)

    @staticmethod
    def _highlight_match(path: str, text: str) -> str:
        """Markup for ``path`` with the part matching what was typed in bold."""
        from rich.markup import escape

        needle = text.replace("\\", "/").rsplit("/", 1)[-1].strip().lower()
        pos = path.lower().rfind(needle) if needle else -1
        if pos < 0:
            return escape(path)
        end = pos + len(needle)
        return (
            f"{escape(path[:pos])}[bold yellow]{escape(path[pos:end])}[/]"
            f"{escape(path[end:])}"
        )

    def _end_autocomplete(self, hide_pane: bool = False) -> None:
        """Leave autocomplete mode and restore the suggestion list's look."""
        was_active = self.autocomplete_mode
        self.autocomplete_mode = False
        pane = self.search_results_pane
        pane.remove_class("autocomplete")
        pane.border_title = ""
        if hide_pane and was_active:
            pane.clear()
            pane.styles.display = "none"

    def _ac_set_input(self, cmd: str, path: str) -> None:
        cmd_input = self.query_one("#command-input", Input)
        cmd_input.value = f":{cmd} {path}"
        cmd_input.cursor_position = len(cmd_input.value)

    def _ac_complete_item(self, item) -> None:
        """Put a suggestion in the input; descend into it when it has sub-OUs."""
        path = getattr(item, "path", None)
        if not path or not self.active_session:
            return
        index = self.active_session.ou_index
        suffix = "/" if index.children(path) else ""
        match = _MOVE_RE.match(self.query_one("#command-input", Input).value)
        cmd = match.group("cmd") if match else "m"
        self._ac_set_input(cmd, path + suffix)

    def _ac_complete_highlighted(self) -> None:
        item = self.search_results_pane.highlighted_child
        if item is not None:
            self._ac_complete_item(item)

    def _ac_resolve_target(self, text: str) -> Optional[str]:
        """DN to move to for what was typed after :move, or None (error shown).

        An exact path wins; otherwise the highlighted suggestion is used so
        that typing "IT" and pressing Enter works without having to Tab first.
        """
        text = text.strip()
        if not text:
            self.notify(MESSAGES["TARGET_REQUIRED"], severity=Severity.WARNING.value)
            return None
        if "=" in text and "," in text:
            return text  # already a DN

        index = self.active_session.ou_index
        if not index.is_loaded:
            self.notify("Still loading the OU list, try again…", severity="warning")
            self._ensure_ou_index(self.active_session)
            return None

        entry = index.find(text)
        if entry is None and self.autocomplete_mode:
            item = self.search_results_pane.highlighted_child
            if item is not None and getattr(item, "path", None):
                entry = index.find(item.path)
        if entry is None:
            self.notify(
                f"No OU matches '{text}'", severity=Severity.WARNING.value
            )
            return None
        return entry.dn

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
            self.active_session.ou_index.invalidate()
        else:
            # Check if the failure is due to deletion protection
            if self.ldap_service.is_protected_from_deletion(dn):
                self.pending_force_delete_dn = dn
                label = (
                    str(self.current_selected_label)
                    if self.current_selected_label
                    else ""
                )
                self.push_screen(
                    ConfirmForceDeleteDialog(label, dn),
                    self.handle_force_delete_confirmation,
                )
            else:
                self.notify(message, severity=Severity.ERROR.value)

    def handle_force_delete_confirmation(self, confirmed: bool):
        """Handle force delete confirmation for protected objects."""
        if confirmed and self.pending_force_delete_dn:
            dn = self.pending_force_delete_dn
            # Remove the deletion protection first
            success, message = self.ldap_service.remove_deletion_protection(dn)
            if success:
                # Retry the delete now that protection is removed
                success, message = self.ldap_service.delete_object(dn)
                if success:
                    self.notify(
                        "Protection removed and object deleted. Use :recycle to restore if needed.",
                        severity=Severity.INFORMATION.value,
                    )
                    self.current_selected_dn = None
                    self.current_selected_label = None
                    if hasattr(self, "details") and self.details:
                        self.details.update_content("No selection", None, None)
                    self.adtree.remove_node_by_dn(dn)
                else:
                    self.notify(message, severity=Severity.ERROR.value)
            else:
                self.notify(message, severity=Severity.ERROR.value)
        else:
            self.notify(
                MESSAGES["DELETE_CANCELLED"], severity=Severity.INFORMATION.value
            )
        self.pending_force_delete_dn = None

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

    def handle_copy_groups_confirmation(
        self, confirmed: bool, source_dn: str, target_dn: str
    ):
        """Handle copy groups confirmation result."""
        if not confirmed:
            return
        try:
            success, message, _added = self.ldap_service.copy_groups(
                source_dn, target_dn
            )
            severity = Severity.INFORMATION if success else Severity.ERROR
            self.notify(message, severity=severity.value)
            self.refresh_current_view()
        except Exception as e:
            self.notify(f"Error copying groups: {e}", severity=Severity.ERROR.value)

    def action_enable_disable_user(self):
        """Toggle enable/disable on the selected user account."""
        if not self.current_selected_dn:
            self.notify(MESSAGES["NO_SELECTION"], severity=Severity.WARNING.value)
            return

        if not self._is_user_object(self.current_selected_dn):
            self.notify(
                "Enable/Disable can only be performed on user accounts",
                severity=Severity.WARNING.value,
            )
            return

        # Check current account status to determine whether to enable or disable
        try:

            def check_status(conn):
                conn.search(
                    self.current_selected_dn,
                    "(objectClass=user)",
                    search_scope="BASE",
                    attributes=["userAccountControl"],
                )
                if not conn.entries:
                    return None
                entry = conn.entries[0]
                if (
                    hasattr(entry, "userAccountControl")
                    and entry.userAccountControl.value
                ):
                    return int(entry.userAccountControl.value)
                return 0

            current_uac = self.ldap_service.connection_manager.execute_with_retry(
                check_status
            )

            if current_uac is None:
                self.notify("User not found", severity=Severity.ERROR.value)
                return

            is_disabled = bool(current_uac & 0x0002)
        except Exception as e:
            self.notify(
                f"Error checking account status: {e}", severity=Severity.ERROR.value
            )
            return

        if is_disabled:
            from ui.dialogs import ConfirmEnableDialog

            self.push_screen(
                ConfirmEnableDialog(
                    self.current_selected_label, self.current_selected_dn
                ),
                self.handle_enable_confirmation,
            )
        else:
            from ui.dialogs import ConfirmDisableDialog

            self.push_screen(
                ConfirmDisableDialog(
                    self.current_selected_label, self.current_selected_dn
                ),
                self.handle_disable_confirmation,
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

    def handle_create_group_confirmation(self, result):
        """Handle create group confirmation result."""
        if result and result.get("success"):
            # Add to history for undo
            self.history_service.add(
                "create_group",
                {
                    "group_dn": result["group_dn"],
                    "group_name": result["group_name"],
                },
            )

            # Refresh tree to show new group
            self.action_refresh_ou()

            # Navigate to and select new group
            self.set_timer(0.5, lambda: self.expand_tree_to_dn(result["group_dn"]))
        elif result:
            # User cancelled dialog
            pass

    def undo_create_group(self, operation):
        """Undo create group operation."""
        try:
            group_dn = operation.details["group_dn"]
            success, message = self.ldap_service.delete_object(group_dn)

            if success:
                self.notify(
                    f"Undid: Created group {operation.details['group_name']}",
                    severity=Severity.INFORMATION.value,
                )
                self.action_refresh_ou()
            else:
                self.notify(
                    f"Failed to undo create group: {message}",
                    severity=Severity.ERROR.value,
                )
        except Exception as e:
            self.notify(
                f"Error undoing create group: {e}", severity=Severity.ERROR.value
            )

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

    def action_create_group(self):
        """Create new AD group."""
        from .ui.dialogs import CreateGroupDialog

        # Use current selected OU or base DN
        target_ou = self._get_current_ou()
        if not target_ou:
            target_ou = self.ldap_service.base_dn if self.ldap_service else self.base_dn

        self.push_screen(
            CreateGroupDialog(target_ou, self.ldap_service),
            self.handle_create_group_confirmation,
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
        if hasattr(self, "details") and hasattr(self.details, "get_last_selected_text"):
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

    def action_logout(self):
        """Disconnect everything and return to login screen for domain switching."""
        for session in list(self.sessions):
            session.close()
        self.sessions.clear()
        self.active_session = None

        # Signal that we need to restart login flow
        self.auth_failed = True
        self.exit()

    # ==================== Connecting several ADs ====================

    def action_connect_ad(self, domain: Optional[str] = None):
        """Log in to another AD (or the same one with another account)."""
        config_service = self._get_config_service()
        if config_service is None or not config_service.ad_configs:
            self.notify("No AD configured", severity="error")
            return

        if domain:
            wanted = {d.lower(): d for d in config_service.ad_configs}
            if domain.lower() not in wanted:
                self.notify(
                    f"Unknown domain '{domain}'. Configured: "
                    + ", ".join(config_service.ad_configs),
                    severity="warning",
                )
                return
            self._prompt_connect_login(wanted[domain.lower()])
        elif config_service.has_multiple_domains():
            self.push_screen(
                ADSelectionDialog(config_service.ad_configs),
                lambda d: self._prompt_connect_login(d) if d else None,
            )
        else:
            self._prompt_connect_login(config_service.get_default_domain())

    def _prompt_connect_login(self, domain: str, user: Optional[str] = None):
        ad_config = self.config_service.get_config(domain)
        self.push_screen(
            LoginDialog(user or last_user, ad_config.domain, ad_config),
            lambda result: self._start_connect(domain, result),
        )

    def _start_connect(self, domain: str, credentials) -> None:
        """Connect in a background thread so the UI stays responsive."""
        if not credentials:
            return
        username, password = credentials
        ad_config = self.config_service.get_config(domain)

        if self._find_session(ad_config.domain, username):
            self.notify(
                f"Already connected to {ad_config.domain} as {username}",
                severity="warning",
            )
            return

        self.notify(f"Connecting to {ad_config.domain} as {username}…")

        def connect():
            try:
                manager = create_connection_manager(username, password, ad_config)
                if manager.get_state() != ConnectionState.CONNECTED:
                    reason = manager.first_error or manager.get_last_error()
                    manager.close()
                    raise ConnectionError(reason or "could not connect")
            except Exception as e:
                self.call_from_thread(self._connect_failed, domain, username, str(e))
                return
            session = ADSession(ad_config, username, manager)
            self.call_from_thread(self._connect_succeeded, session)

        self.run_worker(connect, thread=True, group="connect")

    def _connect_succeeded(self, session: ADSession) -> None:
        self._register_session(session)
        self.notify(
            f"Connected to {session.name} as {session.username}",
            severity="information",
        )

    def _connect_failed(self, domain: str, username: str, error: str) -> None:
        self.notify(f"Login to {domain} failed: {error}", severity="error", timeout=8)
        # Let the user retry right away (typo in the password...)
        self._prompt_connect_login(domain, username)

    def action_close_session(self):
        """Disconnect from the AD of the active tree (keeping the others)."""
        if len(self.sessions) <= 1:
            self.notify("Only one AD connected: use :logout or :q", severity="warning")
            return
        session = self.active_session
        name = session.title
        self.remove_session(session)
        self.notify(f"Disconnected from {name}", severity="information")

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

    # Configure file-based logging before anything else so errors and
    # uncaught crashes are persisted (the TUI hides stderr while running).
    try:
        from .services.logging_service import setup_logging
    except ImportError:
        from services.logging_service import setup_logging
    setup_logging()

    from . import __version__

    # Parse command-line arguments before starting Textual
    parser = argparse.ArgumentParser(
        description="ADTUI - Active Directory Terminal User Interface"
    )
    parser.add_argument(
        "--version", "-V", action="version", version=f"adtui {__version__}"
    )
    parser.add_argument(
        "--update",
        "-u",
        action="store_true",
        help="Check for updates and install if available, then exit",
    )
    parser.add_argument(
        "--check-update",
        action="store_true",
        help="Check for updates without installing, then exit",
    )
    parser.add_argument(
        "--no-auto-update",
        action="store_true",
        help="Skip automatic update check and installation at startup",
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
            # Force fresh check, don't use cache for startup auto-update
            result = update_service.check_for_update(force=True)

            if result.update_available:
                print(
                    f"Update available: {result.current_version} -> {result.latest_version}"
                )
                print("Installing update...")

                success, message = update_service.perform_update()
                if success:
                    print(f"Update successful: {message}")
                    print("Restarting ADTUI with new version...\n")

                    # Restart the application with the new version
                    import sys
                    import os

                    # Use --no-auto-update to prevent infinite update loop
                    os.execv(
                        sys.executable,
                        [sys.executable, "-m", "adtui", "--no-auto-update"],
                    )
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
                app = ADTUI(username, password, ad_config, config_service)
                app.run()

                # Check if app exited due to auth failure or logout (should restart login)
                # If app.auth_failed is True, continue loop to show login again
                if getattr(app, "auth_failed", False):
                    # Clear screen before restarting login
                    os.system("cls" if os.name == "nt" else "clear")
                    continue
                else:
                    # Normal exit - break the loop
                    break
            except Exception as e:
                logger.exception("Error running application: %s", e)
                break
        else:
            # No credentials provided, exit
            return


if __name__ == "__main__":
    main()
