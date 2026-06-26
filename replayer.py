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

def replay_actions(file_path='recorded_actions.json', speed=1.0, max_delay=5.0,
                   default_delay=0.05):
    """Reads actions from a file and replays them using pyautogui.

    Delays for reliability:
      - If actions were recorded with a 'time' field, the real pause between
        consecutive actions is reproduced (so slow windows get the time they
        need), scaled by `speed` and capped at `max_delay` seconds.
      - A 'wait' action ({"type": "wait", "seconds": 2}) forces a strategic
        pause -- add these by hand after steps that trigger slow processes.
      - A 'type' action ({"type": "type", "text": "hello", "interval": 0.02})
        types a whole word/phrase -- add these by hand to enter looked-up text.
      - Without timestamps, a small fixed `default_delay` is used (legacy mode).
    """
    try:
        with open(file_path, 'r') as f:
            actions = json.load(f)
    except FileNotFoundError:
        print(f"Error: The file '{file_path}' was not found.")
        return

    print(f"Starting replay of {len(actions)} actions in 3 seconds...")
    print("Switch to your target window now!")
    time.sleep(3)

    prev_time = None
    for i, action in enumerate(actions):
        try:
            # --- Reliability delay: wait before performing this action ---
            this_time = action.get('time')
            if this_time is not None and prev_time is not None:
                # Reproduce the real gap the user left between actions.
                gap = (this_time - prev_time) / speed
                gap = max(0.0, min(gap, max_delay))
                if gap > 0:
                    time.sleep(gap)
            elif i > 0:
                # Legacy files with no timestamps: small fixed delay.
                time.sleep(default_delay)
            if this_time is not None:
                prev_time = this_time

            if action['type'] == 'wait':
                seconds = float(action.get('seconds', 1)) / speed
                print(f"[{i+1}] Waiting {seconds:.2f}s")
                time.sleep(seconds)

            elif action['type'] == 'type':
                # Type a whole word/phrase. Add these by hand to a JSON file,
                # e.g. {"type": "type", "text": "hello world", "interval": 0.02}
                text = action.get('text', '')
                interval = float(action.get('interval', 0.0)) / speed
                pyautogui.write(text, interval=interval)
                print(f"[{i+1}] Typed: {text!r}")

            elif action['type'] == 'click':
                button_name = action['button'].split('.')[-1]
                pyautogui.moveTo(action['x'], action['y'], duration=0.15)
                pyautogui.click(x=action['x'], y=action['y'], button=button_name)
                print(f"[{i+1}] Clicked {button_name} at ({action['x']}, {action['y']})")

            elif action['type'] == 'drag':
                button_name = action['button'].split('.')[-1]
                pyautogui.moveTo(action['x1'], action['y1'], duration=0.15)
                pyautogui.dragTo(action['x2'], action['y2'], duration=0.3, button=button_name)
                print(f"[{i+1}] Dragged {button_name} from ({action['x1']}, {action['y1']}) "
                      f"to ({action['x2']}, {action['y2']})")

            elif action['type'] == 'key_press':
                key = action['key']
                if not isinstance(key, str):
                    print(f"[{i+1}] Skipping key_press with no usable key value")
                    continue
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
                if not isinstance(key, str):
                    continue
                if key.startswith('Key.'):
                    mapped = KEY_MAP.get(key, key.split('.')[-1])
                    pyautogui.keyUp(mapped)
                else:
                    pyautogui.keyUp(key)

            elif action['type'] == 'comment':
                # Comments document a recording; nothing to replay.
                print(f"[{i+1}] # {action.get('text', '')}")

            else:
                # Unknown/typo'd action type: skip but report it so mistakes
                # in a hand-edited JSON file don't get silently dropped.
                print(f"[{i+1}] Skipping unknown action type: {action.get('type')!r}")

        except Exception as e:
            print(f"[{i+1}] Error replaying action {action}: {e}")

    # Safeguard: release any modifier keys that a missing key_release could
    # have left stuck (e.g. Shift held down makes numbers type as symbols).
    for mod in ('shift', 'shiftright', 'ctrl', 'ctrlright', 'alt', 'altright', 'win'):
        pyautogui.keyUp(mod)

    print("\nReplay finished.")

# --- Main execution ---
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Replay recorded mouse and keyboard actions.')
    parser.add_argument('file', nargs='?', default='recorded_actions.json',
                        help='Path to the actions JSON file (default: recorded_actions.json)')
    parser.add_argument('--speed', type=float, default=1.5,
                        help='Playback speed multiplier. >1 is faster, <1 is slower (default: 1.5).')
    parser.add_argument('--max-delay', type=float, default=5.0,
                        help='Cap on reproduced delay between actions, in seconds (default: 5.0).')
    parser.add_argument('--default-delay', type=float, default=0.05,
                        help='Fixed delay for legacy files without timestamps (default: 0.05).')
    args = parser.parse_args()
    replay_actions(args.file, speed=args.speed, max_delay=args.max_delay,
                   default_delay=args.default_delay)
