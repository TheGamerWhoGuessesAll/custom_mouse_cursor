@echo off
if exist "C:\Users\zhiyu\miniconda3\python.exe" (
    "C:\Users\zhiyu\miniconda3\python.exe" "%~dp0toggle_trail.py" --restart
) else (
    python "%~dp0toggle_trail.py" --restart
)
