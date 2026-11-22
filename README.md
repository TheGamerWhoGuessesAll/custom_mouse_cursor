# Cyber-Prism Custom Animated Windows Cursors

Custom animated Windows cursors (`.ani`) and transparent `.gif` exports featuring an **infinite crystalline fractal zoom** interior, **Ice-White + Electric-Cyan** bevel, **Jet-Black** high-contrast border, and a slow **Cyber-Prism** shine sweep.

## Included Cursors
- `cyber_prism_arrow.ani` — Normal pointer
- `cyber_prism_hand.ani` — Link / hand pointer
- `cyber_prism_ibeam.ani` — Text selection I-Beam
- `cyber_prism_busy.ani` — Busy / Wait / Crosshair

Each cursor also has `256x256` and `64x64` transparent `.gif` exports, plus `preview_light_and_dark.gif` showing visibility on both white and dark backgrounds.

---

## Setup on a New Windows Computer

### 1. Clone the repository
```powershell
git clone https://github.com/TheGamerWhoGuessesAll/custom_mouse_cursor.git
cd custom_mouse_cursor
```
*(No extra Python packages are needed just to apply the pre-built `.ani` cursors—only standard Python 3 on Windows.)*

### 2. Apply the cursors system-wide
```powershell
python apply_cursor.py
```
This backs up your original Windows cursor settings to `cursor_backup.json`, marks the scheme as custom (`Scheme Source = 0`), and activates the **Cyber-Prism** cursors immediately across Windows.

### 3. (Optional) Keep it active across every reboot / Windows update
Register the silent logon script (`ensure_cursor_on_logon.pyw`) in Windows Startup so it re-verifies your cursors on every sign-in without showing a console window:
```powershell
$pyw = (Get-Command pythonw).Source
$script = (Resolve-Path .\ensure_cursor_on_logon.pyw).Path
Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" -Name "CyberPrismCursor" -Value "`"$pyw`" `"$script`""
```

---

## Daily Controls
- **1-Click Toggle (Custom ↔ Normal):** Double-click `toggle_cursor.bat` (or run `python toggle_cursor.py`).
- **Restore Original Windows Cursors:**
  ```powershell
  python restore_cursor.py
  ```
- **Regenerate / Customize Assets:** Requires `pillow` and `numpy`:
  ```powershell
  pip install pillow numpy
  python generate_cursors.py
  ```
