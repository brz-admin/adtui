# Authentication Callback Timing Fix Summary

## Problem Identified

The authentication failure callback was not being set early enough, causing the issue:
```
ERROR:services.connection_manager:DEBUG: No auth failure callback set
```

This happened because:
1. Connection manager was created
2. Initial connection attempt was made
3. If connection failed, callback wasn't set yet (set in `_initialize_services()`)
4. System fell back to reconnecting instead of showing login dialog

## Solution Implemented

**Moved the auth failure callback setup to occur immediately after connection manager creation:**

```python
# Before (in _initialize_services())
self.connection_manager.set_auth_failure_callback(self._on_authentication_failure)

# After (immediately after creation)
self.connection_manager = create_connection_manager(username, password, ad_config)
self.connection_manager.set_auth_failure_callback(self._on_authentication_failure)  # Set immediately
self._initialize_services()
```

## Changes Made

### File: `adtui/adtui.py`

**Location**: In the `__init__` method where connection manager is created

**Change**: Moved auth failure callback setup before `_initialize_services()`

## Expected Behavior After Fix

### Before Fix
1. User enters wrong credentials
2. Connection manager created
3. Initial connection fails
4. No auth callback set → System reconnects
5. User sees reconnection attempts instead of login dialog

### After Fix
1. User enters wrong credentials
2. Connection manager created
3. Auth callback set immediately
4. Initial connection fails
5. Auth callback triggered → Login dialog shown
6. User sees login dialog properly

## Debug Logging

The fix maintains all existing debug logging:
```
DEBUG: Triggering auth failure callback
DEBUG: _on_authentication_failure called
DEBUG: Exiting main app to restart login flow
```

## Files Modified

- `adtui/adtui.py`: Moved auth failure callback setup to occur immediately after connection manager creation

## Testing

To verify the fix:
1. Run application with wrong credentials
2. Check logs for:
   - No "DEBUG: No auth failure callback set" message
   - Proper auth failure callback triggering
   - Login dialog showing correctly
3. Verify authentication failure flow works as expected

## Summary

This fix ensures the auth failure callback is available immediately, even if the initial connection fails. The callback is now set at the earliest possible moment after connection manager creation, preventing the "No auth failure callback set" issue and ensuring proper login dialog display on authentication failures.