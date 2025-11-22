# ADTUI Commands Reference

## Object Management Commands

### Search
```
:s <query>
```
Search for objects by Common Name (cn) or sAMAccountName. Results will be displayed in the search results pane.

**Example:**
```
:s john
:s admin
:s testuser
```

### Delete Object
```
:delete
:del
```
Delete the currently selected object. A confirmation dialog will appear before deletion.

**Steps:**
1. Select an object (from tree or search results)
2. Press `:` to enter command mode
3. Type `delete` or `del`
4. Confirm or cancel in the dialog

**⚠️ Warning:** Deletion is permanent and cannot be undone!

### Move Object
```
:move <target_ou_dn>
:mv <target_ou_dn>
```
Move the currently selected object to a different Organizational Unit.

**Example:**
```
:move ou=NewUsers,ou=Employees,dc=example,dc=com
:mv ou=Disabled,dc=example,dc=com
```

**Steps:**
1. Select an object (from tree or search results)
2. Press `:` to enter command mode
3. Type `move` or `mv` followed by the target OU DN
4. Confirm or cancel in the dialog

### Help
```
:help
```
Display help information with all available commands.

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `:` | Enter command mode |
| `s` | Quick search (opens command mode with "s ") |
| `r` | Refresh current OU |
| `Esc` | Quit application |
| `t` | Test search (development) |

## Object Details

### User Objects (👤)
When you select a user, the details pane shows:
- **General Information:** Name, username, email, profile path, home directory
- **Account Status:** Disabled, locked, password expiration
- **Group Memberships:** List of groups the user belongs to
- **Last Password Change:** Date and time

### Group Objects (👥)
When you select a group, the details pane shows:
- **General Information:** Group name, description, type
- **Members:** List of all group members (name only, not full DN)
- **Member Of:** Parent groups this group belongs to

### Computer Objects (💻)
When you select a computer, the details pane shows:
- **General Information:** Computer name, DNS hostname
- **System Info:** Operating system and version

## Workflow Examples

### Example 1: Find and Delete a User
```
1. Press 's' to search
2. Type: s testuser
3. Click on the user in search results
4. Press ':' then type: delete
5. Confirm deletion in dialog
```

### Example 2: Move a User to Different OU
```
1. Navigate tree or search for user
2. Select the user
3. Press ':' then type: move ou=Archive,dc=company,dc=com
4. Confirm move in dialog
```

### Example 3: Search and View Details
```
1. Press 's' to search
2. Type: s john.doe
3. Click on result to view full details
4. View group memberships, account status, etc.
```

## Tips

- **DN Format:** When specifying target OUs for move operations, use the full Distinguished Name
- **Selection:** Always ensure an object is selected before using delete or move commands
- **Confirmation:** All destructive operations require confirmation
- **Refresh:** Use 'r' to refresh the tree after making changes
- **Search:** Search works on both cn and sAMAccountName fields

## Error Handling

The application will show notifications for:
- ✅ Success: Green notifications for successful operations
- ⚠️ Warning: Yellow notifications for invalid input or missing selections
- ❌ Error: Red notifications for LDAP errors or failed operations

If an operation fails, check:
1. You have proper permissions
2. The object exists and is not protected
3. The target OU exists (for move operations)
4. The DN syntax is correct
