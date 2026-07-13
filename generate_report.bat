@echo off
chcp 65001 >nul
color 0a
@cd /d "%~dp0handler"
python main_menu.py
@cd /d "%~dp0"
pause