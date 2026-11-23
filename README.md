# Cyber-Prism Custom Animated Windows Cursors & FX

Custom animated Windows cursors (`.ani`) and transparent `.gif` exports featuring an **infinite crystalline fractal zoom** interior, **Ice-White + Electric-Cyan** bevel, **Jet-Black** high-contrast border, and a slow **Cyber-Prism** shine sweep—paired with a lightweight click-through **Laser Targeter Trail + Neon Click Ripples + Cyber Click Sounds** overlay (`cursor_trail.pyw`).

## Included Cursors & Effects
- `cyber_prism_arrow.ani` — Normal pointer
- `cyber_prism_hand.ani` — Link / hand pointer
- `cyber_prism_ibeam.ani` — Text selection I-Beam
- `cyber_prism_busy.ani` — Busy / Wait / Crosshair
- `cursor_trail.pyw` — Click-through Win32 `gdiplus` overlay with:
  - **Laser Targeter Trail:** Glowing Electric-Cyan + Ice-White dotted tracking path (`0.26s` retraction).
  - **Neon Click Ripples + Radial Burst:** Expanding cyan/ice-white shockwave on left-click and violet/ice-white on right-click.
  - **Cyber Click Sounds:** Crisp synthesized crystal/mechanical click audio (`click_left.wav` / `click_right.wav`, auto-generated on launch).
  - **Auto-Hides In-Game:** Automatically clears and pauses whenever the Windows cursor is hidden (`GetCursorInfo`).

Each cursor also has `256x256` and `64x64` transparent `.gif` exports, plus `preview_light_and_dark.gif` showing visibility on both white and dark backgrounds.

---

## Setup on a New Windows Computer

### 1. Clone the repository
```powershell
git clone https://github.com/TheGamerWhoGuessesAll/custom_mouse_cursor.git
cd custom_mouse_cursor
```
*(Standard Python 3 on Windows is all you need to run both the cursors and the overlay.)*

### 2. Apply the cursors system-wide
```powershell
python apply_cursor.py
```
This backs up your original Windows cursor settings to `cursor_backup.json`, marks the scheme as custom (`Scheme Source = 0`), and activates the **Cyber-Prism** cursors immediately across Windows.

### 3. Start the Laser Targeter Trail + Click Ripples & Sounds
Double-click `start_trail.bat` (or run `python toggle_trail.py --restart`).

### 4. (Optional) Keep both active across every reboot / Windows update
Register both silent scripts in Windows Startup (`HKCU\...\Run`) so they persist across reboots with zero console windows:
```powershell
$pyw = (Get-Command pythonw).Source
$cursorScript = (Resolve-Path .\ensure_cursor_on_logon.pyw).Path
$trailScript = (Resolve-Path .\cursor_trail.pyw).Path
Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" -Name "CyberPrismCursor" -Value "`"$pyw`" `"$cursorScript`""
Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" -Name "CyberPrismTrail" -Value "`"$pyw`" `"$trailScript`""
```

---

## Daily Controls
- **Toggle Cursors (Custom ↔ Normal):** Double-click `toggle_cursor.bat` (or run `python toggle_cursor.py`).
- **Start / Stop / Toggle Click & Trail FX:** Double-click `start_trail.bat`, `stop_trail.bat`, or `toggle_trail.bat`.
- **Restore Original Windows Cursors:**
  ```powershell
  python restore_cursor.py
  ```
- **Regenerate Cursor Assets:** Requires `pillow` and `numpy`:
  ```powershell
  pip install pillow numpy
  python generate_cursors.py
  ```
