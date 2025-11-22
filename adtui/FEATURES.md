# ADTUI - Advanced Features Documentation

## 🎉 Implemented Features

### 1. ✅ OU Creation (`:mkou`)
Create new Organizational Units with optional descriptions.

**Command:** `:mkou <path>`

**Examples:**
```
:mkou IT/Developers
:mkou Users/Contractors
:mkou Departments/Sales/Region1
```

**Features:**
- Interactive dialog for description
- Automatic path-to-DN conversion
- Validates parent OU existence
- Tracked in operation history for undo

---

### 2. ✅ OU Deletion (`:d`, `:del`)
Delete OUs and other objects with confirmation.

**Command:** `:d` or `:del`

**Features:**
- Works on any selected object (Users, Groups, Computers, OUs)
- Requires explicit confirmation
- Objects go to AD Recycle Bin (if enabled)
- Tracked in operation history

---

### 3. ✅ OU Moving (`:m`)
Move OUs within the directory tree, just like moving users/groups.

**Command:** `:m <target_path>`

**Examples:**
```
:m IT/Archive
:m Departments/Old_Structure
```

**Features:**
- Same autocomplete as user/group moves
- Works on any object type
- Validates target OU exists
- Tracked for undo functionality

---

### 4. ✅ Account Expiry Alerts
Automatic alerts for expiring accounts displayed in user details.

**Alert Levels:**
- 🔴 **RED BOLD:** Account already expired
- 🟡 **YELLOW BOLD:** Expires within 7 days
- 🟡 **YELLOW:** Expires within 30 days

**Location:** User Details Pane (automatic when viewing a user)

**Example Output:**
```
⚠ ACCOUNT EXPIRED 5 days ago!
⚠ Account expires in 3 days!
⚠ Account expires in 15 days
```

---

### 5. ✅ Password Expiry Alerts
Automatic alerts for expiring passwords displayed in user details.

**Alert Levels:**
- 🔴 **RED BOLD:** Password already expired
- 🟡 **YELLOW BOLD:** Expires within 7 days
- 🟡 **YELLOW:** Expires within 14 days

**Calculation:** Based on pwdLastSet + domain max password age (default: 42 days)

**Example Output:**
```
⚠ PASSWORD EXPIRED 12 days ago!
⚠ Password expires in 5 days!
⚠ Password expires in 10 days
```

**Note:** For accurate calculation, domain password policy should be queried (currently uses default 42 days).

---

### 6. ✅ Undo Changes (`:undo`, `:u`)
Undo recent operations with operation history tracking.

**Command:** `:undo` or `:u`

**What Can Be Undone:**
- ✅ OU Creation → Deletes the created OU
- ✅ Move Operations → Moves object back to original location
- ⚠️ Delete Operations → Can't truly undo, but directs to Recycle Bin

**Features:**
- Tracks last 50 operations
- Shows confirmation dialog before undo
- Provides context about what will be undone
- Removes undone operation from history

**Tracked Operations:**
1. **create_ou** - Creating an OU
2. **move** - Moving any object
3. **delete** - Deleting any object (for reference only)

**Example:**
```
:mkou IT/NewDept           # Creates OU
:undo                      # Deletes IT/NewDept

:m Users/Archive           # Moves selected user
:undo                      # Moves user back

:d                         # Deletes object
:undo                      # Shows message about recycle bin
```

---

### 7. ✅ AD Recycle Bin Integration (`:recycle`, `:restore`)

#### View Recycle Bin (`:recycle` or `:rb`)
Display all deleted objects in the AD Recycle Bin.

**Command:** `:recycle` or `:rb`

**Features:**
- Shows deleted users, groups, computers, OUs
- Displays deletion timestamp
- Lists objects in search results pane
- Requires AD Recycle Bin to be enabled on domain

**Output:**
```
👤 [Deleted] John Doe (2024-01-15 14:30:00)
👥 [Deleted] Sales Team (2024-01-14 09:15:00)
📁 [Deleted] Old OU (2024-01-13 16:45:00)
```

#### Restore Deleted Objects (`:restore`)
Restore objects from the AD Recycle Bin.

**Command:** `:restore <name>`

**Examples:**
```
:restore John
:restore SalesTeam
:restore OldOU
```

**Features:**
- Searches for matching deleted objects
- Shows confirmation dialog
- Restores to original location (if possible)
- Handles complex restores

**Important Notes:**
- ⚠️ AD Recycle Bin must be enabled on your domain
- ⚠️ Complex restores may require PowerShell `Restore-ADObject` cmdlet
- ⚠️ Requires appropriate AD permissions

**To Enable AD Recycle Bin (Domain Admin required):**
```powershell
Enable-ADOptionalFeature -Identity 'Recycle Bin Feature' `
  -Scope ForestOrConfigurationSet `
  -Target 'yourdomain.com'
```

---

## 🔄 Complete Command Reference

### Object Management
| Command | Description | Example |
|---------|-------------|---------|
| `/<query>` | Search (vim-style) | `/john.doe` |
| `:s <query>` | Search by cn or sAMAccountName | `:s admin` |
| `:d`, `:del` | Delete selected object | `:d` |
| `:m <path>` | Move with autocomplete | `:m Users/IT/` |
| `:move <path>` | Same as `:m` | `:move IT/Archive` |

