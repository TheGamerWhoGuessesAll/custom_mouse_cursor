import os
import json
import ctypes
from ctypes import wintypes
import winreg

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKUP_PATH = os.path.join(BASE_DIR, "cursor_backup.json")
STATE_PATH = os.path.join(BASE_DIR, "cursor_state.json")
REG_PATH = r"Control Panel\Cursors"

CURSOR_MAP = {
    "Arrow": os.path.join(BASE_DIR, "cyber_prism_arrow.ani"),
    "Hand": os.path.join(BASE_DIR, "cyber_prism_hand.ani"),
    "Help": os.path.join(BASE_DIR, "cyber_prism_help.ani"),
    "NWPen": os.path.join(BASE_DIR, "cyber_prism_pen.ani"),
    "IBeam": os.path.join(BASE_DIR, "cyber_prism_ibeam.ani"),
    "AppStarting": os.path.join(BASE_DIR, "cyber_prism_busy.ani"),
    "Wait": os.path.join(BASE_DIR, "cyber_prism_busy.ani"),
    "Crosshair": os.path.join(BASE_DIR, "cyber_prism_crosshair.ani"),
    "SizeNS": os.path.join(BASE_DIR, "cyber_prism_sizens.ani"),
    "SizeWE": os.path.join(BASE_DIR, "cyber_prism_sizewe.ani"),
    "SizeNWSE": os.path.join(BASE_DIR, "cyber_prism_sizenwse.ani"),
    "SizeNESW": os.path.join(BASE_DIR, "cyber_prism_sizenesw.ani"),
    "SizeAll": os.path.join(BASE_DIR, "cyber_prism_sizeall.ani"),
    "UpArrow": os.path.join(BASE_DIR, "cyber_prism_uparrow.ani"),
    "No": os.path.join(BASE_DIR, "cyber_prism_no.ani"),
}

SPI_SETCURSORS = 0x0057


def backup_current_cursors():
    data = {}
    if os.path.exists(BACKUP_PATH):
        with open(BACKUP_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

    updated = False
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_READ) as k:
        for name in list(CURSOR_MAP.keys()) + ["", "Scheme Source"]:
            if name in data:
                continue
            try:
                val, reg_type = winreg.QueryValueEx(k, name)
                data[name] = {"value": val, "type": reg_type}
            except FileNotFoundError:
                data[name] = {"value": "", "type": winreg.REG_EXPAND_SZ}
            updated = True

    if updated or not os.path.exists(BACKUP_PATH):
        with open(BACKUP_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print(f"Updated cursor backup at {BACKUP_PATH}")


def reload_system_cursors():
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    user32.SystemParametersInfoW.argtypes = [
        wintypes.UINT,
        wintypes.UINT,
        wintypes.LPVOID,
        wintypes.UINT,
    ]
    user32.SystemParametersInfoW.restype = wintypes.BOOL
    ok = user32.SystemParametersInfoW(SPI_SETCURSORS, 0, None, 0)
    if not ok:
        raise ctypes.WinError(ctypes.get_last_error())


def apply_custom():
    for name, path in CURSOR_MAP.items():
        if not os.path.exists(path):
            raise FileNotFoundError(f"Missing cursor file for {name}: {path}")

    backup_current_cursors()

    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_SET_VALUE) as k:
        for name, path in CURSOR_MAP.items():
            winreg.SetValueEx(k, name, 0, winreg.REG_EXPAND_SZ, path)
            print(f"Set {name} -> {os.path.basename(path)}")
        # Mark as a user-custom scheme (Scheme Source = 0) so Windows never auto-resets on reboot/theme sync
        winreg.SetValueEx(k, "", 0, winreg.REG_SZ, "Cyber-Prism")
        winreg.SetValueEx(k, "Scheme Source", 0, winreg.REG_DWORD, 0)

    reload_system_cursors()
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump({"enabled": True}, f)
    print("Cyber-Prism cursors are now ACTIVE system-wide!")


if __name__ == "__main__":
    apply_custom()
