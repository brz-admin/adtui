"""Path Service - Handles DN/path conversions."""

from typing import List


class PathService:
    """Handles conversion between human-readable paths and LDAP DNs."""

    def __init__(self, base_dn: str):
        """Initialize path service.

        Args:
            base_dn: Base Distinguished Name for the domain
        """
        self.base_dn = base_dn

    def dn_to_path(self, dn: str) -> str:
        """Convert DN to human-readable path without DC components.

        Args:
            dn: Distinguished Name like "cn=User,ou=IT,ou=Departments,dc=example,dc=com"

        Returns:
            Human path like "Departments/IT"

        Examples:
            >>> path_service.dn_to_path("cn=User,ou=IT,ou=Departments,dc=example,dc=com")
            "Departments/IT"
        """
        if not dn:
            return ""

        parts = dn.split(",")
        ou_parts = []

        for part in parts:
            part = part.strip()
            if part.lower().startswith("ou="):
                ou_parts.append(part[3:])
            elif part.lower().startswith("dc="):
                # Skip DC components
                continue

        # Reverse to get top-down path
        ou_parts.reverse()
        return "/".join(ou_parts) if ou_parts else ""

    def path_to_dn(self, path: str) -> str:
        """Convert human-readable path to full LDAP DN.

        Args:
            path: Human path like "Departments/IT" or full DN

        Returns:
            Full LDAP DN like "ou=IT,ou=Departments,dc=example,dc=com"

        Examples:
            >>> path_service.path_to_dn("Departments/IT")
            "ou=IT,ou=Departments,dc=example,dc=com"

            >>> path_service.path_to_dn("ou=IT,ou=Departments,dc=example,dc=com")
            "ou=IT,ou=Departments,dc=example,dc=com"
        """
        # If it looks like a full DN already, return it
        if "=" in path and ("ou=" in path.lower() or "cn=" in path.lower()):
            return path

        # Clean up the path
        path = path.strip().strip("/")

        if not path:
            return self.base_dn

        # Split by / and reverse to get DN order
        parts = [p.strip() for p in path.split("/") if p.strip()]
        parts.reverse()

        # Build the DN
        ou_parts = [f"ou={part}" for part in parts]

        # Append base DN
        full_dn = ",".join(ou_parts) + "," + self.base_dn

        return full_dn

    def get_parent_dn(self, dn: str) -> str:
        """Get the parent DN from a full DN.

        Args:
            dn: Full Distinguished Name

        Returns:
            Parent DN

        Examples:
            >>> path_service.get_parent_dn("cn=User,ou=IT,dc=example,dc=com")
            "ou=IT,dc=example,dc=com"
        """
        parts = dn.split(",", 1)
        if len(parts) > 1:
            return parts[1]
        return self.base_dn

    def get_rdn(self, dn: str) -> str:
        """Get the Relative Distinguished Name from a full DN.

        Args:
            dn: Full Distinguished Name

        Returns:
            RDN (first component)

        Examples:
            >>> path_service.get_rdn("cn=User,ou=IT,dc=example,dc=com")
            "cn=User"
        """
        return dn.split(",")[0]

    def extract_ou_name_from_path(self, path: str) -> str:
        """Extract the OU name from a path.

        Args:
            path: Path like "Departments/IT/Developers"

        Returns:
            Last component (OU name) like "Developers"
        """
        parts = path.strip("/").split("/")
        return parts[-1].strip() if parts else ""

    def resolve_path(self, path: str) -> str:
        """Resolve a path to a full DN (alias for path_to_dn).

        Args:
            path: Human path like "Departments/IT" or full DN

        Returns:
            Full LDAP DN
        """
        return self.path_to_dn(path)

    def extract_cn(self, dn: str) -> str:
        """Extract the Common Name from a DN.

        Args:
            dn: Full Distinguished Name like "cn=User,ou=IT,dc=example,dc=com"

        Returns:
            Common Name like "User"
        """
        if not dn:
            return ""
        first_part = dn.split(",")[0]
        if "=" in first_part:
            return first_part.split("=")[1]
        return first_part
