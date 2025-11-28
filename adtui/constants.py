"""Constants and enumerations for ADTUI application."""

from enum import Enum


class ObjectIcon(str, Enum):
    """Icons for different AD object types."""
    USER = "👤"
    GROUP = "👥"
    COMPUTER = "💻"
    OU = "📁"
    GENERIC = "📄"


class ObjectType(str, Enum):
    """AD object types."""
    USER = "user"
    GROUP = "group"
    COMPUTER = "computer"
    OU = "organizationalUnit"
    CONTAINER = "container"


class CommandPrefix(str, Enum):
    """Command prefixes."""
    COLON = ":"
    SLASH = "/"


class Severity(str, Enum):
    """Notification severity levels."""
    INFORMATION = "information"
    WARNING = "warning"
    ERROR = "error"


class LDAPControl:
    """LDAP control OIDs."""
    SHOW_DELETED_OBJECTS = "1.2.840.113556.1.4.417"


class UserAccountControl:
    """User Account Control flags."""
    DISABLED = 0x0002
    LOCKED = 0x0010
    PASSWORD_NEVER_EXPIRES = 0x10000


class PasswordPolicy:
    """Default password policy settings."""
    MAX_AGE_DAYS = 120  # Should be queried from domain policy
    WARNING_DAYS_CRITICAL = 7
    WARNING_DAYS_NORMAL = 14


class AccountPolicy:
    """Account expiry policy settings."""
    WARNING_DAYS_CRITICAL = 7
    WARNING_DAYS_NORMAL = 30
    NEVER_EXPIRES_VALUES = [0, 9223372036854775807]  # 0x7FFFFFFFFFFFFFFF


class HistorySettings:
    """Operation history settings."""
    MAX_HISTORY_SIZE = 50


class SearchSettings:
    """Search configuration."""
    MAX_RESULTS = 1000
    AUTOCOMPLETE_LIMIT = 50


# Command aliases mapping
COMMAND_ALIASES = {
    # Search commands
    's': 'search',
    
    # Delete commands
    'd': 'delete',
    'del': 'delete',
    
    # Move commands
    'm': 'move',
    'mv': 'move',
    
    # OU commands
    'mkou': 'create_ou',
    'createou': 'create_ou',
    
    # Recycle bin commands
    'rb': 'recycle',
    
    # Undo commands
    'u': 'undo',
}


# LDAP attribute names
LDAP_ATTRIBUTES = {
    'COMMON_NAME': 'cn',
    'SAM_ACCOUNT_NAME': 'sAMAccountName',
    'DISPLAY_NAME': 'displayName',
    'MAIL': 'mail',
    'MEMBER_OF': 'memberOf',
    'MEMBER': 'member',
    'DISTINGUISHED_NAME': 'distinguishedName',
    'OBJECT_CLASS': 'objectClass',
    'USER_ACCOUNT_CONTROL': 'userAccountControl',
    'PWD_LAST_SET': 'pwdLastSet',
    'ACCOUNT_EXPIRES': 'accountExpires',
    'IS_DELETED': 'isDeleted',
    'WHEN_CHANGED': 'whenChanged',
    'OU': 'ou',
    'DESCRIPTION': 'description',
    'PROFILE_PATH': 'profilePath',
    'HOME_DIRECTORY': 'homeDirectory',
    'DNS_HOST_NAME': 'dNSHostName',
    'OPERATING_SYSTEM': 'operatingSystem',
    'OPERATING_SYSTEM_VERSION': 'operatingSystemVersion',
}


# LDAP search scopes
class SearchScope(str, Enum):
    """LDAP search scope values."""
    BASE = 'BASE'
    LEVEL = 'LEVEL'
    SUBTREE = 'SUBTREE'


# Default messages
MESSAGES = {
    'NO_SELECTION': "No object selected. Select an object first.",
    'DELETE_SUCCESS': "Successfully deleted object. Use :recycle to restore if needed.",
    'MOVE_SUCCESS': "Successfully moved object",
    'CREATE_OU_SUCCESS': "Successfully created OU",
    'RESTORE_SUCCESS': "Successfully restored object",
    'UNDO_SUCCESS': "Successfully undid operation",
    'DELETE_CANCELLED': "Delete cancelled",
    'MOVE_CANCELLED': "Move cancelled",
    'NO_UNDO_HISTORY': "No operations to undo",
    'UNDO_DELETE_WARNING': "Cannot undo delete. Check :recycle for deleted objects.",
    'SEARCH_EMPTY': "Search query is empty",
    'RECYCLE_BIN_ERROR': "Error accessing Recycle Bin: {error}. Ensure AD Recycle Bin is enabled.",
    'NO_DELETED_OBJECTS': "No deleted objects found in Recycle Bin",
    'MULTIPLE_MATCHES': "Multiple objects found matching '{query}'. Be more specific.",
    'NO_MATCH': "No deleted object found matching '{query}'",
    'RESTORE_COMPLEX': "Restore failed. Use PowerShell: Restore-ADObject cmdlet for complex restores.",
    'TARGET_OU_NOT_FOUND': "Target OU not found: {dn}",
    'INVALID_TARGET_OU': "Invalid target OU: {error}",
    'OU_PATH_REQUIRED': "OU name not specified. Usage: :mkou <OU name>",
    'TARGET_REQUIRED': "Target OU not specified. Usage: :m <path>",
    'RESTORE_NAME_REQUIRED': "Object name not specified. Usage: :restore <name>",
    'ACCOUNT_NOT_LOCKED': "Account is not currently locked",
    'UNLOCK_SUCCESS': "Successfully unlocked user account",
    'UNLOCK_FAILED': "Failed to unlock account: {error}",
    'UNLOCK_USER_ONLY': "Unlock can only be performed on user accounts",
    'CREATE_USER_SUCCESS': "Successfully created user account",
    'CREATE_USER_FAILED': "Failed to create user account: {error}",
    'COPY_USER_SUCCESS': "Successfully copied user account",
    'COPY_USER_FAILED': "Failed to copy user account: {error}",
    'NO_TARGET_OU': "No target OU specified or selected",
}


# UI element IDs
UI_IDS = {
    'COMMAND_INPUT': 'command-input',
    'DETAILS_PANE': 'details-pane',
    'SEARCH_RESULTS_PANE': 'search-results-pane',
    'DIALOG': 'dialog',
    'DIALOG_BUTTONS': 'dialog-buttons',
    'QUESTION': 'question',
    'OU_DESCRIPTION': 'ou-description',
}


# File paths
PATHS = {
    'LAST_USER_FILE': 'last_user.txt',
    'CONFIG_FILE': 'config.ini',
    'STYLES_FILE': 'styles.tcss',
}
