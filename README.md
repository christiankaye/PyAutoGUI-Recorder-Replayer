Mouse Recorder & Replayer

Record and replay repetitive GUI tasks with Python.

Uses pynput to listen for mouse/keyboard events  
Uses PyAutoGUI to replay recorded actions  
Actions (clicks, coordinates, keystrokes, mouse drags,) are saved to a file, then read back to replicate them on demand

Recorder: Press F9 to pause, F9 again to resume recording
Replayer and Recorder: 3 second delay for time to move window out of the way
Captures your mouse clicks and keystrokes via background pynput

Record a test (creates a time-stamped json file):
Example command: python recorder.py test_login.json
Then perform your actions and press Esc to save.

Replay that same test:
Example command: python replayer.py test_login.json
Modifier: --speed 2 to play back at double speed

Note: ESC stops the recording and creates the .json file
Hand edit your JSON to insert whole words/phrases

Credit to Yemdi for the original inspiration: 
https://thethinkdrop.blogspot.com/2026/01/step-by-step-pyautogui-tutorial.html
