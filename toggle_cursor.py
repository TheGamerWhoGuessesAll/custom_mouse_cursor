import os
import winreg
import apply_cursor
import restore_cursor

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REG_PATH = r"Control Panel\Cursors"


def is_custom_active() -> bool:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_READ) as k:
            val, _ = winreg.QueryValueEx(k, "Arrow")
            return os.path.normcase(BASE_DIR) in os.path.normcase(str(val))
    except FileNotFoundError:
        return False


def main():
    if is_custom_active():
        print("Custom cursor is active -> switching back to NORMAL Windows cursor...")
        restore_cursor.main()
    else:
        print("Normal cursor is active -> switching to CUSTOM Cyber-Prism cursor...")
        apply_cursor.apply_custom()


if __name__ == "__main__":
    main()
