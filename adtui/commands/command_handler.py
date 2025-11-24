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
    
    def __init__(self, app: 'App'):
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
            '/': self._handle_search,
            's': self._handle_search,
            
            # Delete commands
            'd': self._handle_delete,
            'del': self._handle_delete,
            'delete': self._handle_delete,
            
            # Move commands
            'm': self._handle_move,
            'mv': self._handle_move,
            'move': self._handle_move,
            
            # OU commands
            'mkou': self._handle_create_ou,
            'createou': self._handle_create_ou,
            
            # Recycle bin commands
            'recycle': self._handle_recycle,
            'rb': self._handle_recycle,
            'restore': self._handle_restore,
            
            # History commands
            'undo': self._handle_undo,
            'u': self._handle_undo,
            
            # Help command
            'help': self._handle_help,
            
            # Quit command
            'q': self._handle_quit,
            'quit': self._handle_quit,
            'exit': self._handle_quit,
        }
    
    def execute(self, command_str: str) -> None:
        """Parse and execute a command.
        
        Args:
            command_str: The command string from user input
        """
        if not command_str:
            return
        
        # Handle search with /
        if command_str.startswith('/'):
            query = command_str[1:].strip()
            if query:
                self._handle_search(query)
            else:
                self.app.notify(MESSAGES['SEARCH_EMPTY'], severity=Severity.WARNING.value)
            return
        
        # Remove colon prefix if present
        if command_str.startswith(':'):
            command_str = command_str[1:]
        
        # Split into command and arguments (preserve spaces in args)
        parts = command_str.split(maxsplit=1)
        if not parts:
            return
        
        command = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ''
        
        # Look up and execute command
        handler = self.commands.get(command)
        if handler:
            handler(args)
        else:
            self.app.notify(f"Unknown command: {command}", severity=Severity.WARNING.value)
    
    def _handle_search(self, query: str) -> None:
        """Handle search command."""
        if not query:
            self.app.notify(MESSAGES['SEARCH_EMPTY'], severity=Severity.WARNING.value)
            return
        
        try:
            results = self.app.ldap_service.search_objects(query)
            self.app.search_results_pane.populate(results, self.app.conn)
            self.app.search_results_pane.styles.display = "block"
        except Exception as e:
            self.app.notify(f"Error searching AD: {e}", severity=Severity.ERROR.value)
    
    def _handle_delete(self, args: str) -> None:
        """Handle delete command."""
        if not self.app.current_selected_dn:
            self.app.notify(MESSAGES['NO_SELECTION'], severity=Severity.WARNING.value)
            return
        
        self.app.pending_delete_dn = self.app.current_selected_dn
        
        from ui.dialogs import ConfirmDeleteDialog
        self.app.push_screen(
            ConfirmDeleteDialog(self.app.current_selected_label, self.app.current_selected_dn),
            self.app.handle_delete_confirmation
        )
    
    def _handle_move(self, target_path: str) -> None:
        """Handle move command."""
        if not self.app.current_selected_dn:
            self.app.notify(MESSAGES['NO_SELECTION'], severity=Severity.WARNING.value)
            return
        
        if not target_path:
            self.app.notify(MESSAGES['TARGET_REQUIRED'], severity=Severity.WARNING.value)
            return
        
        target_dn = self.app.path_service.path_to_dn(target_path)
        
        # Validate target exists
        if not self.app.ldap_service.validate_ou_exists(target_dn):
            self.app.notify(MESSAGES['TARGET_OU_NOT_FOUND'].format(dn=target_dn), severity=Severity.ERROR.value)
            return
        
        self.app.pending_move_dn = self.app.current_selected_dn
        self.app.pending_move_target = target_dn
        
        from ui.dialogs import ConfirmMoveDialog
        self.app.push_screen(
            ConfirmMoveDialog(self.app.current_selected_label, self.app.current_selected_dn, target_dn),
            self.app.handle_move_confirmation
        )
    
    def _handle_create_ou(self, path: str) -> None:
        """Handle OU creation command."""
        if not path:
            self.app.notify(MESSAGES['OU_PATH_REQUIRED'], severity=Severity.WARNING.value)
            return
        
        from ui.dialogs import CreateOUDialog
        self.app.push_screen(
            CreateOUDialog(path),
            self.app.handle_create_ou_confirmation
        )
    
    def _handle_recycle(self, args: str) -> None:
        """Handle recycle bin view command."""
        try:
            results = self.app.ldap_service.get_deleted_objects()
            self.app.search_results_pane.populate(results)
            self.app.notify(f"Found {len(results)} deleted objects. Use :restore <name> to restore.", 
                           severity=Severity.INFORMATION.value)
        except Exception as e:
            self.app.notify(str(e), severity=Severity.ERROR.value)
    
    def _handle_restore(self, cn: str) -> None:
        """Handle restore command."""
        if not cn:
            self.app.notify(MESSAGES['RESTORE_NAME_REQUIRED'], severity=Severity.WARNING.value)
            return
        
        try:
            result = self.app.ldap_service.search_deleted_object(cn)
            
            if result is None:
                self.app.notify(MESSAGES['NO_MATCH'].format(query=cn), severity=Severity.WARNING.value)
            elif 'error' in result and result['error'] == 'multiple':
                self.app.notify(MESSAGES['MULTIPLE_MATCHES'].format(query=cn), severity=Severity.WARNING.value)
            else:
                from ui.dialogs import ConfirmRestoreDialog
                self.app.push_screen(
                    ConfirmRestoreDialog(cn, result['dn']),
                    lambda confirmed: self.app.restore_object(result['dn']) if confirmed else None
                )
        except Exception as e:
            self.app.notify(str(e), severity=Severity.ERROR.value)
    
    def _handle_undo(self, args: str) -> None:
        """Handle undo command."""
        if not self.app.history_service.can_undo():
            self.app.notify(MESSAGES['NO_UNDO_HISTORY'], severity=Severity.INFORMATION.value)
            return
        
        last_op = self.app.history_service.get_last()
        
        if last_op.type == 'delete':
            self.app.notify(MESSAGES['UNDO_DELETE_WARNING'], severity=Severity.WARNING.value)
        elif last_op.type == 'create_ou':
            from ui.dialogs import ConfirmUndoDialog
            self.app.push_screen(
                ConfirmUndoDialog(f"Delete OU: {last_op.details['name']}"),
                lambda confirmed: self.app.undo_create_ou(last_op) if confirmed else None
            )
        elif last_op.type == 'move':
            from ui.dialogs import ConfirmUndoDialog
            self.app.push_screen(
                ConfirmUndoDialog(f"Move back: {last_op.details['object']}"),
                lambda confirmed: self.app.undo_move(last_op) if confirmed else None
            )
        else:
            self.app.notify(f"Cannot undo operation type: {last_op.type}", severity=Severity.WARNING.value)
    
    def _handle_help(self, args: str) -> None:
        """Handle help command."""
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
:q, :quit, :exit - Quit application

[bold]Keyboard Shortcuts:[/bold]
/                - Open search (vim-style)
:                - Enter command mode
r                - Refresh current OU
Esc              - Cancel command mode

[bold cyan]Move with Autocomplete:[/bold cyan]
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
