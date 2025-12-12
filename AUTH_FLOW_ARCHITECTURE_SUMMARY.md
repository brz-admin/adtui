# Authentication Flow Architecture Summary

## Current Architecture Understanding

The application uses a **two-app architecture**:

### 1. LoginFlowApp
- Handles initial login process
- Shows login dialog
- Collects credentials
- Exits when login succeeds or fails

### 2. ADTUI (Main App)
- Main application interface
- Shows AD tree and details
- Handles all operations
- Should return to login when authentication fails

## Current Authentication Failure Flow

### Problem
When authentication fails in the main app, the login dialog is pushed but doesn't show properly because:
1. The main app is still running
2. The login dialog is pushed as a screen within the main app
3. The architecture expects separate app instances

### Current Implementation
```python
# In _on_authentication_failure()
self.push_screen(LoginDialog(self.ad_config))
```

This tries to show the login dialog within the main app, but the architecture expects the main app to exit and the login app to restart.

## Proposed Solutions

### Solution 1: Modify Architecture (Recommended)
**Change the main script to handle authentication failure by restarting login flow:**

```python
# In main script (adtui.py or entry point)
try:
    # Run main app
    main_app = ADTUI(username, password, ad_config)
    main_app.run()
except AuthenticationError:
    # Restart login flow
    login_app = LoginFlowApp()
    login_app.run()
```

**Pros:**
- Follows existing architecture pattern
- Clean separation between login and main app
- Proper screen transitions

**Cons:**
- Requires changes to main script
- More complex error handling

### Solution 2: Modify Auth Failure Handler (Current Approach)
**Make the auth failure handler exit the main app:**

```python
# In _on_authentication_failure()
self.exit()  # Exit main app
# This would need the main script to catch and restart login
```

**Pros:**
- Minimal changes to auth failure handler
- Follows existing exit pattern

**Cons:**
- Requires main script changes
- Might lose application state

### Solution 3: Use Modal Dialog (Simpler but Limited)
**Show login dialog as a modal within main app:**

```python
# In _on_authentication_failure()
# Clear main interface first
self.clear_main_interface()
# Then show login dialog
self.push_screen(LoginDialog(self.ad_config))
```

**Pros:**
- No architecture changes needed
- Simple to implement

**Cons:**
- Might not match expected UX
- Could have screen transition issues

## Recommended Approach

### Short-Term Fix (Quick Implementation)
1. **Modify auth failure handler** to exit main app:
   ```python
   def _on_authentication_failure(self):
       self.notify("Authentication failed. Please check your credentials.", severity="error")
       self.exit()  # Exit main app to trigger login restart
   ```

2. **Modify main script** to catch exit and restart login:
   ```python
   try:
       main_app.run()
   except Exception:
       # Restart login flow
       login_app = LoginFlowApp()
       login_app.run()
   ```

### Long-Term Fix (Proper Architecture)
1. **Create proper authentication error exception**:
   ```python
   class AuthenticationError(Exception):
       pass
   ```

2. **Raise exception in auth failure handler**:
   ```python
   def _on_authentication_failure(self):
       self.notify("Authentication failed. Please check your credentials.", severity="error")
       raise AuthenticationError("Authentication failed")
   ```

3. **Handle exception in main script**:
   ```python
   try:
       main_app.run()
   except AuthenticationError:
       # Clean up and restart login
       login_app = LoginFlowApp()
       login_app.run()
   ```

## Current Debug Logging

The application now has debug logging to help diagnose the issue:

```
DEBUG: Triggering auth failure callback
DEBUG: _on_authentication_failure called
DEBUG: About to push LoginDialog
DEBUG: LoginDialog pushed
```

If these messages appear but the login dialog doesn't show, it confirms that the dialog is being pushed but not displayed properly due to the architecture mismatch.

## Next Steps

1. **Check debug logs** to confirm the flow
2. **Choose an approach** based on architecture preferences
3. **Implement the fix** at the appropriate level
4. **Test the solution** with wrong credentials

## Summary

The authentication failure handling needs to be aligned with the application's two-app architecture. The current approach of pushing a login dialog within the main app doesn't work well with the expected flow. The recommended solution is to exit the main app and restart the login flow when authentication fails, which requires coordination between the auth failure handler and the main script.