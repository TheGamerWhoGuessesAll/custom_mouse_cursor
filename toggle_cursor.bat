@echo off
if exist "C:\Users\zhiyu\miniconda3\python.exe" (
    "C:\Users\zhiyu\miniconda3\python.exe" "%~dp0toggle_cursor.py"
) else (
    python "%~dp0toggle_cursor.py"
)
