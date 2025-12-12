# Debug Logging Summary for Authentication Failure Diagnosis

## Problem Description

The authentication failure callback is not showing the login dialog as expected. To diagnose this issue, comprehensive debug logging has been added to track the authentication failure flow.

## Debug Logging Added

### 1. Main Application Auth Failure Handler (`adtui/adtui.py`)

**Location**: `_on_authentication_failure()` method

**Debug Logs Added**:
- `"DEBUG: _on_authentication_failure called"` - Confirms handler is called
- `"DEBUG: About to push LoginDialog"` - Confirms before dialog push
- `"DEBUG: LoginDialog pushed"` - Confirms after dialog push
- `"DEBUG: No AD config available"` - Helps diagnose missing config issues

### 2. Connection Manager Auth Trigger (`adtui/services/connection_manager.py`)

**Location**: `_trigger_auth_failure()` method

**Debug Logs Added**:
- `"DEBUG: Triggering auth failure callback"` - Confirms callback is triggered
- `"DEBUG: Auth failure callback completed"` - Confirms callback completed
- `"DEBUG: No auth failure callback set"` - Helps diagnose missing callback issues

## Expected Debug Output

### Successful Authentication Failure Flow
```
DEBUG: Triggering auth failure callback
DEBUG: _on_authentication_failure called
DEBUG: About to push LoginDialog
DEBUG: LoginDialog pushed
DEBUG: Auth failure callback completed
```

### Missing Callback Issue
```
DEBUG: No auth failure callback set
```

### Missing AD Config Issue
```
DEBUG: Triggering auth failure callback
DEBUG: _on_authentication_failure called
DEBUG: No AD config available
DEBUG: Auth failure callback completed
```

### Callback Exception Issue
```
DEBUG: Triggering auth failure callback
DEBUG: _on_authentication_failure called
[Exception traceback shown]
```

## Diagnosis Steps

### Step 1: Check if Auth Failure Callback is Set
- Look for `"DEBUG: No auth failure callback set"`
- If found: Connection manager was not properly initialized

### Step 2: Check if Auth Failure Handler is Called
- Look for `"DEBUG: _on_authentication_failure called"`
- If not found: Callback not triggered or exception occurred

### Step 3: Check if Login Dialog is Pushed
- Look for `"DEBUG: About to push LoginDialog"` and `"DEBUG: LoginDialog pushed"`
- If not found: Issue in auth failure handler before dialog push

### Step 4: Check for AD Configuration Issues
- Look for `"DEBUG: No AD config available"`
- If found: AD configuration not available when needed

### Step 5: Check for Exceptions
- Look for exception tracebacks in logs
- Identifies where the process is failing

## Files Modified for Debugging

- `adtui/adtui.py`: Added debug logging to `_on_authentication_failure()`
- `adtui/services/connection_manager.py`: Added debug logging to `_trigger_auth_failure()`

## Next Steps

1. **Run the application with wrong credentials**
2. **Check the logs for debug messages**
3. **Identify where the flow is breaking**
4. **Fix the specific issue** based on debug output

## Expected Resolution

Once the debug logs are analyzed, the specific issue preventing the login dialog from showing can be identified and fixed. The debug logging provides comprehensive coverage of the entire authentication failure flow, from error detection to login dialog display.

## Removal of Debug Logging

After the issue is resolved, the debug logging can be removed by:
1. Removing the `print()` statements from `adtui/adtui.py`
2. Removing the `logger.error("DEBUG:")` statements from `adtui/services/connection_manager.py`
3. The application will then return to normal operation without debug output

## Summary

This debug logging provides a systematic way to diagnose why the login dialog is not showing on authentication failure. By following the expected debug output flow, the exact point of failure can be identified and resolved.