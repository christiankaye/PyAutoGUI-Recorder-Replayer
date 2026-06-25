# 🖱️ Mouse Recorder & Replayer

Record and replay repetitive GUI tasks with Python.

## How It Works

- **Record** mouse and keyboard events using [`pynput`](https://pypi.org/project/pynput/) (background listener)
- **Replay** captured actions using [`PyAutoGUI`](https://pyautogui.readthedocs.io/)
- Actions (clicks, coordinates, keystrokes, mouse drags) are saved to a timestamped JSON file, then read back to replicate them on demand.

---

## Features

- **Pause/Resume Recording** — Press `F9` to pause recording; press `F9` again to resume.
- **3-Second Startup Delay** — Both the recorder and replayer give you 3 seconds to switch to the target window before recording or replaying begins.
- **ESC to Save** — Press `Esc` at any time during recording to stop and save your JSON file.
- **Customizable Speed** — Replay at double speed (or any multiplier) with the `--speed` flag.
- **Editable Output** — JSON files are human-readable; hand-edit them to insert full words, phrases, or adjust timings.

---

## Quick Start

### 1. Record a Test

```bash
python recorder.py test_run.json
```
Press **F9** to pause and resume recording. (Helpful when switching windows, looking for addresses, etc.)
Perform your actions. Press **F7** when done to save `test_run.json`.

### 2. Replay That Test

```bash
python replayer.py test_login.json
```

Play back at **2× speed**:

```bash
python replayer.py test_login.json --speed 2
```

---

## Tips & Notes

| Tip | Description |
|-----|-------------|
| 🎯 **Window setup** | After starting the script, quickly switch to the application you want to automate. |
| ✏️ **Edit recordings** | Open the generated `.json` file in any text editor to tweak keystrokes or insert pauses. |
| 🖥️ **No GUI?** | Open the scripts in [Thonny](https://thonny.org/) or any Python IDE for a very good graphical run/debug experience. |
| **Real World Use** | I use this tool to fill in my vehicle mileage on SAP / Concur.
---
## Credits

Inspired by Yemdi's tutorial:  
[Step by Step PyAutoGUI Tutorial](https://thethinkdrop.blogspot.com/2026/01/step-by-step-pyautogui-tutorial.html)
