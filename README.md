# GraceRosaryBoost - GrRB

Automates the use of Rosary Ring abilities in Benediction to quickly change crouch speed.

## Current build

- Roblox-aware overlay: keeps GrRB above Roblox while Roblox is focused.
- Optional **Follow Roblox** mode with five positions: top-left, top-right, bottom-left, bottom-right and center.
- Drag the window freely with the left mouse button.
- Position and settings are saved between launches.
- **Sorrow** theme keeps the original red rain style.
- Right-click or the ⋮ button opens settings.
- CPS can be changed from 1 to 100.

## Controls

- Mouse4 / Mouse5 selects the activation button.
- Right-click opens the menu.
- Use **Change Rosary key...** in the menu, then press the desired keyboard key. The choice is saved between launches.
- Left-drag moves the overlay.

> The old source referenced `SCAN_CODE` without defining it. The new build defines it explicitly so the value can be adjusted for the actual in-game binding.

## Build

The repository includes a GitHub Actions workflow that checks `main.py`, builds the Windows EXE with PyInstaller and uploads it as a workflow artifact.

## 🛠 Technical Stack

- **Language:** Python
- **Libraries:** Tkinter, pynput, threading, ctypes
- **Platform:** Windows

![Image](https://github.com/user-attachments/assets/9a15ad01-c9ad-4dfe-9cf2-0b7c232fdf01)
