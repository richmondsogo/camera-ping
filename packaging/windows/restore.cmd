@echo off
rem Camera Monitor - Database Restore Launcher
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0restore.ps1" %*
exit /b %ERRORLEVEL%
