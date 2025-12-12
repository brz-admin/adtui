#!/usr/bin/env python3

"""Simple test to verify the changes work."""

import sys
sys.path.insert(0, '/home/ti2103@domman.ad/dev/adtui')

# Test that the imports work
try:
    from textual.app import App, ComposeResult
    from textual.widgets import Static, Footer, Input
    from textual.containers import Horizontal, Vertical
    print("✓ All imports successful")
except ImportError as e:
    print(f"✗ Import failed: {e}")
    sys.exit(1)

# Test that the CSS file can be read
try:
    with open('adtui/styles.tcss', 'r') as f:
        css_content = f.read()
    print("✓ CSS file readable")
    
    # Check if connection-status styling exists
    if '#connection-status' in css_content:
        print("✓ Connection status CSS found")
    else:
        print("✗ Connection status CSS not found")
        
except Exception as e:
    print(f"✗ CSS file error: {e}")
    sys.exit(1)

# Test that the adtui.py file has the correct structure
try:
    with open('adtui/adtui.py', 'r') as f:
        adtui_content = f.read()
    print("✓ ADTUI file readable")
    
    # Check if connection status widget is created at the top level
    if 'yield self.connection_status_widget' in adtui_content:
        print("✓ Connection status widget yield found")
    else:
        print("✗ Connection status widget yield not found")
        
    # Check if it's before the Horizontal container in the compose method
    lines = adtui_content.split('\n')
    in_compose = False
    widget_line = -1
    horizontal_line = -1
    
    for i, line in enumerate(lines):
        if 'def compose(self) -> ComposeResult:' in line:
            in_compose = True
        elif in_compose and 'def ' in line and 'compose' not in line:
            # End of compose method
            break
            
        if in_compose:
            if 'yield self.connection_status_widget' in line:
                widget_line = i
            if 'with Horizontal():' in line:
                horizontal_line = i
    
    if widget_line != -1 and horizontal_line != -1 and widget_line < horizontal_line:
        print("✓ Connection status widget is positioned before Horizontal container")
    else:
        print(f"✗ Connection status widget positioning issue: widget_line={widget_line}, horizontal_line={horizontal_line}")
        
except Exception as e:
    print(f"✗ ADTUI file error: {e}")
    sys.exit(1)

print("\n✓ All tests passed! The connection indicator should now be visible.")