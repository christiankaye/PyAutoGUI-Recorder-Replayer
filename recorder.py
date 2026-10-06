# recorder.py
import json
import queue
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from pynput import keyboard, mouse


DRAG_THRESHOLD = 5


class RecorderGui:
    def __init__(self, root):
        self.root = root
        self.recorded_actions = []
        self.press_state = {}
        self.mouse_listener = None
        self.keyboard_listener = None
        self.recording = False
        self.paused = False
        self.starting = False
        self.countdown_job = None
        self.gui_bounds = (0, 0, 0, 0)
        self.state_lock = threading.Lock()
        self.messages = queue.Queue()

        root.title('PyAutoGUI Recorder')
        root.resizable(True, False)
        root.protocol('WM_DELETE_WINDOW', self.close)

        main = ttk.Frame(root, padding=12)
        main.grid(sticky='nsew')
        root.columnconfigure(0, weight=1)
        main.columnconfigure(1, weight=1)

        ttk.Label(main, text='Save as:').grid(row=0, column=0, sticky='w', padx=(0, 8))
        default_path = Path(__file__).resolve().with_name('recorded_actions.json')
        self.file_path = tk.StringVar(value=str(default_path))
        self.path_entry = ttk.Entry(main, textvariable=self.file_path)
        self.path_entry.grid(row=0, column=1, sticky='ew')
        self.browse_button = ttk.Button(main, text='Browse...', command=self.browse)
        self.browse_button.grid(row=0, column=2, padx=(8, 0))

        self.status = tk.StringVar(value='Ready to record.')
        ttk.Label(main, textvariable=self.status).grid(
            row=1, column=0, columnspan=3, sticky='w', pady=(12, 0)
        )

        instructions = 'F7: stop and save    F9: pause or resume'
        ttk.Label(main, text=instructions).grid(
            row=2, column=0, columnspan=3, sticky='w', pady=(4, 0)
        )

        buttons = ttk.Frame(main)
        buttons.grid(row=3, column=0, columnspan=3, pady=(12, 0))
        self.start_button = ttk.Button(buttons, text='Start Recording', command=self.start)
        self.start_button.grid(row=0, column=0, padx=4)
        self.stop_button = ttk.Button(
            buttons,
            text='Stop and Save',
            command=self.stop_and_save,
            state='disabled',
        )
        self.stop_button.grid(row=0, column=1, padx=4)

        self.root.after(100, self.process_messages)

    def browse(self):
        current_path = Path(self.file_path.get()) if self.file_path.get() else Path.cwd()
        chosen_path = filedialog.asksaveasfilename(
            title='Save recorded actions',
            initialdir=str(current_path.parent),
            initialfile=current_path.name,
            defaultextension='.json',
            filetypes=(('JSON files', '*.json'), ('All files', '*.*')),
        )
        if chosen_path:
            self.file_path.set(chosen_path)

    def validated_save_path(self):
        entered_path = self.file_path.get().strip()
        if not entered_path:
            raise ValueError('Choose a filename before starting the recorder.')

        save_path = Path(entered_path).expanduser()
        if save_path.suffix.lower() != '.json':
            save_path = save_path.with_suffix('.json')
        if not save_path.parent.exists():
            raise ValueError('The selected folder does not exist.')
        if not save_path.parent.is_dir():
            raise ValueError('The selected save location is not a folder.')
        if save_path.exists() and save_path.is_dir():
            raise ValueError('The selected filename is a folder.')

        self.file_path.set(str(save_path))
        return save_path

    def start(self):
        try:
            self.validated_save_path()
        except ValueError as error:
            messagebox.showerror('Cannot start recording', str(error))
            return

        self.recorded_actions = []
        self.press_state = {}
        self.starting = True
        self.set_active(True)
        self.update_gui_bounds()
        self.run_countdown(3)

    def run_countdown(self, seconds_left):
        if not self.starting:
            return
        if seconds_left > 0:
            self.status.set(f'Recording starts in {seconds_left}... switch to the target window.')
            self.countdown_job = self.root.after(
                1000,
                lambda: self.run_countdown(seconds_left - 1),
            )
            return

        self.countdown_job = None
        self.starting = False
        self.begin_listening()

    def update_gui_bounds(self):
        self.root.update_idletasks()
        left = self.root.winfo_rootx()
        top = self.root.winfo_rooty()
        right = left + self.root.winfo_width()
        bottom = top + self.root.winfo_height()
        self.gui_bounds = (left, top, right, bottom)

    def begin_listening(self):
        with self.state_lock:
            self.recording = True
            self.paused = False

        self.mouse_listener = mouse.Listener(on_click=self.on_click)
        self.keyboard_listener = keyboard.Listener(
            on_press=self.on_press,
            on_release=self.on_release,
        )
        self.mouse_listener.start()
        self.keyboard_listener.start()
        self.status.set('Recording... press F7 to stop and save, or F9 to pause.')

    def is_gui_coordinate(self, x, y):
        left, top, right, bottom = self.gui_bounds
        return left <= x <= right and top <= y <= bottom

    def on_click(self, x, y, button, pressed):
        with self.state_lock:
            if not self.recording or self.paused:
                return

            # Do not save clicks used to operate this recorder window.
            if self.is_gui_coordinate(x, y):
                self.press_state.clear()
                return

            if pressed:
                self.press_state = {
                    'x': x,
                    'y': y,
                    'button': str(button),
                }
                return

            start_x = self.press_state.get('x', x)
            start_y = self.press_state.get('y', y)
            button_name = self.press_state.get('button', str(button))
            self.press_state = {}
            moved = (
                abs(x - start_x) > DRAG_THRESHOLD or
                abs(y - start_y) > DRAG_THRESHOLD
            )
            if moved:
                action = {
                    'type': 'drag',
                    'x1': start_x,
                    'y1': start_y,
                    'x2': x,
                    'y2': y,
                    'button': button_name,
                    'time': time.time(),
                }
            else:
                action = {
                    'type': 'click',
                    'x': x,
                    'y': y,
                    'button': button_name,
                    'time': time.time(),
                }
            self.recorded_actions.append(action)

    def on_press(self, key):
        if key == keyboard.Key.f7:
            self.request_stop_from_listener()
            return False

        if key == keyboard.Key.f9:
            with self.state_lock:
                if not self.recording:
                    return
                self.paused = not self.paused
                self.press_state = {}
                paused = self.paused
            message = 'Recording paused. Press F9 to resume.' if paused else 'Recording resumed.'
            self.messages.put(('status', message))
            return

        with self.state_lock:
            if not self.recording or self.paused:
                return
            character = getattr(key, 'char', None)
            key_value = character if character is not None else str(key)
            self.recorded_actions.append({
                'type': 'key_press',
                'key': key_value,
                'time': time.time(),
            })

    def on_release(self, key):
        if key in (keyboard.Key.f7, keyboard.Key.f9):
            return

        with self.state_lock:
            if not self.recording or self.paused:
                return
            character = getattr(key, 'char', None)
            key_value = character if character is not None else str(key)
            self.recorded_actions.append({
                'type': 'key_release',
                'key': key_value,
                'time': time.time(),
            })

    def request_stop_from_listener(self):
        with self.state_lock:
            if not self.recording:
                return
            self.recording = False
        if self.mouse_listener is not None:
            self.mouse_listener.stop()
        self.messages.put(('stop',))

    def stop_and_save(self):
        if self.starting:
            self.cancel_countdown()
            self.status.set('Recording cancelled.')
            self.set_active(False)
            return True

        with self.state_lock:
            was_recording = self.recording
            self.recording = False
            actions = list(self.recorded_actions)

        if not was_recording and self.keyboard_listener is None:
            return True

        self.stop_listeners()

        if not actions:
            self.status.set('Stopped. No actions were recorded.')
            self.set_active(False)
            return True

        try:
            save_path = self.validated_save_path()
            with open(save_path, 'w', encoding='utf-8') as file:
                json.dump(actions, file, indent=4)
        except (OSError, ValueError) as error:
            self.status.set('Recording stopped, but the file could not be saved.')
            self.set_active(False)
            messagebox.showerror('Save failed', str(error))
            return False

        self.status.set(f'Saved {len(actions)} actions to {save_path.name}.')
        self.set_active(False)
        return True

    def stop_listeners(self):
        if self.mouse_listener is not None:
            self.mouse_listener.stop()
        if self.keyboard_listener is not None:
            self.keyboard_listener.stop()
        self.mouse_listener = None
        self.keyboard_listener = None
        with self.state_lock:
            self.paused = False
            self.press_state = {}

    def cancel_countdown(self):
        self.starting = False
        if self.countdown_job is not None:
            self.root.after_cancel(self.countdown_job)
            self.countdown_job = None

    def process_messages(self):
        try:
            while True:
                message = self.messages.get_nowait()
                if message[0] == 'status':
                    self.status.set(message[1])
                elif message[0] == 'stop':
                    self.stop_and_save()
        except queue.Empty:
            pass

        if self.root.winfo_exists():
            self.root.after(100, self.process_messages)

    def set_active(self, active):
        entry_state = 'disabled' if active else 'normal'
        self.path_entry.configure(state=entry_state)
        self.browse_button.configure(state=entry_state)
        self.start_button.configure(state=entry_state)
        self.stop_button.configure(state='normal' if active else 'disabled')

    def close(self):
        if self.starting:
            self.cancel_countdown()
            self.root.destroy()
            return
        if (self.recording or self.keyboard_listener is not None) and not self.stop_and_save():
            return
        self.stop_listeners()
        self.root.destroy()


def run_gui():
    root = tk.Tk()
    RecorderGui(root)
    root.mainloop()


if __name__ == '__main__':
    run_gui()
