# replayer.py
import pyautogui
import json
import time

# CRITICAL: PyAutoGUI's failsafe is enabled by default.
# Move the mouse to the top-left corner of the screen to stop the script.
pyautogui.FAILSAFE = True

# Map pynput key strings to PyAutoGUI key names
KEY_MAP = {
    'Key.enter': 'enter',
    'Key.tab': 'tab',
    'Key.space': 'space',
    'Key.backspace': 'backspace',
    'Key.delete': 'delete',
    'Key.esc': 'escape',
    'Key.shift': 'shift',
    'Key.shift_r': 'shiftright',
    'Key.ctrl_l': 'ctrl',
    'Key.ctrl_r': 'ctrlright',
    'Key.alt_l': 'alt',
    'Key.alt_r': 'altright',
    'Key.cmd': 'win',
    'Key.caps_lock': 'capslock',
    'Key.up': 'up',
    'Key.down': 'down',
    'Key.left': 'left',
    'Key.right': 'right',
    'Key.home': 'home',
    'Key.end': 'end',
    'Key.page_up': 'pageup',
    'Key.page_down': 'pagedown',
    'Key.f1': 'f1',
    'Key.f2': 'f2',
    'Key.f3': 'f3',
    'Key.f4': 'f4',
    'Key.f5': 'f5',
    'Key.f6': 'f6',
    'Key.f7': 'f7',
    'Key.f8': 'f8',
    'Key.f9': 'f9',
    'Key.f10': 'f10',
    'Key.f11': 'f11',
    'Key.f12': 'f12',
    'Key.insert': 'insert',
    'Key.print_screen': 'printscreen',
    'Key.menu': 'menu',
}

def replay_actions(file_path='recorded_actions.json'):
    """Reads actions from a file and replays them using pyautogui."""
    try:
        with open(file_path, 'r') as f:
            actions = json.load(f)
    except FileNotFoundError:
        print(f"Error: The file '{file_path}' was not found.")
        return

    print(f"Starting replay of {len(actions)} actions in 3 seconds...")
    print("Switch to your target window now!")
    time.sleep(3)

    for i, action in enumerate(actions):
        try:
            if action['type'] == 'click':
                button_name = action['button'].split('.')[-1]
                pyautogui.moveTo(action['x'], action['y'], duration=0.15)
                pyautogui.click(x=action['x'], y=action['y'], button=button_name)
                print(f"[{i+1}] Clicked {button_name} at ({action['x']}, {action['y']})")
                time.sleep(0.3)

            elif action['type'] == 'key_press':
                key = action['key']
                if key.startswith('Key.'):
                    # Map special key names
                    mapped = KEY_MAP.get(key, key.split('.')[-1])
                    pyautogui.keyDown(mapped)
                    print(f"[{i+1}] Pressed key: {mapped}")
                else:
                    # Regular character
                    pyautogui.keyDown(key)
                    print(f"[{i+1}] Pressed key: '{key}'")

            elif action['type'] == 'key_release':
                key = action['key']
                if key.startswith('Key.'):
                    mapped = KEY_MAP.get(key, key.split('.')[-1])
                    pyautogui.keyUp(mapped)
                else:
                    pyautogui.keyUp(key)

            # Small delay between actions for realism
            time.sleep(0.02)

        except Exception as e:
            print(f"[{i+1}] Error replaying action {action}: {e}")

    print("\nReplay finished.")

# --- Main execution ---
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Replay recorded mouse and keyboard actions.')
    parser.add_argument('file', nargs='?', default='recorded_actions.json',
                        help='Path to the actions JSON file (default: recorded_actions.json)')
    args = parser.parse_args()
    replay_actions(args.file)