# recorder.py
import argparse
import json
import time
from pynput import mouse, keyboard

# Parse command-line arguments
parser = argparse.ArgumentParser(description='Record mouse and keyboard actions to a JSON file.')
parser.add_argument('file', nargs='?', default='recorded_actions.json',
                    help='Output JSON file name (default: recorded_actions.json)')
args = parser.parse_args()

# This list will store all the recorded actions
recorded_actions = []

# Minimum distance (pixels) between press and release to count as a drag
DRAG_THRESHOLD = 5

# Holds the position/button/time of the most recent mouse press
press_state = {}

# When True, input events are ignored (not recorded). Toggle with F9.
paused = False

def on_click(x, y, button, pressed):
    """Callback for mouse events.

    Records a press/release pair as either a 'click' (released near where it
    was pressed) or a 'drag' (released far from the press point).
    """
    if paused:
        return
    if pressed:
        # Remember where the press started; decide click vs drag on release.
        press_state['x'] = x
        press_state['y'] = y
        press_state['button'] = str(button)
        press_state['time'] = time.time()
    else:
        start_x = press_state.get('x', x)
        start_y = press_state.get('y', y)
        moved = abs(x - start_x) > DRAG_THRESHOLD or abs(y - start_y) > DRAG_THRESHOLD
        if moved:
            action = {
                'type': 'drag',
                'x1': start_x,
                'y1': start_y,
                'x2': x,
                'y2': y,
                'button': str(button),
                'time': time.time()
            }
            recorded_actions.append(action)
            print(f"Recorded drag from ({start_x}, {start_y}) to ({x}, {y}) with {button}")
        else:
            action = {
                'type': 'click',
                'x': x,
                'y': y,
                'button': str(button),
                'time': time.time()
            }
            recorded_actions.append(action)
            print(f"Recorded click at ({x}, {y}) with {button}")

def on_press(key):
    """Callback function to handle key press events."""
    global paused

    # Stop on Escape *before* recording, so the stop key isn't saved/replayed.
    if key == keyboard.Key.esc:
        print("Stopping recorder...")
        mouse_listener.stop()       # tell the mouse listener to stop too
        return False                # This stops the keyboard listener

    # Toggle pause with F9; the toggle key itself is never recorded.
    if key == keyboard.Key.f9:
        paused = not paused
        print("Recording PAUSED (press F9 to resume)." if paused
              else "Recording RESUMED.")
        return

    if paused:
        return

    # key.char is a printable character; it is None or missing for special keys.
    char = getattr(key, 'char', None)
    if char is not None:
        action = {
            'type': 'key_press',
            'key': char,
            'time': time.time()
        }
        recorded_actions.append(action)
        print(f"Recorded key press: '{char}'")
    else:
        action = {
            'type': 'key_press',
            'key': str(key),
            'time': time.time()
        }
        recorded_actions.append(action)
        print(f"Recorded special key press: {key}")

def on_release(key):
    """Callback function to handle key release events."""
    # Don't record the Escape release (it's the stop key) or the F9 toggle.
    if key == keyboard.Key.esc or key == keyboard.Key.f9:
        return

    if paused:
        return

    char = getattr(key, 'char', None)
    if char is not None:
        action = {
            'type': 'key_release',
            'key': char,
            'time': time.time()
        }
    else:
        action = {
            'type': 'key_release',
            'key': str(key),
            'time': time.time()
        }
    recorded_actions.append(action)

# --- Main execution ---
print("Starting input recorder. Press 'Esc' to stop, 'F9' to pause/resume.")
print("Recording: mouse clicks and keyboard key presses/releases.")

# Give the user 3 seconds to switch to the target window before recording.
print("Recording starts in 3 seconds... switch to your target window now!")
time.sleep(3)

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
    with open(args.file, 'w') as f:
        json.dump(recorded_actions, f, indent=4)
    print(f"\nSuccessfully saved {len(recorded_actions)} actions to {args.file}")
    print(f"  - Mouse clicks: {sum(1 for a in recorded_actions if a['type'] == 'click')}")
    print(f"  - Mouse drags:  {sum(1 for a in recorded_actions if a['type'] == 'drag')}")
    print(f"  - Key presses:  {sum(1 for a in recorded_actions if a['type'] == 'key_press')}")
    print(f"  - Key releases: {sum(1 for a in recorded_actions if a['type'] == 'key_release')}")
else:
    print("No actions were recorded.")