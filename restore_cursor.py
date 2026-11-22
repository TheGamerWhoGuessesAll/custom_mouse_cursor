import os
import json
import ctypes
from ctypes import wintypes
import winreg

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKUP_PATH = os.path.join(BASE_DIR, "cursor_backup.json")
STATE_PATH = os.path.join(BASE_DIR, "cursor_state.json")
REG_PATH = r"Control Panel\Cursors"

SPI_SETCURSORS = 0x0057
SPIF_UPDATEINIFILE = 0x01
SPIF_SENDWININICHANGE = 0x02


def main():
    if not os.path.exists(BACKUP_PATH):
        print(f"No backup found at {BACKUP_PATH}; clearing custom entries to Windows defaults.")
        defaults = ["Arrow", "Hand", "AppStarting", "Wait"]
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_SET_VALUE) as k:
            for name in defaults:
                winreg.SetValueEx(k, name, 0, winreg.REG_EXPAND_SZ, "")
    else:
        with open(BACKUP_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_SET_VALUE) as k:
            for name, info in data.items():
                winreg.SetValueEx(k, name, 0, info.get("type", winreg.REG_EXPAND_SZ), info["value"])
                print(f"Restored {name} -> {info['value']!r}")

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    user32.SystemParametersInfoW.argtypes = [
        wintypes.UINT,
        wintypes.UINT,
        wintypes.LPVOID,
        wintypes.UINT,
    ]
    user32.SystemParametersInfoW.restype = wintypes.BOOL
    ok = user32.SystemParametersInfoW(
        SPI_SETCURSORS, 0, None, 0
    )
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump({"enabled": False}, f)
    print("SystemParametersInfoW(SPI_SETCURSORS):", ok)


if __name__ == "__main__":
    main()
