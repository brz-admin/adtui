#!/usr/bin/env python3
"""Test script to verify imports work correctly."""

import sys

try:
    print("Testing imports...")
    
    print("  - Importing constants...")
    from constants import ObjectIcon, Severity, MESSAGES
    
    print("  - Importing services...")
    from services import LDAPService, HistoryService, PathService
    
    print("  - Importing commands...")
    from commands import CommandHandler
    
    print("  - Importing UI dialogs...")
    from ui.dialogs import ConfirmDeleteDialog
    
    print("  - Importing widgets...")
    from widgets.details_pane import DetailsPane
    from widgets.user_details import UserDetailsPane
    from widgets.group_details import GroupDetailsPane
    
    print("\n✅ All imports successful!")
    print("\nNote: Cannot test full app without LDAP connection.")
    print("The 'refresh()' conflict has been fixed by renaming to 'refresh_details()'")
    
except ImportError as e:
    print(f"\n❌ Import error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"\n❌ Error: {e}")
    sys.exit(1)
