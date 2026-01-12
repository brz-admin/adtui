"""Modal dialogs for ADTUI."""

import logging
from typing import Dict, Optional, Tuple, List, Any

from ldap3 import Connection

from textual.screen import ModalScreen
from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal, ScrollableContainer
from textual.widgets import (
    Static,
    Button,
    Input,
    ListView,
    ListItem,
    Label,
    Checkbox,
    TextArea,
)

logger = logging.getLogger(__name__)


class BaseConfirmDialog(ModalScreen[bool]):
    """Base class for confirmation dialogs."""

    def __init__(
        self,
        title: str,
        message: str,
        confirm_text: str,
        confirm_variant: str = "primary",
    ):
        super().__init__()
        self.title = title
        self.message = message
        self.confirm_text = confirm_text
        self.confirm_variant = confirm_variant

    def compose(self) -> ComposeResult:
        yield Vertical(
            Static(f"{self.title}\n\n{self.message}", id="question"),
            Horizontal(
                Button(self.confirm_text, variant=self.confirm_variant, id="confirm"),
                Button("Cancel", variant="primary", id="cancel"),
                id="dialog-buttons",
            ),
            id="dialog",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "confirm")


class ConfirmDeleteDialog(BaseConfirmDialog):
    """Dialog to confirm object deletion."""

    def __init__(self, label: str, dn: str):
        super().__init__(
            title="[bold red]Confirm Deletion[/bold red]",
            message=f"Are you sure you want to delete:\n\n{label}\n\nDN: {dn}\n\nThis action cannot be undone!",
            confirm_text="Delete",
            confirm_variant="error",
        )


class ConfirmMoveDialog(BaseConfirmDialog):
    """Dialog to confirm object move."""

    def __init__(self, label: str, from_dn: str, to_dn: str):
        super().__init__(
            title="[bold yellow]Confirm Move[/bold yellow]",
            message=f"Move object:\n{label}\n\nFrom: {from_dn}\n\nTo: {to_dn}\n\nConfirm?",
            confirm_text="Move",
            confirm_variant="success",
        )


class ConfirmRestoreDialog(BaseConfirmDialog):
    """Dialog to confirm object restoration."""

    def __init__(self, name: str, dn: str):
        super().__init__(
            title="[bold cyan]Restore Deleted Object[/bold cyan]",
            message=f"Restore: {name}\n\nDN: {dn}\n\nConfirm?",
            confirm_text="Restore",
            confirm_variant="success",
        )


class ConfirmUndoDialog(BaseConfirmDialog):
    """Dialog to confirm undo operation."""

    def __init__(self, message: str):
        super().__init__(
            title="[bold yellow]Undo Last Operation[/bold yellow]",
            message=f"{message}\n\nConfirm?",
            confirm_text="Undo",
            confirm_variant="warning",
        )


class CreateOUDialog(ModalScreen):
    """Dialog to create a new OU."""

    def __init__(self, parent_dn: str = None, path: str = None):
        super().__init__()
        self.parent_dn = parent_dn
        self.path = path  # Keep for backward compatibility

    def compose(self) -> ComposeResult:
        if self.parent_dn:
            # New mode: creating OU in parent
            parent_path = self._dn_to_path(self.parent_dn)
            question_text = (
                f"[bold green]Create New OU[/bold green]\n\nLocation: {parent_path}\n"
            )
        else:
            # Legacy mode: creating at specific path
            question_text = (
                f"[bold green]Create New OU[/bold green]\n\nPath: {self.path}\n"
            )

        yield Vertical(
            Static(question_text, id="question"),
            Input(placeholder="OU Name", id="ou-name"),
            Input(placeholder="Description (optional)", id="ou-description"),
            Horizontal(
                Button("Create", variant="success", id="create"),
                Button("Cancel", variant="primary", id="cancel"),
                id="dialog-buttons",
            ),
            id="dialog",
        )

    def _dn_to_path(self, dn: str) -> str:
        """Convert DN to human-readable path."""
        parts = dn.split(",")
        ou_parts = []

        for part in parts:
            part = part.strip()
            if part.lower().startswith("ou="):
                ou_parts.append(part[3:])

        ou_parts.reverse()
        return "/" + "/".join(ou_parts) if ou_parts else "/"

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "create":
            name_input = self.query_one("#ou-name", Input)
            description_input = self.query_one("#ou-description", Input)

            if self.parent_dn:
                # New mode: return (ou_name, parent_dn, description)
                self.dismiss(
                    (name_input.value, self.parent_dn, description_input.value)
                )
            else:
                # Legacy mode: return (path, description)
                self.dismiss((self.path, description_input.value))
        else:
            self.dismiss(None)


