# replayer.py
import argparse
import json
import math
import platform
import queue
import sys
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import pyautogui


# Move the mouse to the top-left corner of the screen to stop the replay.
pyautogui.FAILSAFE = True

COMMAND_KEY = 'command' if platform.system() == 'Darwin' else 'win'


KEY_MAP = {
    'Key.enter': 'enter',
    'Key.tab': 'tab',
    'Key.space': 'space',
    'Key.backspace': 'backspace',
    'Key.delete': 'delete',
    'Key.esc': 'escape',
    'Key.shift': 'shift',
    'Key.shift_l': 'shift',
    'Key.shift_r': 'shiftright',
    'Key.ctrl_l': 'ctrl',
    'Key.ctrl_r': 'ctrlright',
    'Key.alt_l': 'alt',
    'Key.alt_r': 'altright',
    'Key.cmd': COMMAND_KEY,
    'Key.cmd_l': COMMAND_KEY,
    'Key.cmd_r': COMMAND_KEY,
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

REQUIRED_FIELDS = {
    'wait': ('seconds',),
    'type': ('text',),
    'click': ('x', 'y', 'button'),
    'drag': ('x1', 'y1', 'x2', 'y2', 'button'),
    'key_press': ('key',),
    'key_release': ('key',),
    'comment': (),
}


def load_actions(file_path):
    """Load and validate a JSON action file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            actions = json.load(file)
    except FileNotFoundError as error:
        raise ValueError(f"The file '{file_path}' was not found.") from error
    except PermissionError as error:
        raise ValueError(f"Permission was denied for '{file_path}'.") from error
    except json.JSONDecodeError as error:
        raise ValueError(
            f"Invalid JSON at line {error.lineno}, column {error.colno}: {error.msg}"
        ) from error
    except OSError as error:
        raise ValueError(f"Could not read '{file_path}': {error}") from error

    if not isinstance(actions, list):
        raise ValueError('The JSON file must contain a list of actions.')
    if not actions:
        raise ValueError('The JSON file does not contain any actions.')

    for index, action in enumerate(actions, start=1):
        if not isinstance(action, dict):
            raise ValueError(f'Action {index} must be a JSON object.')

        action_type = action.get('type')
        if action_type not in REQUIRED_FIELDS:
            raise ValueError(f'Action {index} has an unknown type: {action_type!r}.')

        missing = [field for field in REQUIRED_FIELDS[action_type] if field not in action]
        if missing:
            raise ValueError(f"Action {index} is missing: {', '.join(missing)}.")

        if ('time' in action and
                (not isinstance(action['time'], (int, float)) or
                 not math.isfinite(action['time']))):
            raise ValueError(f"Action {index} has a non-numeric 'time' value.")

        if action_type in ('wait', 'type'):
            field = 'seconds' if action_type == 'wait' else 'interval'
            value = action.get(field, 0.0)
            if (not isinstance(value, (int, float)) or
                    not math.isfinite(value) or value < 0):
                raise ValueError(f"Action {index} has an invalid '{field}' value.")

        if action_type in ('click', 'drag'):
            coordinate_fields = ('x', 'y') if action_type == 'click' else ('x1', 'y1', 'x2', 'y2')
            if any(not isinstance(action[field], (int, float)) or
                   not math.isfinite(action[field]) for field in coordinate_fields):
                raise ValueError(f'Action {index} has a non-numeric coordinate.')
            button = str(action['button']).split('.')[-1]
            if button not in ('left', 'middle', 'right'):
                raise ValueError(f'Action {index} has an unsupported mouse button: {button!r}.')

        if action_type in ('key_press', 'key_release'):
            if not isinstance(action['key'], str) or not action['key']:
                raise ValueError(f'Action {index} has an invalid key value.')

        if action_type == 'type' and not isinstance(action['text'], str):
            raise ValueError(f'Action {index} has a non-text value for typing.')

    return actions


def action_description(action):
    """Return a short description suitable for progress display."""
    action_type = action['type']
    if action_type == 'click':
        return f"Click at ({action['x']}, {action['y']})"
    if action_type == 'drag':
        return f"Drag to ({action['x2']}, {action['y2']})"
    if action_type == 'key_press':
        return f"Press {action['key']}"
    if action_type == 'key_release':
        return f"Release {action['key']}"
    if action_type == 'type':
        return f"Type {action['text']!r}"
    if action_type == 'wait':
        return f"Wait {action['seconds']} seconds"
    return action.get('text', 'Comment')


def interruptible_wait(seconds, stop_event):
    """Wait for a duration, returning True if Stop was requested."""
    deadline = time.monotonic() + seconds
    while True:
        pyautogui.failSafeCheck()
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return False
        wait_time = min(remaining, 0.1)
        if stop_event is None:
            time.sleep(wait_time)
        elif stop_event.wait(wait_time):
            return True


def release_modifier_keys():
    """Release modifiers even when the mouse is currently in the failsafe corner."""
    failsafe_was_enabled = pyautogui.FAILSAFE
    try:
        pyautogui.FAILSAFE = False
        for modifier in ('shift', 'shiftright', 'ctrl', 'ctrlright',
                         'alt', 'altright', 'win', 'command'):
            pyautogui.keyUp(modifier)
    finally:
        pyautogui.FAILSAFE = failsafe_was_enabled


def replay_action_list(actions, speed=1.0, max_delay=5.0, default_delay=0.05,
                       stop_event=None, progress_callback=None, countdown=True):
    """Replay validated actions and return 'finished', 'stopped', or 'failsafe'."""
    if not math.isfinite(speed) or speed <= 0:
        raise ValueError('Speed must be greater than zero.')
    if (not math.isfinite(max_delay) or not math.isfinite(default_delay) or
            max_delay < 0 or default_delay < 0):
        raise ValueError('Delay values cannot be negative.')

    try:
        if countdown:
            for seconds_left in (3, 2, 1):
                if progress_callback:
                    progress_callback(0, len(actions),
                                      f'Replay starts in {seconds_left}...')
                if interruptible_wait(1, stop_event):
                    return 'stopped'

        previous_time = None
        for index, action in enumerate(actions, start=1):
            if stop_event is not None and stop_event.is_set():
                return 'stopped'
            pyautogui.failSafeCheck()

            this_time = action.get('time')
            if this_time is not None and previous_time is not None:
                gap = max(0.0, min((this_time - previous_time) / speed, max_delay))
                if interruptible_wait(gap, stop_event):
                    return 'stopped'
            elif index > 1 and interruptible_wait(default_delay, stop_event):
                return 'stopped'
            if this_time is not None:
                previous_time = this_time

            if progress_callback:
                progress_callback(index, len(actions), action_description(action))

            action_type = action['type']
            if action_type == 'wait':
                if interruptible_wait(float(action['seconds']) / speed, stop_event):
                    return 'stopped'
            elif action_type == 'type':
                interval = float(action.get('interval', 0.0)) / speed
                for character in action['text']:
                    if stop_event is not None and stop_event.is_set():
                        return 'stopped'
                    pyautogui.write(character)
                    if interval and interruptible_wait(interval, stop_event):
                        return 'stopped'
            elif action_type == 'click':
                button = str(action['button']).split('.')[-1]
                pyautogui.moveTo(action['x'], action['y'], duration=0.15)
                pyautogui.click(x=action['x'], y=action['y'], button=button)
            elif action_type == 'drag':
                button = str(action['button']).split('.')[-1]
                pyautogui.moveTo(action['x1'], action['y1'], duration=0.15)
                pyautogui.dragTo(action['x2'], action['y2'], duration=0.3, button=button)
            elif action_type in ('key_press', 'key_release'):
                key = action['key']
                mapped_key = KEY_MAP.get(key, key.split('.')[-1]) if key.startswith('Key.') else key
                if action_type == 'key_press':
                    pyautogui.keyDown(mapped_key)
                else:
                    pyautogui.keyUp(mapped_key)
            # Comment actions intentionally perform no operation.

        return 'finished'
    except pyautogui.FailSafeException:
        return 'failsafe'
    finally:
        release_modifier_keys()


def replay_actions(file_path='recorded_actions.json', speed=1.0, max_delay=5.0,
                   default_delay=0.05):
    """Load an action file and replay it from the command line."""
    actions = load_actions(file_path)

    def show_progress(index, total, description):
        if index:
            print(f'[{index}/{total}] {description}')
        else:
            print(description)

    result = replay_action_list(
        actions,
        speed=speed,
        max_delay=max_delay,
        default_delay=default_delay,
        progress_callback=show_progress,
    )
    if result == 'finished':
        print('\nReplay finished.')
    elif result == 'failsafe':
        print('\nReplay stopped by the PyAutoGUI failsafe.')
    else:
        print('\nReplay stopped.')
    return result


class ReplayerGui:
    def __init__(self, root):
        self.root = root
        self.actions = None
        self.worker = None
        self.stop_event = threading.Event()
        self.messages = queue.Queue()

        root.title('PyAutoGUI Replayer')
        root.resizable(True, False)
        root.protocol('WM_DELETE_WINDOW', self.close)

        main = ttk.Frame(root, padding=12)
        main.grid(sticky='nsew')
        root.columnconfigure(0, weight=1)
        main.columnconfigure(1, weight=1)

        ttk.Label(main, text='Action file:').grid(row=0, column=0, sticky='w', padx=(0, 8))
        self.file_path = tk.StringVar()
        ttk.Entry(main, textvariable=self.file_path).grid(row=0, column=1, sticky='ew')
        self.browse_button = ttk.Button(main, text='Browse...', command=self.browse)
        self.browse_button.grid(row=0, column=2, padx=(8, 0))

        settings = ttk.Frame(main)
        settings.grid(row=1, column=0, columnspan=3, sticky='w', pady=(12, 0))
        self.speed = tk.StringVar(value='1.5')
        self.max_delay = tk.StringVar(value='5.0')
        self.default_delay = tk.StringVar(value='0.05')
        ttk.Label(settings, text='Speed:').grid(row=0, column=0)
        ttk.Entry(settings, textvariable=self.speed, width=7).grid(row=0, column=1, padx=(4, 14))
        ttk.Label(settings, text='Max delay:').grid(row=0, column=2)
        ttk.Entry(settings, textvariable=self.max_delay, width=7).grid(row=0, column=3, padx=(4, 14))
        ttk.Label(settings, text='Default delay:').grid(row=0, column=4)
        ttk.Entry(settings, textvariable=self.default_delay, width=7).grid(row=0, column=5, padx=(4, 0))

        self.progress = ttk.Progressbar(main, mode='determinate')
        self.progress.grid(row=2, column=0, columnspan=3, sticky='ew', pady=(14, 4))
        self.status = tk.StringVar(value='Choose a JSON action file.')
        ttk.Label(main, textvariable=self.status).grid(row=3, column=0, columnspan=3, sticky='w')

        safety_text = 'Safety: move the mouse to the top-left corner to stop replay immediately.'
        ttk.Label(main, text=safety_text, foreground='#8b0000').grid(
            row=4, column=0, columnspan=3, sticky='w', pady=(10, 0)
        )

        buttons = ttk.Frame(main)
        buttons.grid(row=5, column=0, columnspan=3, pady=(12, 0))
        self.play_button = ttk.Button(buttons, text='Play', command=self.play)
        self.play_button.grid(row=0, column=0, padx=4)
        self.stop_button = ttk.Button(buttons, text='Stop', command=self.stop, state='disabled')
        self.stop_button.grid(row=0, column=1, padx=4)

        self.root.after(100, self.process_messages)

    def browse(self):
        initial_directory = Path(self.file_path.get()).parent if self.file_path.get() else Path.cwd()
        chosen_path = filedialog.askopenfilename(
            title='Choose an action file',
            initialdir=str(initial_directory),
            filetypes=(('JSON files', '*.json'), ('All files', '*.*')),
        )
        if not chosen_path:
            return

        try:
            actions = load_actions(chosen_path)
        except ValueError as error:
            self.actions = None
            self.status.set('The selected file is invalid.')
            messagebox.showerror('Invalid action file', str(error))
            return

        self.file_path.set(chosen_path)
        self.actions = actions
        self.progress.configure(maximum=len(actions), value=0)
        self.status.set(f'Ready: {len(actions)} actions loaded.')

    def read_settings(self):
        try:
            speed = float(self.speed.get())
            max_delay = float(self.max_delay.get())
            default_delay = float(self.default_delay.get())
        except ValueError as error:
            raise ValueError('Speed and delay settings must be numbers.') from error

        if not math.isfinite(speed) or speed <= 0:
            raise ValueError('Speed must be greater than zero.')
        if (not math.isfinite(max_delay) or not math.isfinite(default_delay) or
                max_delay < 0 or default_delay < 0):
            raise ValueError('Delay settings cannot be negative.')
        return speed, max_delay, default_delay

    def play(self):
        if self.worker is not None and self.worker.is_alive():
            return

        try:
            actions = load_actions(self.file_path.get())
            speed, max_delay, default_delay = self.read_settings()
        except ValueError as error:
            messagebox.showerror('Cannot start replay', str(error))
            return

        self.actions = actions
        self.progress.configure(maximum=len(actions), value=0)
        self.stop_event.clear()
        self.set_running(True)
        self.status.set('Preparing replay...')
        self.worker = threading.Thread(
            target=self.run_replay,
            args=(actions, speed, max_delay, default_delay),
            daemon=True,
        )
        self.worker.start()

    def run_replay(self, actions, speed, max_delay, default_delay):
        try:
            result = replay_action_list(
                actions,
                speed=speed,
                max_delay=max_delay,
                default_delay=default_delay,
                stop_event=self.stop_event,
                progress_callback=lambda index, total, text: self.messages.put(
                    ('progress', index, total, text)
                ),
            )
            self.messages.put(('done', result))
        except Exception as error:
            self.messages.put(('error', str(error)))

    def stop(self):
        self.stop_event.set()
        self.stop_button.configure(state='disabled')
        self.status.set('Stopping...')

    def process_messages(self):
        try:
            while True:
                message = self.messages.get_nowait()
                if message[0] == 'progress':
                    _, index, total, text = message
                    self.progress.configure(value=index, maximum=total)
                    prefix = f'Action {index} of {total}: ' if index else ''
                    self.status.set(prefix + text)
                elif message[0] == 'done':
                    result = message[1]
                    self.set_running(False)
                    if result == 'finished':
                        self.progress.configure(value=self.progress['maximum'])
                        self.status.set('Replay complete.')
                    elif result == 'failsafe':
                        self.status.set('Stopped by the PyAutoGUI failsafe.')
                        messagebox.showwarning(
                            'Failsafe activated',
                            'Replay stopped because the mouse reached the top-left corner.',
                        )
                    else:
                        self.status.set('Replay stopped.')
                elif message[0] == 'error':
                    self.set_running(False)
                    self.status.set('Replay failed.')
                    messagebox.showerror('Replay error', message[1])
        except queue.Empty:
            pass

        if self.root.winfo_exists():
            self.root.after(100, self.process_messages)

    def set_running(self, running):
        normal_or_disabled = 'disabled' if running else 'normal'
        self.browse_button.configure(state=normal_or_disabled)
        self.play_button.configure(state=normal_or_disabled)
        self.stop_button.configure(state='normal' if running else 'disabled')

    def close(self):
        self.stop_event.set()
        self.root.destroy()


def run_gui():
    root = tk.Tk()
    ReplayerGui(root)
    root.mainloop()


def run_cli(arguments):
    parser = argparse.ArgumentParser(description='Replay recorded mouse and keyboard actions.')
    parser.add_argument('file', nargs='?', default='recorded_actions.json',
                        help='Path to the actions JSON file (default: recorded_actions.json)')
    parser.add_argument('--speed', type=float, default=1.5,
                        help='Playback speed multiplier (default: 1.5).')
    parser.add_argument('--max-delay', type=float, default=5.0,
                        help='Maximum reproduced delay in seconds (default: 5.0).')
    parser.add_argument('--default-delay', type=float, default=0.05,
                        help='Delay for files without timestamps (default: 0.05).')
    args = parser.parse_args(arguments)
    try:
        replay_actions(args.file, args.speed, args.max_delay, args.default_delay)
    except ValueError as error:
        parser.error(str(error))


if __name__ == '__main__':
    # Running without arguments (including from Thonny) opens the GUI. Supplying
    # command-line arguments retains the original command-line workflow.
    if len(sys.argv) == 1:
        run_gui()
    else:
        run_cli(sys.argv[1:])
