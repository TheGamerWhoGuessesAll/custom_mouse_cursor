import os
import json
import apply_cursor

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_PATH = os.path.join(BASE_DIR, "cursor_state.json")


def main():
    enabled = True
    if os.path.exists(STATE_PATH):
        try:
            with open(STATE_PATH, "r", encoding="utf-8") as f:
                enabled = bool(json.load(f).get("enabled", True))
        except Exception:
            enabled = True
    if enabled:
        apply_cursor.apply_custom()


if __name__ == "__main__":
    main()