class EditUserDialog(ModalScreen):
    """Dialog to edit user attributes."""

    def __init__(self, dn: str, connection_manager, user_details, base_dn: str):
        super().__init__()
        self.dn = dn
        self.connection_manager = connection_manager
        self.user_details = user_details
        self.base_dn = base_dn

    def compose(self) -> ComposeResult:
        cn = (
            str(self.user_details.entry.cn.value)
            if self.user_details and hasattr(self.user_details.entry, "cn")
            else "User"
        )
        entry = self.user_details.entry

        yield Vertical(
            Static(f"[bold cyan]Edit User: {cn}[/bold cyan]\n", id="question"),
            ScrollableContainer(
                Input(
                    placeholder="Display Name",
                    id="displayName",
                    value=str(entry.displayName.value)
                    if hasattr(entry, "displayName")
                    else "",
                ),
                Input(
                    placeholder="Given Name (First Name)",
                    id="givenName",
                    value=str(entry.givenName.value)
                    if hasattr(entry, "givenName")
                    else "",
                ),
                Input(
                    placeholder="Surname (Last Name)",
                    id="sn",
                    value=str(entry.sn.value) if hasattr(entry, "sn") else "",
                ),
                Input(
                    placeholder="Email",
                    id="mail",
                    value=str(entry.mail.value) if hasattr(entry, "mail") else "",
                ),
                Input(
                    placeholder="Telephone",
                    id="telephoneNumber",
                    value=str(entry.telephoneNumber.value)
                    if hasattr(entry, "telephoneNumber")
                    else "",
                ),
                Input(
                    placeholder="Mobile",
                    id="mobile",
                    value=str(entry.mobile.value) if hasattr(entry, "mobile") else "",
                ),
                Input(
                    placeholder="Office",
                    id="physicalDeliveryOfficeName",
                    value=str(entry.physicalDeliveryOfficeName.value)
                    if hasattr(entry, "physicalDeliveryOfficeName")
                    else "",
                ),
                Input(
                    placeholder="Department",
                    id="department",
                    value=str(entry.department.value)
                    if hasattr(entry, "department")
                    else "",
                ),
                Input(
                    placeholder="Title",
                    id="title",
                    value=str(entry.title.value) if hasattr(entry, "title") else "",
                ),
                Input(
                    placeholder="Description",
                    id="description",
                    value=str(entry.description.value)
                    if hasattr(entry, "description")
                    else "",
                ),
                Input(
                    placeholder="Profile Path",
                    id="profilePath",
                    value=str(entry.profilePath.value)
                    if hasattr(entry, "profilePath")
                    else "",
                ),
                Input(
                    placeholder="Home Directory",
                    id="homeDirectory",
                    value=str(entry.homeDirectory.value)
                    if hasattr(entry, "homeDirectory")
                    else "",
                ),
            ),
            Horizontal(
                Button("Save", variant="success", id="save"),
                Button("Cancel", variant="primary", id="cancel"),
                id="dialog-buttons",
            ),
            id="dialog",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save":
            try:
                from ldap3 import MODIFY_REPLACE, MODIFY_DELETE

                # Required fields that cannot be empty
                required_fields = ["displayName", "givenName", "sn"]
                # Optional fields that can be empty (will be deleted if empty)
                optional_fields = [
                    "mail",
                    "telephoneNumber",
                    "mobile",
                    "physicalDeliveryOfficeName",
                    "department",
                    "title",
                    "description",
                    "profilePath",
                    "homeDirectory",
                ]

                def update_user_op(conn: Connection):
                    # Process required fields
                    for field in required_fields:
                        value = self.query_one(f"#{field}", Input).value.strip()
                        if value:  # Only update if not empty
                            conn.modify(self.dn, {field: [(MODIFY_REPLACE, [value])]})

                    # Process optional fields
                    for field in optional_fields:
                        value = self.query_one(f"#{field}", Input).value.strip()
                        if value:  # Update with new value if not empty
                            conn.modify(self.dn, {field: [(MODIFY_REPLACE, [value])]})
                        else:  # Delete the attribute if empty
                            # Check if the attribute currently exists before trying to delete
                            entry = self.user_details.entry
                            if hasattr(entry, field):
                                try:
                                    conn.modify(self.dn, {field: [(MODIFY_DELETE, [])]})
                                except Exception as e:
                                    # Attribute might not exist or cannot be deleted, continue
                                    pass

                if self.connection_manager:
                    self.connection_manager.execute_with_retry(update_user_op)

                self.app.notify("User updated successfully", severity="information")
                self.dismiss(True)
            except Exception as e:
                self.app.notify(f"Error updating user: {e}", severity="error")
        else:
            self.dismiss(False)


class ManageGroupsDialog(ModalScreen):
    """Dialog to manage user's group memberships."""

    BINDINGS = [
        ("escape", "dismiss_dialog", "Close"),
        ("delete", "remove_group", "Remove"),
        ("a", "add_group", "Add Group"),
    ]

    def __init__(self, dn: str, connection_manager, user_details, base_dn: str):
        super().__init__()
        self.dn = dn
        self.connection_manager = connection_manager
        self.user_details = user_details
        self.base_dn = base_dn
        self.groups_data = {}

    def compose(self) -> ComposeResult:
        cn = (
            str(self.user_details.entry.cn.value)
            if self.user_details and hasattr(self.user_details.entry, "cn")
            else "User"
        )

        yield Vertical(
            Static(
                f"[bold cyan]Group Memberships: {cn}[/bold cyan]\n\nMember of {len(self.user_details.member_of) if self.user_details else 0} groups\n[dim]Delete: Remove | A: Add | Esc: Close[/dim]\n",
                id="question",
            ),
            Input(placeholder="Search groups to add...", id="group-search"),
            ListView(id="groups-list"),
            Horizontal(
                Button("Add Group", variant="success", id="add"),
                Button("Remove", variant="error", id="remove"),
                Button("Close", variant="primary", id="close"),
                id="dialog-buttons",
            ),
            id="dialog",
        )

    def on_mount(self) -> None:
        """Populate the groups list after mounting."""
        groups_list = self.query_one("#groups-list", ListView)
        if self.user_details and self.user_details.member_of:
            for group in self.user_details.member_of:
                item = ListItem(Label(group["name"]))
                self.groups_data[id(item)] = group
                groups_list.append(item)
        groups_list.focus()

    def action_dismiss_dialog(self) -> None:
        self.dismiss()

    def _refresh_groups_list(self) -> None:
        """Refresh the groups list from current user_details."""
        groups_list = self.query_one("#groups-list", ListView)
        groups_list.clear()
        self.groups_data.clear()

        if self.user_details and self.user_details.member_of:
            for group in self.user_details.member_of:
                item = ListItem(Label(group["name"]))
                self.groups_data[id(item)] = group
                groups_list.append(item)

        # Update the header with current count
        header = self.query_one("#question", Static)
        cn = (
            str(self.user_details.entry.cn.value)
            if self.user_details and hasattr(self.user_details.entry, "cn")
            else "User"
        )
        header.update(
            f"[bold cyan]Group Memberships: {cn}[/bold cyan]\n\nMember of {len(self.user_details.member_of) if self.user_details else 0} groups\n[dim]Delete: Remove | A: Add | Esc: Close[/dim]\n"
        )

    def _update_user_details(self) -> None:
        """Update user_details after LDAP operations."""
        try:
            # Re-fetch user details to get current group memberships
            from widgets.user_details import UserDetailsPane

            temp_user_details = UserDetailsPane()
            temp_user_details.update_user_details(self.dn, self.connection_manager)
            self.user_details = temp_user_details
        except Exception as e:
            self.app.notify(f"Error refreshing user details: {e}", severity="error")

    def action_remove_group(self) -> None:
        """Remove selected group."""
        groups_list = self.query_one("#groups-list", ListView)
        if not groups_list.highlighted_child:
            self.app.notify("No group selected", severity="warning")
            return

        item = groups_list.highlighted_child
        group_data = self.groups_data.get(id(item))
        if not group_data:
            self.app.notify("Invalid group selection", severity="warning")
            return

        try:
            from ldap3 import MODIFY_DELETE

            def remove_group_op(conn):
                conn.modify(group_data["dn"], {"member": [(MODIFY_DELETE, [self.dn])]})

            self.connection_manager.execute_with_retry(remove_group_op)
            self.app.notify(
                f"Removed from {group_data['name']}", severity="information"
            )

            # Update user details and refresh list instead of direct manipulation
            self._update_user_details()
            self._refresh_groups_list()

            # Refocus the list
            groups_list.focus()
        except Exception as e:
            self.app.notify(f"Error removing from group: {e}", severity="error")

    def action_add_group(self) -> None:
        """Focus search input to add group."""
        self.query_one("#group-search", Input).focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        """Search for groups as user types."""
        if event.input.id == "group-search":
            query = event.value.strip()
            if len(query) >= 2:
                self._search_groups(query)
            elif len(query) == 0:
                # Clear search results
                groups_list = self.query_one("#groups-list", ListView)
                groups_list.clear()
                # Repopulate with current memberships
                if self.user_details and self.user_details.member_of:
                    for group in self.user_details.member_of:
                        item = ListItem(Label(group["name"]))
                        self.groups_data[id(item)] = group
                        groups_list.append(item)

    def _search_groups(self, query: str) -> None:
        """Search for groups matching query and show in list."""
        try:
            # Use domain base DN to search all groups in AD, not just user's OU
            def search_groups_op(conn):
                conn.search(
                    self.base_dn,
                    f"(&(objectClass=group)(cn=*{query}*))",
                    attributes=["cn", "distinguishedName"],
                    size_limit=50,
                )
                return conn.entries

            entries = self.connection_manager.execute_with_retry(search_groups_op)

            # Sort entries alphabetically by group name
            entries = sorted(entries, key=lambda x: str(x.cn.value).lower())

            # Clear and show search results
            groups_list = self.query_one("#groups-list", ListView)
            groups_list.clear()
            self.groups_data.clear()

            if entries:
                for entry in entries:
                    group_name = str(entry.cn.value)
                    group_dn = entry.entry_dn

                    # Mark if already a member
                    is_member = any(
                        g["dn"] == group_dn for g in (self.user_details.member_of or [])
                    )
                    label_text = (
                        f"{group_name} [dim](member)[/dim]" if is_member else group_name
                    )

                    item = ListItem(Label(label_text))
                    self.groups_data[id(item)] = {
                        "name": group_name,
                        "dn": group_dn,
                        "is_member": is_member,
                    }
                    groups_list.append(item)

                self.app.notify(f"Found {len(entries)} groups", severity="information")
            else:
                self.app.notify(
                    f"No groups found matching '{query}'", severity="information"
                )
        except Exception as e:
            self.app.notify(f"Search error: {e}", severity="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "remove":
            self.action_remove_group()
        elif event.button.id == "add":
            # Add by search text
            search_input = self.query_one("#group-search", Input)
            query = search_input.value.strip()
            if query:
                self._add_group_by_name(query)
        else:
            self.dismiss()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Add to selected group from search results."""
        if event.list_view.id == "groups-list":
            item = event.item
            group_data = self.groups_data.get(id(item))
            if group_data and not group_data.get("is_member", False):
                self._add_to_group(group_data)

    def _add_group_by_name(self, group_name: str) -> None:
        """Add user to group by search then selection."""
        # Just trigger search, user selects from results
        self._search_groups(group_name)

    def _add_to_group(self, group_data: dict) -> None:
        """Add user to specified group."""
        try:
            from ldap3 import MODIFY_ADD

            def add_to_group_op(conn):
                conn.modify(group_data["dn"], {"member": [(MODIFY_ADD, [self.dn])]})

            self.connection_manager.execute_with_retry(add_to_group_op)
            self.app.notify(f"Added to {group_data['name']}", severity="information")

            # Update user details and refresh list
            self._update_user_details()
            self._refresh_groups_list()

            # Clear search input
            search_input = self.query_one("#group-search", Input)
            search_input.value = ""
            search_input.focus()
        except Exception as e:
            self.app.notify(f"Error adding to group: {e}", severity="error")


class ManageGroupMembersDialog(ModalScreen):
    """Dialog to manage group members."""

    BINDINGS = [
        ("escape", "dismiss_dialog", "Close"),
    ]

    def __init__(self, dn: str, connection_manager, group_details):
        super().__init__()
        self.dn = dn
        self.connection_manager = connection_manager
        self.group_details = group_details

    def compose(self) -> ComposeResult:
        cn = (
            str(self.group_details.entry.cn.value)
            if self.group_details and hasattr(self.group_details.entry, "cn")
            else "Group"
        )

        yield Vertical(
            Static(
                f"[bold cyan]Group Members: {cn}[/bold cyan]\n\nMembers ({len(self.group_details.members) if self.group_details else 0})\n[dim]Esc: Close[/dim]\n",
                id="question",
            ),
            ListView(id="members-list"),
            Horizontal(
                Button("Close", variant="primary", id="close"), id="dialog-buttons"
            ),
            id="dialog",
        )

    def on_mount(self) -> None:
        """Populate the members list after mounting."""
        members_list = self.query_one("#members-list", ListView)
        if self.group_details and self.group_details.members:
            for member in self.group_details.members:
                members_list.append(ListItem(Label(member["name"])))
        members_list.focus()

    def action_dismiss_dialog(self) -> None:
        self.dismiss()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss()


class EditAttributesDialog(ModalScreen):
    """Dialog to edit object attributes."""

    def __init__(self, dn: str, connection_manager):
        super().__init__()
        self.dn = dn
        self.connection_manager = connection_manager
        self.attributes = {}

    def compose(self) -> ComposeResult:
        yield Vertical(
            Static(
                f"[bold cyan]All Attributes[/bold cyan]\n{self.dn}\n[dim]Select attribute and press Enter to edit | Esc: Close[/dim]\n",
                id="question",
            ),
            ListView(id="attributes-list"),
            Horizontal(
                Button("Close", variant="primary", id="close"), id="dialog-buttons"
            ),
            id="dialog",
        )

    def on_mount(self) -> None:
        """Load and display all attributes."""
        try:

            def load_attributes_op(conn):
                conn.search(
                    self.dn, "(objectClass=*)", search_scope="BASE", attributes=["*"]
                )
                return conn.entries

            entries = self.connection_manager.execute_with_retry(load_attributes_op)
            if entries:
                entry = entries[0]
                attrs_list = self.query_one("#attributes-list", ListView)

                for attr in sorted(entry.entry_attributes_as_dict.keys()):
                    values = entry.entry_attributes_as_dict[attr]
                    if isinstance(values, list):
                        value_str = ", ".join(str(v) for v in values[:3])
                        if len(values) > 3:
                            value_str += f" ... (+{len(values) - 3} more)"
                    else:
                        value_str = str(values)

                    # Truncate long values
                    if len(value_str) > 60:
                        value_str = value_str[:60] + "..."

                    label = f"[bold]{attr}:[/bold] {value_str}"
                    item = ListItem(Label(label))
                    self.attributes[id(item)] = {"name": attr, "values": values}
                    attrs_list.append(item)

                attrs_list.focus()
        except Exception as e:
            self.app.notify(f"Error loading attributes: {e}", severity="error")

    def action_dismiss_dialog(self) -> None:
        self.dismiss()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Edit selected attribute."""
        item = event.item
        attr_data = self.attributes.get(id(item))
        if attr_data:
            # Open edit dialog for this attribute
            self.app.push_screen(
                EditSingleAttributeDialog(
                    self.dn,
                    self.connection_manager,
                    attr_data["name"],
                    attr_data["values"],
                ),
                self._refresh_after_edit,
            )

    def _refresh_after_edit(self, result) -> None:
        """Refresh attributes list after editing."""
        if result:
            # Reload the attributes
            attrs_list = self.query_one("#attributes-list", ListView)
            attrs_list.clear()
            self.attributes.clear()
            self.on_mount()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss()


class EditSingleAttributeDialog(ModalScreen):
    """Dialog to edit a single attribute."""

    def __init__(self, dn: str, connection_manager, attr_name: str, current_values):
        super().__init__()
        self.dn = dn
        self.connection_manager = connection_manager
        self.attr_name = attr_name
        self.current_values = current_values

    def compose(self) -> ComposeResult:
        # Convert values to string
        if isinstance(self.current_values, list):
            value_str = "\n".join(str(v) for v in self.current_values)
        else:
            value_str = str(self.current_values)

        yield Vertical(
            Static(
                f"[bold cyan]Edit Attribute: {self.attr_name}[/bold cyan]\n\n[dim]For multi-value: one per line[/dim]\n",
                id="question",
            ),
            Input(placeholder="New value", id="attr-value", value=value_str),
            Horizontal(
                Button("Save", variant="success", id="save"),
                Button("Cancel", variant="primary", id="cancel"),
                id="dialog-buttons",
            ),
            id="dialog",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save":
            try:
                from ldap3 import MODIFY_REPLACE, MODIFY_DELETE

                new_value = self.query_one("#attr-value", Input).value.strip()

                if new_value:
                    # Split by newlines for multi-value
                    values = [v.strip() for v in new_value.split("\n") if v.strip()]

                    def update_attr_op(conn):
                        conn.modify(
                            self.dn, {self.attr_name: [(MODIFY_REPLACE, values)]}
                        )

                    self.connection_manager.execute_with_retry(update_attr_op)
                    self.app.notify(f"Updated {self.attr_name}", severity="information")
                    self.dismiss(True)
                else:
                    # Delete the attribute if value is empty

                    def delete_attr_op(conn):
                        conn.modify(self.dn, {self.attr_name: [(MODIFY_DELETE, [])]})

                    self.connection_manager.execute_with_retry(delete_attr_op)
                    self.app.notify(f"Deleted {self.attr_name}", severity="information")
                    self.dismiss(True)
            except Exception as e:
                self.app.notify(f"Error: {e}", severity="error")
        else:
            self.dismiss(False)


def validate_password_complexity(password: str) -> tuple[bool, list[str]]:
    """Validate password meets AD complexity requirements.

    Returns:
        Tuple of (is_valid: bool, error_messages: list[str])
    """
    errors = []

    # Length check (minimum 8 characters for AD default)
    if len(password) < 8:
        errors.append("Password must be at least 8 characters long")

    # Complexity checks
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)

    complexity_count = sum([has_upper, has_lower, has_digit, has_special])
    if complexity_count < 3:
        errors.append(
            "Password must contain at least 3 of: uppercase, lowercase, digits, special characters"
        )

    # Check for common patterns
    if password.lower() in ["password", "12345678", "qwerty123"]:
        errors.append("Password is too common")

    # Check for username inclusion (basic check)
    # This would need the actual username for proper validation

    return len(errors) == 0, errors


class SetPasswordDialog(ModalScreen):
    """Dialog to set user password."""

    def __init__(self, dn: str, connection_manager):
        super().__init__()
        self.dn = dn
        self.connection_manager = connection_manager

    def _validate_password_complexity(self, password: str) -> bool:
        """Validate password meets AD complexity requirements."""
        errors = []

        # Length check (minimum 8 characters for AD default)
        if len(password) < 8:
            errors.append("Password must be at least 8 characters long")

        # Complexity checks
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)

        complexity_count = sum([has_upper, has_lower, has_digit, has_special])
        if complexity_count < 3:
            errors.append(
                "Password must contain at least 3 of: uppercase, lowercase, digits, special characters"
            )

        # Check for common patterns
        if password.lower() in ["password", "12345678", "qwerty123"]:
            errors.append("Password is too common")

        if errors:
            error_msg = "Password requirements not met:\n" + "\n".join(
                f"• {error}" for error in errors
            )
            self.app.notify(error_msg, severity="warning")
            return False

        return True

    def compose(self) -> ComposeResult:
        cn = self.dn.split(",")[0].split("=")[1] if "," in self.dn else self.dn
        yield Vertical(
            Static(f"[bold cyan]Set Password for: {cn}[/bold cyan]\n", id="question"),
            Static("New password:"),
            Input(placeholder="Enter new password", password=True, id="password1"),
            Static("\nConfirm password:"),
            Input(placeholder="Re-enter password", password=True, id="password2"),
            Static(""),  # Spacer
            Horizontal(
                Button("Set Password", variant="success", id="save"),
                Button("Cancel", variant="primary", id="cancel"),
                id="dialog-buttons",
            ),
            id="dialog",
            classes="password-dialog",
        )

    def on_mount(self) -> None:
        """Focus first password field."""
        self.query_one("#password1", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save":
            try:
                pwd1_input = self.query_one("#password1", Input)
                pwd2_input = self.query_one("#password2", Input)

                pwd1 = pwd1_input.value
                pwd2 = pwd2_input.value

                if len(pwd1) == 0 or len(pwd2) == 0:
                    self.app.notify("Password cannot be empty", severity="warning")
                    return

                if pwd1 != pwd2:
                    self.app.notify("Passwords do not match", severity="warning")
                    return

                if len(pwd1) < 8:
                    self.app.notify(
                        "Password must be at least 8 characters", severity="warning"
                    )
                    return

                # Set password using ldap3 Microsoft extension for Active Directory
                # Check if connection is secure (required for password operations)
                if hasattr(self.connection_manager, "get_connection"):
                    conn = self.connection_manager.get_connection()
                    if hasattr(conn, "server") and not conn.server.ssl:
                        self.app.notify(
                            "Password changes require SSL/TLS connection. Enable use_ssl in config.ini",
                            severity="error",
                        )
                        return
                else:
                    self.app.notify("No connection available", severity="error")
                    return

                # Validate password complexity for AD
                is_valid, errors = validate_password_complexity(pwd1)
                if not is_valid:
                    error_msg = "Password requirements not met:\n" + "\n".join(
                        f"• {error}" for error in errors
                    )
                    self.app.notify(error_msg, severity="warning")
                    return

                def set_password_op(conn: Connection):
                    # Use Microsoft extension for password modification (handles encoding automatically)
                    result = conn.extend.microsoft.modify_password(self.dn, pwd1)

                    if result and conn.result["result"] == 0:
                        self.app.notify(
                            "Password updated successfully", severity="information"
                        )
                        self.dismiss(True)
                    else:
                        error_msg = conn.result.get("message", "Unknown error")
                        error_desc = conn.result.get("description", "No description")

                if self.connection_manager:
                    self.connection_manager.execute_with_retry(set_password_op)
            except Exception as e:
                self.app.notify(f"Error setting password: {e}", severity="error")
                import traceback

                traceback.print_exc()
        else:
            self.dismiss(False)


class ConfirmUnlockDialog(BaseConfirmDialog):
    """Dialog to confirm user account unlock."""

    def __init__(self, label: str, dn: str):
        super().__init__(
            title="[bold red]⚠ Unlock Account[/bold red]",
            message=f"Are you sure you want to unlock this account?\n\n{label}\n\nDN: {dn}\n\n[yellow]This will reset the lockout counter and allow login attempts.[/yellow]",
            confirm_text="Unlock",
            confirm_variant="error",
        )


class ConfirmEnableDialog(BaseConfirmDialog):
    """Dialog to confirm user account enable."""

    def __init__(self, label: str, dn: str):
        super().__init__(
            title="[bold green]✓ Enable Account[/bold green]",
            message=f"Are you sure you want to enable this disabled account?\n\n{label}\n\nDN: {dn}\n\n[yellow]This will allow user to log in to system.[/yellow]",
            confirm_text="Enable",
            confirm_variant="success",
        )


class ConfirmDisableDialog(BaseConfirmDialog):
    """Dialog to confirm user account disable."""

    def __init__(self, label: str, dn: str):
        super().__init__(
            title="[bold red]⚠ Disable Account[/bold red]",
            message=f"Are you sure you want to disable this account?\n\n{label}\n\nDN: {dn}\n\n[yellow]This will prevent user from logging in to system.[/yellow]",
            confirm_text="Disable",
            confirm_variant="error",
        )


class ConfirmRestoreDialog(BaseConfirmDialog):
    """Dialog to confirm restoring a deleted object from Recycle Bin."""

    def __init__(self, label: str, dn: str):
        super().__init__(
            title="[bold green]♻ Restore Object[/bold green]",
            message=f"Are you sure you want to restore this deleted object?\n\n{label}\n\n[yellow]The object will be restored to its original location.[/yellow]",
            confirm_text="Restore",
            confirm_variant="success",
        )


class CreateUserDialog(ModalScreen):
    """Dialog to create a new user account."""

    def __init__(self, target_ou: str, ldap_service):
        super().__init__()
        self.target_ou = target_ou
        self.ldap_service = ldap_service

    def compose(self) -> ComposeResult:
        yield Vertical(
            Static(f"[bold green]Create New User Account[/bold green]\n"),
            Static(f"Target OU: [cyan]{self.target_ou}[/cyan]\n"),
            ScrollableContainer(
                Input(placeholder="Full Name*", id="full-name"),
                Input(placeholder="First Name (optional)", id="first-name"),
                Input(placeholder="Last Name (optional)", id="last-name"),
                Input(placeholder="User Logon Name*", id="samaccount"),
                Static("\n[bold]Password:[/bold]"),
                Input(placeholder="Password*", password=True, id="password1"),
                Input(placeholder="Confirm Password*", password=True, id="password2"),
                Static("\n[bold]Account Options:[/bold]"),
                Checkbox(
                    "User must change password at next logon",
                    id="must-change",
                    value=True,
                ),
                Checkbox("User cannot change password", id="cannot-change"),
                Checkbox("Password never expires", id="never-expires"),
                Checkbox("Account is disabled", id="disabled"),
                Horizontal(
                    Static("Account expires (YYYY-MM-DD, optional):"),
                    Input(placeholder="", id="account-expires"),
                ),
                id="scrollable-content",
            ),
            Horizontal(
                Button("Create", variant="success", id="create"),
                Button("Cancel", variant="primary", id="cancel"),
                id="dialog-buttons",
            ),
            id="dialog",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "create":
            self._create_user()
        else:
            self.dismiss(None)

    def on_input_changed(self, event: Input.Changed) -> None:
        """Auto-generate sAMAccountName when full name changes."""
        if (
            event.input.id == "full-name"
            and not self.query_one("#samaccount", Input).value
        ):
            full_name = event.value.strip()
            if full_name:
                samaccount = self.ldap_service.generate_samaccount_name(full_name)
                self.query_one("#samaccount", Input).value = samaccount

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Validate sAMAccountName availability."""
        if event.input.id == "samaccount":
            samaccount = event.value.strip()
            if samaccount:
                available, message = self.ldap_service.check_samaccount_availability(
                    samaccount
                )
                if not available:
                    self.app.notify(message, severity="warning")

    def _create_user(self):
        """Create the user account."""
        try:
            # Get form values
            full_name = self.query_one("#full-name", Input).value.strip()
            first_name = self.query_one("#first-name", Input).value.strip()
            last_name = self.query_one("#last-name", Input).value.strip()
            samaccount = self.query_one("#samaccount", Input).value.strip()
            password1 = self.query_one("#password1", Input).value
            password2 = self.query_one("#password2", Input).value

            # Validate required fields
            if not full_name:
                self.app.notify("Full Name is required", severity="warning")
                return
            if not samaccount:
                self.app.notify("User Logon Name is required", severity="warning")
                return
            if not password1:
                self.app.notify("Password is required", severity="warning")
                return
            if password1 != password2:
                self.app.notify("Passwords do not match", severity="warning")
                return

            # Validate password complexity
            is_valid, errors = validate_password_complexity(password1)
            if not is_valid:
                error_msg = "Password requirements not met:\n" + "\n".join(
                    f"• {error}" for error in errors
                )
                self.app.notify(error_msg, severity="warning")
                return

            # Get account options
            must_change = self.query_one("#must-change", Checkbox).value
            cannot_change = self.query_one("#cannot-change", Checkbox).value
            never_expires = self.query_one("#never-expires", Checkbox).value
            disabled = self.query_one("#disabled", Checkbox).value
            account_expires = self.query_one("#account-expires", Input).value.strip()

            # Create user
            success, message, user_dn = self.ldap_service.create_user(
                full_name=full_name,
                samaccount=samaccount,
                password=password1,
                ou_dn=self.target_ou,
                first_name=first_name,
                last_name=last_name,
                user_must_change_password=must_change,
                user_cannot_change_password=cannot_change,
                password_never_expires=never_expires,
                account_disabled=disabled,
                account_expires=account_expires if account_expires else "",
            )

            if success:
                self.app.notify(message, severity="information")
                self.dismiss(
                    {
                        "success": True,
                        "message": message,
                        "user_dn": user_dn,
                        "full_name": full_name,
                        "samaccount": samaccount,
                    }
                )
            else:
                self.app.notify(message, severity="error")

        except Exception as e:
            self.app.notify(f"Error creating user: {e}", severity="error")


class CopyUserDialog(ModalScreen):
    """Dialog to copy an existing user account."""

    def __init__(self, source_dn: str, source_label: str, target_ou: str, ldap_service):
        super().__init__()
        self.source_dn = source_dn
        self.source_label = source_label
        self.target_ou = target_ou
        self.ldap_service = ldap_service

    def compose(self) -> ComposeResult:
        yield Vertical(
            Static(f"[bold green]Copy User Account[/bold green]\n"),
            Static(f"Source User: [cyan]{self.source_label}[/cyan]"),
            Static(f"Target OU: [cyan]{self.target_ou}[/cyan]\n"),
            ScrollableContainer(
                Input(placeholder="New Full Name*", id="full-name"),
                Input(placeholder="New User Logon Name*", id="samaccount"),
                Static("\n[bold]Password:[/bold]"),
                Input(placeholder="Password*", password=True, id="password1"),
                Input(placeholder="Confirm Password*", password=True, id="password2"),
                Static("\n[bold]Copy Options:[/bold]"),
                Checkbox("Copy group memberships", id="copy-groups"),
                Checkbox(
                    "Copy account options (password settings, disabled status)",
                    id="copy-options",
                ),
                Checkbox("Copy manager relationship", id="copy-manager"),
                Static("\n[bold]Account Options:[/bold]"),
                Checkbox(
                    "User must change password at next logon",
                    id="must-change",
                    value=True,
                ),
                Checkbox("User cannot change password", id="cannot-change"),
                Checkbox("Password never expires", id="never-expires"),
                Checkbox("Account is disabled", id="disabled"),
                Horizontal(
                    Static("Account expires (YYYY-MM-DD, optional):"),
                    Input(placeholder="", id="account-expires"),
                ),
                id="scrollable-content",
            ),
            Horizontal(
                Button("Copy", variant="success", id="copy"),
                Button("Cancel", variant="primary", id="cancel"),
                id="dialog-buttons",
            ),
            id="dialog",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "copy":
            self._copy_user()
        else:
            self.dismiss(None)

    def on_input_changed(self, event: Input.Changed) -> None:
        """Auto-generate sAMAccountName when full name changes."""
        if (
            event.input.id == "full-name"
            and not self.query_one("#samaccount", Input).value
        ):
            full_name = event.value.strip()
            if full_name:
                samaccount = self.ldap_service.generate_samaccount_name(full_name)
                self.query_one("#samaccount", Input).value = samaccount

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Validate sAMAccountName availability."""
        if event.input.id == "samaccount":
            samaccount = event.value.strip()
            if samaccount:
                available, message = self.ldap_service.check_samaccount_availability(
                    samaccount
                )
                if not available:
                    self.app.notify(message, severity="warning")

    def _copy_user(self):
        """Copy the user account."""
        try:
            # Get form values
            new_full_name = self.query_one("#full-name", Input).value.strip()
            new_samaccount = self.query_one("#samaccount", Input).value.strip()
            password1 = self.query_one("#password1", Input).value
            password2 = self.query_one("#password2", Input).value

            # Validate required fields
            if not new_full_name:
                self.app.notify("New Full Name is required", severity="warning")
                return
            if not new_samaccount:
                self.app.notify("New User Logon Name is required", severity="warning")
                return
            if not password1:
                self.app.notify("Password is required", severity="warning")
                return
            if password1 != password2:
                self.app.notify("Passwords do not match", severity="warning")
                return

            # Validate password complexity
            is_valid, errors = validate_password_complexity(password1)
            if not is_valid:
                error_msg = "Password requirements not met:\n" + "\n".join(
                    f"• {error}" for error in errors
                )
                self.app.notify(error_msg, severity="warning")
                return

            # Get copy options
            copy_groups = self.query_one("#copy-groups", Checkbox).value
            copy_manager = self.query_one("#copy-manager", Checkbox).value
            copy_options = self.query_one("#copy-options", Checkbox).value

            # Copy user
            success, message, user_dn = self.ldap_service.copy_user(
                source_dn=self.source_dn,
                new_full_name=new_full_name,
                new_samaccount=new_samaccount,
                password=password1,
                target_ou_dn=self.target_ou,
                copy_groups=copy_groups,
                copy_manager=copy_manager,
                copy_account_options=copy_options,
            )

            if success:
                self.app.notify(message, severity="information")
                self.dismiss(
                    {
                        "success": True,
                        "message": message,
                        "user_dn": user_dn,
                        "full_name": new_full_name,
                        "samaccount": new_samaccount,
                    }
                )
            else:
                self.app.notify(message, severity="error")

        except Exception as e:
            self.app.notify(f"Error copying user: {e}", severity="error")


class ADSelectionDialog(ModalScreen[str]):
    """Dialog for selecting AD domain when multiple are configured."""

    CSS = """
    ADSelectionDialog {
        align: center middle;
    }
    
    #dialog {
        width: 60;
        max-width: 60;
        height: 30;
        border: thick $background 80%;
        background: $surface;
        padding: 2 3;
    }
    
    #ascii-art {
        text-align: center;
        margin-bottom: 2;
    }
    
    #question {
        text-align: center;
        margin-bottom: 1;
    }
    
    #domains-list {
        height: auto;
        max-height: 15;
        margin: 1 0;
        border: solid $primary;
    }
    
    #domain-info {
        text-align: center;
        margin-top: 1;
        color: $text-muted;
    }
    
    #dialog-buttons {
        align: center middle;
        margin-top: 2;
        width: 100%;
    }
    
    #dialog-buttons Button {
        margin: 0 1;
        min-width: 12;
    }
    """

    def __init__(self, ad_configs: Dict[str, "ADConfig"]):
        super().__init__()
        self.ad_configs = ad_configs
        self.domain_data = {}

    def compose(self) -> ComposeResult:
        ascii_art = """[bold palegreen]   db    888b.    88888 8    8 888 [/bold palegreen]
[bold palegreen]  dPYb   8   8      8   8    8  8  [/bold palegreen]
[bold palegreen] dPwwYb  8   8      8   8b..d8  8  [/bold palegreen]
[bold palegreen]dP    Yb 888P'      8   `Y88P' 888 [/bold palegreen]
                                   """

        yield Vertical(
            Static(ascii_art, id="ascii-art"),
            Static(
                "[bold cyan]Select Active Directory Domain[/bold cyan]\n", id="question"
            ),
            ListView(id="domains-list"),
            Static("", id="domain-info"),
            Horizontal(
                Button("Select", variant="success", id="select"),
                Button("Cancel", variant="primary", id="cancel"),
                id="dialog-buttons",
            ),
            id="dialog",
        )

    def on_mount(self) -> None:
        """Populate the domains list after mounting."""
        domains_list = self.query_one("#domains-list", ListView)

        for domain, config in self.ad_configs.items():
            label = f"[bold]{domain}[/bold] - {config.server}"
            if config.use_ssl:
                label += " [green](SSL)[/green]"
            else:
                label += " [yellow](No SSL)[/yellow]"

            item = ListItem(Label(label))
            self.domain_data[id(item)] = domain
            domains_list.append(item)

        domains_list.focus()

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        """Update domain info when selection changes."""
        if event.list_view.id == "domains-list":
            item = event.item
            domain = self.domain_data.get(id(item))
            if domain:
                config = self.ad_configs[domain]
                info_text = f"Domain: {config.domain}\nServer: {config.server}\nBase DN: {config.base_dn}"
                self.query_one("#domain-info", Static).update(info_text)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "select":
            domains_list = self.query_one("#domains-list", ListView)
            if domains_list.highlighted_child:
                item = domains_list.highlighted_child
                domain = self.domain_data.get(id(item))
                if domain:
                    self.dismiss(domain)
            else:
                self.app.notify("Please select a domain", severity="warning")
        else:
            self.dismiss(None)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle domain selection from list."""
        if event.list_view.id == "domains-list":
            item = event.item
            domain = self.domain_data.get(id(item))
            if domain:
                self.dismiss(domain)


class LoginDialog(ModalScreen):
    """Dialog for user authentication."""

    CSS = """
    LoginDialog {
        align: center middle;
    }
    
    Horizontal {
        align: center middle;
    }
    
    #dialog {
        width: 60;
        height: 30;
        border: thick $background 80%;
        background: $surface;
        padding: 1 2;
    }
    
    #question {
        text-align: center;
        margin-bottom: 1;
    }
    
    Input {
        width: 100%;
        margin: 1 0;
    }
    
    #dialog-buttons {
        align: center middle;
        margin-top: 1;
        width: 100%;
    }
    
    #dialog-buttons Button {
        align: center middle;
        margin: 0 1;
        min-width: 50%;
    }
    """

    def __init__(self, last_user: str, domain: str, ad_config=None):
        super().__init__()
        self.last_user = last_user
        self.domain = domain
        self.ad_config = ad_config

    def compose(self) -> ComposeResult:
        ascii_art = """[bold palegreen]   db    888b.    88888 8    8 888 [/bold palegreen]