### OU Management
| Command | Description | Example |
|---------|-------------|---------|
| `:mkou <path>` | Create new OU | `:mkou IT/Dev` |
| `:createou <path>` | Same as `:mkou` | `:createou Sales/Region2` |

### History & Recovery
| Command | Description | Example |
|---------|-------------|---------|
| `:undo`, `:u` | Undo last operation | `:undo` |
| `:recycle`, `:rb` | View Recycle Bin | `:recycle` |
| `:restore <name>` | Restore deleted object | `:restore UserName` |

### Help
| Command | Description |
|---------|-------------|
| `:help` | Show all commands |

---

## 📊 Features Matrix

| Feature | Status | Notes |
|---------|--------|-------|
| OU Creation | ✅ Full | With description support |
| OU Deletion | ✅ Full | With confirmation |
| OU Moving | ✅ Full | With autocomplete |
| Account Expiry Alerts | ✅ Full | 7/30 day warnings |
| Password Expiry Alerts | ✅ Full | 7/14 day warnings |
| Undo Changes | ✅ Partial | Move & Create only |
| Recycle Bin View | ✅ Full | Requires AD RB enabled |
| Recycle Bin Restore | ⚠️ Limited | Complex cases need PowerShell |

---

## ⚠️ Important Limitations & Requirements

### AD Recycle Bin
The Recycle Bin features require:
1. **AD Recycle Bin enabled** on your domain (Server 2008 R2+)
2. **Proper permissions** to view and restore deleted objects
3. **Forest functional level** of Windows Server 2008 R2 or higher

If Recycle Bin is not enabled:
- Deleted objects are permanently removed
- `:recycle` command will show an error
- `:restore` will not work

### Undo Limitations
- **Delete operations cannot be truly undone** without Recycle Bin
- Only last 50 operations are tracked
- History is lost when application closes
- Some complex operations may not be fully reversible

### Password Expiry Calculation
- Currently uses default 42-day policy
- Should ideally query domain password policy
- Password expiry dates are estimates

### Restore Complex Objects
Some objects may be too complex to restore via LDAP:
- Objects with many child objects
- Objects with complex security descriptors
- Cross-domain references

For these cases, use PowerShell:
```powershell
Get-ADObject -Filter {Name -eq "ObjectName"} -IncludeDeletedObjects | Restore-ADObject
```

---

## 🎯 Usage Workflows

### Creating and Managing OUs
```bash
# Create a new OU structure
:mkou IT
:mkou IT/Developers
:mkou IT/Support
:mkou IT/Management

# Oops, wrong structure - undo
:undo
:undo
:undo

# Delete an OU (select it first)
<select OU in tree>
:d
```

### Recovering Deleted Objects
```bash
# Accidentally deleted a user
<select user>
:d
<confirm>

# Oh no! Let's restore it
:recycle                    # View deleted objects
:restore username           # Restore by name
```

### Checking Account Health
```bash
# Search for a user
/john.doe

# Select user from results
# Details pane automatically shows:
# - Password expiry warnings
# - Account expiry warnings
# - Account status
```

### Moving with Undo Safety Net
```bash
# Move a user to wrong OU
<select user>
:m IT/Wrong_Dept/
<confirm>

# Undo the move
:undo
<confirm>

# User is back in original location
```

---

## 🔐 Required Permissions

To use all features, your AD account needs:

### Basic Operations
- Read permissions on AD objects
- Search permissions

### Modify Operations
- Modify permissions on target objects
- Create/Delete permissions on OUs

### Recycle Bin
- "List Contents" on Deleted Objects container
- "Restore Deleted Objects" extended right

### Undo Operations
- Same permissions as original operation

---

## 🐛 Troubleshooting

### "Recycle Bin not accessible"
- Check if AD Recycle Bin is enabled
- Verify you have permissions to view deleted objects
- Ensure domain functional level is adequate

### "Cannot restore object"
- Some objects require PowerShell for complex restores
- Check if object has child objects
- Verify target location still exists

### "Undo failed"
- Target location may have been deleted
- Permissions may have changed
- Object may have been modified by another admin

### Password/Account expiry dates seem wrong
- Application uses estimated policy (42 days default)
- Domain policy may be different
- Check actual domain password policy with:
  ```powershell
  Get-ADDefaultDomainPasswordPolicy
  ```

---

## 📝 Future Enhancements

Possible future improvements:
1. Query actual domain password policy
2. Persistent operation history (save to file)
3. More granular undo levels
4. Bulk operations with undo support
5. Export/Import undo history
6. Computer account expiry alerts

---

## 🎓 Tips & Best Practices

1. **Always check Recycle Bin** before panicking about deletions
2. **Use undo immediately** - operation history is limited
3. **Test complex operations** on test OUs first
4. **Monitor expiry alerts regularly** to prevent account lockouts
5. **Keep PowerShell handy** for complex restore scenarios
6. **Document major changes** outside the application
7. **Verify undo success** after using :undo command

---

## 📞 Command Quick Reference Card

```
SEARCH:         /query      :s query
DELETE:         :d          :del
MOVE:           :m path     :move path
CREATE OU:      :mkou path
UNDO:           :u          :undo
RECYCLE BIN:    :rb         :recycle
RESTORE:        :restore name
HELP:           :help
```

---

**Version:** 2.0  
**Last Updated:** 2024  
**Requires:** Windows Server 2008 R2+ (for Recycle Bin features)
