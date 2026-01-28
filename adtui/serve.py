"""Web-friendly entry point for textual serve.

Usage:
    textual serve --url "http://localhost:8000" "python -m adtui.serve"

For external access:
    textual serve --host 0.0.0.0 --port 8000 --url "http://YOUR_IP:8000" "python -m adtui.serve"
"""

import logging

from .adtui import ADTUI, create_connection_manager
from .services.config_service import ConfigService

logger = logging.getLogger(__name__)


class ADTUIServeApp(ADTUI):
    """Web-friendly ADTUI that handles login within the TUI.

    This app is designed to be used with `textual serve` for browser-based access.
    Each web client gets their own instance with their own LDAP session.

    Inherits from ADTUI to get all keybindings and functionality.
    """

    def compose(self):
        """Show splash screen instead of full UI - UI is built after login."""
        from textual.widgets import Static, Footer
        from . import __version__

        ascii_art = f"""[bold palegreen]   db    888b.    88888 8    8 888 [/bold palegreen]
[bold palegreen]  dPYb   8   8      8   8    8  8  [/bold palegreen]
[bold palegreen] dPwwYb  8   8      8   8b..d8  8  [/bold palegreen]
[bold palegreen]dP    Yb 888P'      8   `Y88P' 888 [/bold palegreen]
                            [dim]v{__version__}[/dim]"""

        yield Static(
            f"{ascii_art}\n\n[bold cyan]Active Directory TUI[/bold cyan]\n\n[dim]Initializing...[/dim]",
            id="splash"
        )
        yield Footer()

    def __init__(self):
        """Initialize without credentials - login happens via dialog."""
        # Load config first to get ad_config for base_dn
        self.config_service = None
        self.selected_domain = None
        self._config_error = None

        try:
            self.config_service = ConfigService()
            is_valid, issues = self.config_service.validate_config()
            if not is_valid:
                self._config_error = "Configuration errors:\n" + "\n".join(f"- {i}" for i in issues)
        except FileNotFoundError:
            self._config_error = (
                "No configuration file found.\n\n"
                "Please create config.ini in:\n"
                "- /home/adtui/config.ini (Docker)\n"
                "- ~/.config/adtui/config.ini (Linux)\n"
                "- Current directory"
            )
        except Exception as e:
            self._config_error = f"Error loading configuration:\n{e}"

        # Get default domain's config for initialization
        ad_config = None
        if self.config_service and not self._config_error:
            self.selected_domain = self.config_service.get_default_domain()
            ad_config = self.config_service.get_config(self.selected_domain)

        # Initialize parent without credentials (creates placeholder widgets)
        super().__init__(username=None, password=None, ad_config=ad_config)

        # Flag to track if we've completed login
        self._logged_in = False

    def on_mount(self) -> None:
        """Show login dialog instead of normal mount behavior."""
        if self._config_error:
            self.notify(self._config_error, severity="error", timeout=30)
            return

        # Show domain selection if multiple domains, otherwise show login
        if self.config_service.has_multiple_domains():
            from .ui.dialogs import ADSelectionDialog
            self.push_screen(
                ADSelectionDialog(self.config_service.ad_configs),
                self._handle_ad_selection
            )
        else:
            self._show_login()

    def _handle_ad_selection(self, domain) -> None:
        """Handle AD domain selection."""
        if domain:
            self.selected_domain = domain
            # Update ad_config for the selected domain
            self.ad_config = self.config_service.get_config(self.selected_domain)
            self.base_dn = self.ad_config.base_dn
            self._show_login()
        else:
            # User cancelled, show selection again
            from .ui.dialogs import ADSelectionDialog
            self.push_screen(
                ADSelectionDialog(self.config_service.ad_configs),
                self._handle_ad_selection
            )

    def _show_login(self) -> None:
        """Show login dialog."""
        from .ui.dialogs import LoginDialog

        ad_config = self.config_service.get_config(self.selected_domain)

        # No last_user for web version - each session starts fresh
        self.push_screen(
            LoginDialog("", ad_config.domain, ad_config),
            self._handle_login
        )

    def _handle_login(self, result) -> None:
        """Handle login result and initialize connection."""
        if not result:
            # User cancelled, show login again
            self._show_login()
            return

        username, password = result
        ad_config = self.config_service.get_config(self.selected_domain)

        try:
            # Create connection manager with credentials
            self.connection_manager = create_connection_manager(
                username, password, ad_config
            )

            # Set auth failure callback
            self.connection_manager.set_auth_failure_callback(
                self._on_authentication_failure
            )

            # Initialize all services (this also creates the real widgets)
            self._initialize_services()

            # Mark as logged in
            self._logged_in = True

            # Rebuild the UI with the real widgets
            self._rebuild_ui()

            self.notify("Connected successfully!", severity="information", timeout=3)

        except Exception as e:
            logger.exception("Login failed")
            self.notify(f"Login failed: {e}", severity="error", timeout=5)
            self._show_login()

    def _rebuild_ui(self) -> None:
        """Rebuild the UI after successful login."""
        from textual.containers import Horizontal, Vertical
        from textual.widgets import Input, Footer

        # Remove splash screen specifically
        try:
            splash = self.query_one("#splash")
            splash.remove()
        except Exception:
            pass

        # Remove any existing footer
        try:
            for footer in self.query("Footer"):
                footer.remove()
        except Exception:
            pass

        # Check if command-input already exists (shouldn't, but just in case)
        try:
            existing_input = self.query_one("#command-input")
            existing_input.remove()
        except Exception:
            pass

        # Mount the real ADTUI layout
        horizontal = Horizontal()
        self.mount(horizontal)

        left_vertical = Vertical()
        right_vertical = Vertical()
        horizontal.mount(left_vertical)
        horizontal.mount(right_vertical)

        left_vertical.mount(self.adtree)
        right_vertical.mount(self.details)
        right_vertical.mount(self.search_results_pane)

        cmd_input = Input(placeholder=": command/search", id="command-input")
        cmd_input.visible = False
        self.mount(cmd_input)

        self.mount(Footer())

        # Expand tree to show root level
        self.set_timer(0.5, self._expand_tree_on_startup)
        self.set_timer(2.0, self._delayed_tree_rebuild)

        # Update footer
        self._update_footer()

    def _on_authentication_failure(self) -> None:
        """Handle authentication failure - show login again."""
        self.notify("Authentication failed. Please log in again.", severity="error")
        self._logged_in = False
        self._show_login()

    def action_logout(self):
        """Disconnect and return to login screen for domain switching."""
        # Close current connection
        if self.connection_manager:
            try:
                self.connection_manager.close()
            except Exception:
                pass
            self.connection_manager = None

        self._logged_in = False

        # Clear the UI and show login again
        self._clear_ui()

        # Show domain selection or login
        if self.config_service.has_multiple_domains():
            from .ui.dialogs import ADSelectionDialog
            self.push_screen(
                ADSelectionDialog(self.config_service.ad_configs),
                self._handle_ad_selection
            )
        else:
            self._show_login()

    def _clear_ui(self) -> None:
        """Clear all UI widgets to prepare for new login."""
        from textual.widgets import Static, Footer

        # Remove all widgets except footer
        for widget in list(self.query("*")):
            try:
                widget.remove()
            except Exception:
                pass

        # Show splash screen again
        from . import __version__

        ascii_art = f"""[bold palegreen]   db    888b.    88888 8    8 888 [/bold palegreen]
[bold palegreen]  dPYb   8   8      8   8    8  8  [/bold palegreen]
[bold palegreen] dPwwYb  8   8      8   8b..d8  8  [/bold palegreen]
[bold palegreen]dP    Yb 888P'      8   `Y88P' 888 [/bold palegreen]
                            [dim]v{__version__}[/dim]"""

        self.mount(Static(
            f"{ascii_art}\n\n[bold cyan]Active Directory TUI[/bold cyan]\n\n[dim]Disconnected...[/dim]",
            id="splash"
        ))
        self.mount(Footer())


# Export class for direct import
app = ADTUIServeApp


def main():
    """Entry point for python -m adtui.serve"""
    app_instance = ADTUIServeApp()
    app_instance.run()


if __name__ == "__main__":
    main()
