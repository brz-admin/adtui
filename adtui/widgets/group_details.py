"""Group details pane widget for displaying AD group information."""

import logging
from typing import Optional, List, Any

from textual.widgets import Static
from ldap3 import MODIFY_ADD, MODIFY_DELETE

logger = logging.getLogger(__name__)


class GroupDetailsPane(Static):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.group_dn = None
        self.connection_manager = None
        self.entry = None
        self.members = []
        self.member_of = []

    def update_group_details(self, group_dn, connection_manager):
        """Load and display group details."""

        self.group_dn = group_dn
        self.connection_manager = connection_manager
        self.load_group_details()

    def load_group_details(self):
        """Fetch group members and memberOf from LDAP."""

        try:

            def search_group_op(conn):
                conn.search(
                    self.group_dn,
                    "(objectClass=*)",
                    search_scope="BASE",
                    attributes=["cn", "member", "memberOf", "description", "groupType"],
                )
                return conn.entries

            entries = self.connection_manager.execute_with_retry(search_group_op)

            if entries:
                self.entry = entries[0]

                # Extract members (just the CN)
                if hasattr(self.entry, "member") and self.entry.member:
                    self.members = [
                        {"name": dn.split(",")[0].split("=")[1], "dn": dn}
                        for dn in self.entry.member.values
                    ]
                else:
                    self.members = []

                # Extract memberOf groups (just the CN)
                if hasattr(self.entry, "memberOf") and self.entry.memberOf:
                    self.member_of = [
                        {"name": dn.split(",")[0].split("=")[1], "dn": dn}
                        for dn in self.entry.memberOf.values
                    ]
                else:
                    self.member_of = []
        except Exception as e:
            import traceback

            traceback.print_exc()

    def refresh_display(self):
        """Refresh the displayed content."""
        if not self.entry:
            return "[red]Error loading group details[/red]"

        return self._build_content()

    def _build_content(self) -> str:
        """Build the content string for display."""

        if not self.entry:
            logger.debug("No entry found, returning 'No group data'")
            return "No group data"

        # General Information
        cn = str(self.entry.cn.value) if hasattr(self.entry, "cn") else "N/A"
        description = (
            str(self.entry.description.value)
            if hasattr(self.entry, "description")
            else "N/A"
        )

        # Group type
        group_type = "N/A"
        if hasattr(self.entry, "groupType"):
            gt = int(self.entry.groupType.value)
            if gt & 0x00000002:
                group_type = "Global"
            elif gt & 0x00000004:
                group_type = "Domain Local"
            elif gt & 0x00000008:
                group_type = "Universal"
            if gt & 0x80000000:
                group_type += " Security Group"
            else:
                group_type += " Distribution Group"

        # Build content
        content = f"""[bold cyan]Group Details[/bold cyan]

[bold]General Information:[/bold]
Group Name: {cn}
Description: {description}
Group Type: {group_type}
DN: {self.group_dn}

[bold]Members ({len(self.members)}):[/bold]
"""

        if self.members:
            for member in self.members:
                content += f"  • {member['name']}\n"
        else:
            content += "  No members\n"

        content += f"\n[bold]Member Of ({len(self.member_of)} groups):[/bold]\n"

        if self.member_of:
            for group in self.member_of:
                content += f"  • {group['name']}\n"
        else:
            content += "  Not a member of any group\n"

        content += "\n[dim]Press 'a' to edit attributes | 'g' to view members[/dim]"

        return content

    def add_member(self, member_dn):
        """Add a member to the group."""
        try:

            def add_member_op(conn):
                conn.modify(self.group_dn, {"member": [(MODIFY_ADD, [member_dn])]})
                return conn.result

            result = self.connection_manager.execute_with_retry(add_member_op)
            if result["result"] == 0:
                logger.info("Successfully added member to group %s", self.group_dn)
                self.load_group_details()
                return True
            else:
                logger.warning(
                    "Failed to add member: %s",
                    result.get("description", "Unknown error"),
                )
                return False
        except Exception as e:
            logger.error("Error adding member to group: %s", e)
            return False

    def remove_member(self, member_dn: str) -> bool:
        """Remove a member from group."""
        try:

            def remove_member_op(conn):
                conn.modify(self.group_dn, {"member": [(MODIFY_DELETE, [member_dn])]})
                return conn.result

            result = self.connection_manager.execute_with_retry(remove_member_op)
            if result["result"] == 0:
                logger.info("Successfully removed member from group %s", self.group_dn)
                self.load_group_details()
                return True
            else:
                logger.warning(
                    "Failed to remove member: %s",
                    result.get("description", "Unknown error"),
                )
                return False
        except Exception as e:
            logger.error("Error removing member from group: %s", e)
            return False

    def join_group(self, parent_group_dn: str) -> bool:
        """Add this group to another group."""
        try:

            def join_group_op(conn):
                conn.modify(
                    parent_group_dn, {"member": [(MODIFY_ADD, [self.group_dn])]}
                )
                return conn.result

            result = self.connection_manager.execute_with_retry(join_group_op)
            if result["result"] == 0:
                logger.info("Successfully joined group %s", parent_group_dn)
                self.load_group_details()
                return True
            else:
                logger.warning(
                    "Failed to join group: %s",
                    result.get("description", "Unknown error"),
                )
                return False
        except Exception as e:
            logger.error("Error joining group: %s", e)
            return False

    def leave_group(self, parent_group_dn: str) -> bool:
        """Remove this group from another group."""
        try:

            def leave_group_op(conn):
                conn.modify(
                    parent_group_dn, {"member": [(MODIFY_DELETE, [self.group_dn])]}
                )
                return conn.result

            result = self.connection_manager.execute_with_retry(leave_group_op)
            if result["result"] == 0:
                logger.info("Successfully left group %s", parent_group_dn)
                self.load_group_details()
                return True
            else:
                logger.warning(
                    "Failed to leave group: %s",
                    result.get("description", "Unknown error"),
                )
                return False
        except Exception as e:
            logger.error("Error leaving group: %s", e)
            return False
