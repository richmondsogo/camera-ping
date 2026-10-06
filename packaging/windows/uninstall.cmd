@echo off
rem Camera Monitor - Windows Uninstall Launcher
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0uninstall.ps1" %*
exit /b %ERRORLEVEL%