[bold palegreen]  dPYb   8   8      8   8    8  8  [/bold palegreen]
[bold palegreen] dPwwYb  8   8      8   8b..d8  8  [/bold palegreen]
[bold palegreen]dP    Yb 888P'      8   `Y88P' 888 [/bold palegreen]
                                   """
        yield Horizontal(
            Vertical(
                Static(
                    f"{ascii_art}\n\n[bold cyan]Active Directory Login[/bold cyan]\nDomain: {self.domain}\n",
                    id="question",
                ),
                Input(placeholder="Username", id="username", value=self.last_user),
                Input(placeholder="Password", password=True, id="password"),
                Horizontal(
                    Button("Login", variant="success", id="login"),
                    Button("Cancel", variant="primary", id="cancel"),
                    id="dialog-buttons",
                ),
                id="dialog",
            )
        )

    def on_mount(self) -> None:
        """Focus username field if empty, otherwise password field."""
        username_input = self.query_one("#username", Input)
        if username_input.value:
            self.query_one("#password", Input).focus()
        else:
            username_input.focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key in input fields."""
        if event.input.id == "username":
            # Move to password field when Enter is pressed in username
            self.query_one("#password", Input).focus()
        elif event.input.id == "password":
            # Trigger login when Enter is pressed in password field
            self._attempt_login()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "login":
            self._attempt_login()
        else:
            self.dismiss(None)

    def _attempt_login(self) -> None:
        """Attempt to login with current credentials."""
        username = self.query_one("#username", Input).value.strip()
        password = self.query_one("#password", Input).value

        if not username:
            self.app.notify("Username is required", severity="warning")
            return
        if not password:
            self.app.notify("Password is required", severity="warning")
            return

        self.dismiss((username, password))
