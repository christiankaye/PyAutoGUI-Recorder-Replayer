# recorder.py
import json
from pynput import mouse, keyboard

# This list will store all the recorded actions
recorded_actions = []

def on_click(x, y, button, pressed):
    """Callback function to handle mouse click events."""
    if pressed:
        action = {
            'type': 'click',
            'x': x,
            'y': y,
            'button': str(button)
        }
        recorded_actions.append(action)
        print(f"Recorded click at ({x}, {y}) with {button}")

def on_press(key):
    """Callback function to handle key press events."""
    try:
        action = {
            'type': 'key_press',
            'key': key.char
        }
        recorded_actions.append(action)
        print(f"Recorded key press: '{key.char}'")
    except AttributeError:
        action = {
            'type': 'key_press',
            'key': str(key)
        }
        recorded_actions.append(action)
        print(f"Recorded special key press: {key}")

    # Stop listener if the Escape key is pressed
    if key == keyboard.Key.esc:
        print("Stopping recorder...")
        mouse_listener.stop()       # <-- NEW: tell the mouse listener to stop too
        return False                # This stops the keyboard listener

def on_release(key):
    """Callback function to handle key release events."""
    try:
        action = {
            'type': 'key_release',
            'key': key.char
        }
    except AttributeError:
        action = {
            'type': 'key_release',
            'key': str(key)
        }
    recorded_actions.append(action)

# --- Main execution ---
print("Starting input recorder. Press 'Esc' to stop.")
print("Recording: mouse clicks and keyboard key presses/releases.")

# Set up listeners
mouse_listener = mouse.Listener(on_click=on_click)
key_listener = keyboard.Listener(on_press=on_press, on_release=on_release)

# Start listening in the background
mouse_listener.start()
key_listener.start()

# Wait for the listeners to stop (i.e., when 'Esc' is pressed)
mouse_listener.join()        # Now this WILL finish because we stopped it
key_listener.join()

# Save the recorded actions to a file
if recorded_actions:
    with open('recorded_actions.json', 'w') as f:
        json.dump(recorded_actions, f, indent=4)
    print(f"\nSuccessfully saved {len(recorded_actions)} actions to recorded_actions.json")
    print(f"  - Mouse clicks: {sum(1 for a in recorded_actions if a['type'] == 'click')}")
    print(f"  - Key presses:  {sum(1 for a in recorded_actions if a['type'] == 'key_press')}")
    print(f"  - Key releases: {sum(1 for a in recorded_actions if a['type'] == 'key_release')}")
else:
    print("No actions were recorded.")