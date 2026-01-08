"""Command handler for parsing and executing commands."""

from typing import TYPE_CHECKING, Callable, Dict, Optional
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from constants import MESSAGES, Severity

if TYPE_CHECKING:
    from textual.app import App


class CommandHandler:
    """Handles command parsing and execution."""

    def __init__(self, app: "App"):
        """Initialize command handler.

        Args:
            app: The main application instance
        """
        self.app = app
        self.commands = self._build_command_registry()

    def _build_command_registry(self) -> Dict[str, Callable]:
        """Build the command registry mapping command names to handlers."""
        return {
            # Search commands
            "/": self._handle_search,
            "s": self._handle_search,
            # Delete commands
            "d": self._handle_delete,
            "del": self._handle_delete,
            "delete": self._handle_delete,
            # Move commands
            "m": self._handle_move,
            "mv": self._handle_move,
            "move": self._handle_move,
            # OU commands
            "mkou": self._handle_create_ou,
            "createou": self._handle_create_ou,
            # Recycle bin commands
            "recycle": self._handle_recycle,
            "rb": self._handle_recycle,
            "restore": self._handle_restore,
            # History commands
            # User management commands
            "unlock": self._handle_unlock,
            "enable": self._handle_enable,
            "en": self._handle_enable,
            "disable": self._handle_disable,
            "dis": self._handle_disable,
            #  commands
            "-tree": self._handle__tree,
            "createuser": self._handle_create_user,
            "cu": self._handle_create_user,
            "copyuser": self._handle_copy_user,
            "undo": self._handle_undo,
            "u": self._handle_undo,
            # Help command
            "help": self._handle_help,
            # Quit command
            "q": self._handle_quit,
            "quit": self._handle_quit,
            "exit": self._handle_quit,
        }

    def execute(self, command_str: str) -> None:
        """Parse and execute a command.

        Args:
            command_str: The command string from user input
        """
        if not command_str:
            return

        # Handle search with /
        if command_str.startswith("/"):
            query = command_str[1:].strip()
            if query:
                self._handle_search(query)
            else:
                self.app.notify(
                    MESSAGES["SEARCH_EMPTY"], severity=Severity.WARNING.value
                )
            return

        # Remove colon prefix if present
        if command_str.startswith(":"):
            command_str = command_str[1:]

        # Split into command and arguments (preserve spaces in args)
        parts = command_str.split(maxsplit=1)
        if not parts:
            return

        command = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        # Look up and execute command
        handler = self.commands.get(command)
        if handler:
            handler(args)
        else:
            self.app.notify(
                f"Unknown command: {command}", severity=Severity.WARNING.value
            )

    def _handle_search(self, query: str) -> None:
        """Handle search command."""
        if not query:
            self.app.notify(MESSAGES["SEARCH_EMPTY"], severity=Severity.WARNING.value)
            return

        try:
            results = self.app.ldap_service.search_objects(query)
            self.app.search_results_pane.populate(results, self.app.connection_manager)
            self.app.search_results_pane.styles.display = "block"
            # Focus the search results
            self.app.search_results_pane.focus()
        except Exception as e:
            self.app.notify(f"Error searching AD: {e}", severity=Severity.ERROR.value)

    def _handle_delete(self, args: str) -> None:
        """Handle delete command."""
        if not self.app.current_selected_dn:
            self.app.notify(MESSAGES["NO_SELECTION"], severity=Severity.WARNING.value)
            return

        self.app.pending_delete_dn = self.app.current_selected_dn

        from ui.dialogs import ConfirmDeleteDialog

        self.app.push_screen(
            ConfirmDeleteDialog(
                self.app.current_selected_label, self.app.current_selected_dn
            ),
            self.app.handle_delete_confirmation,
        )

    def _handle_move(self, target_path: str) -> None:
        """Handle move command."""
        if not self.app.current_selected_dn:
            self.app.notify(MESSAGES["NO_SELECTION"], severity=Severity.WARNING.value)
            return

        if not target_path:
            self.app.notify(
                MESSAGES["TARGET_REQUIRED"], severity=Severity.WARNING.value
            )
            return

        target_dn = self.app.path_service.path_to_dn(target_path)

        # Validate target exists
        if not self.app.ldap_service.validate_ou_exists(target_dn):
            self.app.notify(
                MESSAGES["TARGET_OU_NOT_FOUND"].format(dn=target_dn),
                severity=Severity.ERROR.value,
            )
            return

        self.app.pending_move_dn = self.app.current_selected_dn
        self.app.pending_move_target = target_dn

        from ui.dialogs import ConfirmMoveDialog

        self.app.push_screen(
            ConfirmMoveDialog(
                self.app.current_selected_label, self.app.current_selected_dn, target_dn
            ),
            self.app.handle_move_confirmation,
        )

    def _handle_create_ou(self, ou_name: str) -> None:
        """Handle OU creation command."""
        # If no OU name provided, use current selection as parent and prompt for name
        if not ou_name:
            if not self.app.current_selected_dn:
                self.app.notify(
                    "No OU selected. Please select an OU first.",
                    severity=Severity.WARNING.value,
                )
                return

            from ui.dialogs import CreateOUDialog

            self.app.push_screen(
                CreateOUDialog(parent_dn=self.app.current_selected_dn),
                self.app.handle_create_ou_confirmation,
            )
        else:
            # OU name provided, use current selection as parent
            if not self.app.current_selected_dn:
                self.app.notify(
                    "No OU selected. Please select an OU first.",
                    severity=Severity.WARNING.value,
                )
                return

            # Create OU directly with provided name
            self.app.create_ou_in_parent(ou_name, self.app.current_selected_dn)

    def _handle_recycle(self, args: str) -> None:
        """Handle recycle bin view command."""
        try:
            results = self.app.ldap_service.get_deleted_objects()
            self.app.search_results_pane.populate(results, self.app.connection_manager)
            self.app.notify(
                f"Found {len(results)} deleted objects. Use :restore <name> to restore.",
                severity=Severity.INFORMATION.value,
            )
        except Exception as e:
            self.app.notify(str(e), severity=Severity.ERROR.value)

    def _handle_restore(self, cn: str) -> None:
        """Handle restore command."""
        if not cn:
            self.app.notify(
                MESSAGES["RESTORE_NAME_REQUIRED"], severity=Severity.WARNING.value
            )
            return

        try:
            result = self.app.ldap_service.search_deleted_object(cn)

            if result is None:
                self.app.notify(
                    MESSAGES["NO_MATCH"].format(query=cn),
                    severity=Severity.WARNING.value,
                )
            elif "error" in result and result["error"] == "multiple":
                self.app.notify(
                    MESSAGES["MULTIPLE_MATCHES"].format(query=cn),
                    severity=Severity.WARNING.value,
                )
        except Exception as e:
            self.app.notify(
                f"Error restoring object: {e}", severity=Severity.ERROR.value
            )

    def _is_user_object(self, dn: str) -> bool:
        """Check if DN represents a user object."""
        try:
            self.app.ldap_service.conn.search(
                dn, "(objectClass=*)", search_scope="BASE", attributes=["objectClass"]
            )
            if self.app.ldap_service.conn.entries:
                obj_classes = [
                    str(cls).lower()
                    for cls in self.app.ldap_service.conn.entries[0].objectClass
                ]
                return "user" in obj_classes and "computer" not in obj_classes
            return False
        except:
            return False

    def _handle_create_user(self, args: str) -> None:
        """Handle create user command."""
        from ui.dialogs import CreateUserDialog

        # Determine target OU
        if args.strip():
            # Use specified OU path
            target_ou = self.app.path_service.resolve_path(args.strip())
        else:
            # Use current selected OU
            target_ou = self._get_current_ou()

        if not target_ou:
            self.app.notify(
                "No target OU specified or selected", severity=Severity.WARNING.value
            )
            return

        self.app.push_screen(
            CreateUserDialog(target_ou, self.app.ldap_service),
            self.app.handle_create_user_confirmation,
        )

    def _handle_copy_user(self, args: str) -> None:
        """Handle copy user command."""
        from ui.dialogs import CopyUserDialog

        # Parse arguments: [source_dn] [target_ou]
        parts = args.strip().split(maxsplit=1)

        if len(parts) == 0:
            # Use current selected user
            if not self.app.current_selected_dn:
                self.app.notify(
                    "No user selected to copy", severity=Severity.WARNING.value
                )
                return
            if not self._is_user_object(self.app.current_selected_dn):
                self.app.notify(
                    "Selected object is not a user", severity=Severity.WARNING.value
                )
                return

            source_dn = self.app.current_selected_dn
            source_label = self.app.current_selected_label
            target_ou = self._get_current_ou()
        elif len(parts) == 1:
            # Source DN specified, use current OU as target
            source_dn = parts[0]
            source_label = (
                source_dn.split(",")[0].split("=")[1] if "=" in source_dn else source_dn
            )
            target_ou = self._get_current_ou()
        else:
            # Both source and target specified
            source_dn = parts[0]
            source_label = (
                source_dn.split(",")[0].split("=")[1] if "=" in source_dn else source_dn
            )
            target_ou = self.app.path_service.resolve_path(parts[1])

        if not target_ou:
            self.app.notify("Invalid target OU", severity=Severity.WARNING.value)
            return

        self.app.push_screen(
            CopyUserDialog(source_dn, source_label, target_ou, self.app.ldap_service),
            self.app.handle_copy_user_confirmation,
        )

    def _get_current_ou(self) -> str:
        """Get the currently selected OU DN."""
        if self.app.current_selected_dn:
            # Check if current selection is an OU
            if self.app.current_selected_label and "📁" in str(
                self.app.current_selected_label
            ):
                return self.app.current_selected_dn
            else:
                # Get parent OU of selected object
                dn_parts = self.app.current_selected_dn.split(",")
                if len(dn_parts) > 1:
                    return ",".join(dn_parts[1:])

        # Fallback to base DN
        return (
            self.app.ldap_service.base_dn if self.app.ldap_service else self.app.base_dn
        )

    def _handle_unlock(self, args: str) -> None:
        """Handle unlock command."""
        if not self.app.current_selected_dn:
            self.app.notify(MESSAGES["NO_SELECTION"], severity=Severity.WARNING.value)
            return

        # Check if selected object is a user
        if not self._is_user_object(self.app.current_selected_dn):
            self.app.notify(
                "Unlock can only be performed on user accounts",
                severity=Severity.WARNING.value,
            )
            return

        from ui.dialogs import ConfirmUnlockDialog

        self.app.push_screen(
            ConfirmUnlockDialog(
                self.app.current_selected_label, self.app.current_selected_dn
            ),
            self.app.handle_unlock_confirmation,
        )

    def _handle_enable(self, args: str) -> None:
        """Handle enable command."""
        if not self.app.current_selected_dn:
            self.app.notify(MESSAGES["NO_SELECTION"], severity=Severity.WARNING.value)
            return

        # Check if selected object is a user
        if not self._is_user_object(self.app.current_selected_dn):
            self.app.notify(
                "Enable can only be performed on user accounts",
                severity=Severity.WARNING.value,
            )
            return

        from ui.dialogs import ConfirmEnableDialog

        self.app.push_screen(
            ConfirmEnableDialog(
                self.app.current_selected_label, self.app.current_selected_dn
            ),
            self.app.handle_enable_confirmation,
        )

    def _handle__tree(self, args: str) -> None:
        """Handle  tree command - rebuild tree."""
        try:
            self.app.notify("Rebuilding AD tree...", severity="information")

            if (
                hasattr(self.app, "adtree")
                and self.app.adtree
                and self.app.adtree.connection_manager
            ):
                self.app.adtree.build_tree()
                self.app.notify("Tree rebuilt successfully", severity="information")
            else:
                self.app.notify("ADTree not available", severity="error")
        except Exception as e:
            self.app.notify(f"Error rebuilding tree: {e}", severity="error")
            import traceback

            traceback.print_exc()

    def _handle_disable(self, args: str) -> None:
        """Handle disable command."""
        if not self.app.current_selected_dn:
            self.app.notify(MESSAGES["NO_SELECTION"], severity=Severity.WARNING.value)
            return

        # Check if selected object is a user
        if not self._is_user_object(self.app.current_selected_dn):
            self.app.notify(
                "Disable can only be performed on user accounts",
                severity=Severity.WARNING.value,
            )
            return

        from ui.dialogs import ConfirmDisableDialog

        self.app.push_screen(
            ConfirmDisableDialog(
                self.app.current_selected_label, self.app.current_selected_dn
            ),
            self.app.handle_disable_confirmation,
        )

    def _handle_undo(self, args: str) -> None:
        """Handle undo command."""
        if not self.app.history_service.can_undo():
            self.app.notify(
                MESSAGES["NO_UNDO_HISTORY"], severity=Severity.INFORMATION.value
            )
            return

        last_op = self.app.history_service.get_last()

        if last_op.type == "delete":
            self.app.notify(
                MESSAGES["UNDO_DELETE_WARNING"], severity=Severity.WARNING.value
            )
        elif last_op.type == "create_ou":
            from ui.dialogs import ConfirmUndoDialog

            self.app.push_screen(
                ConfirmUndoDialog(f"Delete OU: {last_op.details['name']}"),
                lambda confirmed: self.app.undo_create_ou(last_op)
                if confirmed
                else None,
            )
        elif last_op.type == "move":
            from ui.dialogs import ConfirmUndoDialog

            self.app.push_screen(
                ConfirmUndoDialog(f"Move back: {last_op.details['object']}"),
                lambda confirmed: self.app.undo_move(last_op) if confirmed else None,
            )
        elif last_op.type == "create_user":
            from ui.dialogs import BaseConfirmDialog

            self.app.push_screen(
                BaseConfirmDialog(
                    title="[bold red]⚠ Undo Create User[/bold red]",
                    message=f"Are you sure you want to undo creating this user?\n\n{last_op.details['full_name']} ({last_op.details['samaccount']})\n\n[yellow]This will permanently delete of user account.[/yellow]",
                    confirm_text="Delete",
                    confirm_variant="error",
                ),
                lambda confirmed: self.app.undo_create_user(last_op)
                if confirmed
                else None,
            )
        elif last_op.type == "copy_user":
            from ui.dialogs import BaseConfirmDialog

            self.app.push_screen(
                BaseConfirmDialog(
                    title="[bold red]⚠ Undo Copy User[/bold red]",
                    message=f"Are you sure you want to undo copying this user?\n\n{last_op.details['full_name']} ({last_op.details['samaccount']})\n\n[yellow]This will permanently delete of copied user account.[/yellow]",
                    confirm_text="Delete",
                    confirm_variant="error",
                ),
                lambda confirmed: self.app.undo_copy_user(last_op)
                if confirmed
                else None,
            )
        else:
            self.app.notify(
                f"Cannot undo operation type: {last_op.type}",
                severity=Severity.WARNING.value,
            )

    def _handle_help(self, args: str) -> None:
        """Handle help command."""
        help_text = """[bold cyan]Available Commands:[/bold cyan]

[bold]Search & Navigation:[/bold]
/<query>         - Search (vim-style)
:s <query>       - Search for objects by cn or sAMAccountName

[bold]Object Management:[/bold]
/del         - Delete currently selected object
:m <path>        - Move to path with autocomplete
:move <path>     - Same as :m
:unlock          - Unlock currently selected locked user account
:enable          - Enable currently selected disabled user account
:en              - Same as :enable
:disable         - Disable currently selected enabled user account
:dis             - Same as :disable
:createuser [ou] - Create new user account (uses current OU if not specified)
:cu [ou]         - Same as :createuser
:copyuser [source] [ou] - Copy user account (uses current selection if not specified)

[bold]OU Management:[/bold]
:mkou <name>     - Create new OU with name in current location
:createou <name> - Same as :mkou

[bold]Recovery & History:[/bold]
:recycle, :rb    - Show AD Recycle Bin contents
:restore <name>  - Restore deleted object
:undo, :u        - Undo last operation

[bold]Other:[/bold]
:help            - Show this help message
:q, :quit, :exit - Quit application

[bold]Move with Autocomplete:[/bold]
Type :m and start typing a path:
  :m User[autocomplete shows suggestions]
  :m Users/[shows subdirectories]

Full LDAP DN also works:
  :m ou=IT,ou=Users,dc=example,dc=com
"""
        self.app.notify(help_text, timeout=15)

    def _handle_quit(self, args: str) -> None:
        """Handle quit command."""
        self.app.exit()
