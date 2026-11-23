import os
import sys
import time
import subprocess

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PID_PATH = os.path.join(BASE_DIR, "trail.pid")
TRAIL_SCRIPT = os.path.join(BASE_DIR, "cursor_trail.pyw")


def is_pid_running(pid: int) -> bool:
    res = subprocess.run(
        ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
        capture_output=True, text=True, check=False
    )
    return str(pid) in res.stdout


def stop_existing() -> bool:
    if os.path.exists(PID_PATH):
        try:
            pid = int(open(PID_PATH, "r", encoding="utf-8").read().strip())
            if is_pid_running(pid):
                subprocess.run(["taskkill", "/PID", str(pid), "/F"], check=False, capture_output=True)
                try:
                    os.remove(PID_PATH)
                except OSError:
                    pass
                return True
        except Exception:
            pass
        try:
            os.remove(PID_PATH)
        except OSError:
            pass
    return False


def start_new():
    pyw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    if not os.path.exists(pyw):
        pyw = r"C:\Users\zhiyu\miniconda3\pythonw.exe"
    subprocess.Popen([pyw, TRAIL_SCRIPT], creationflags=0x00000008)


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "--toggle"
    was_running = stop_existing()
    if mode == "--stop":
        print("Cursor trail STOPPED.")
        return
    if mode == "--restart":
        time.sleep(0.2)
        start_new()
        print("Cursor trail STARTED.")
        return
    # --toggle
    if was_running:
        print("Cursor trail STOPPED.")
    else:
        start_new()
        print("Cursor trail STARTED.")


if __name__ == "__main__":
    main()
