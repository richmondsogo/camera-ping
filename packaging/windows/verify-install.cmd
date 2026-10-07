@echo off
rem Camera Monitor - Installation Verification Suite Launcher
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0verify-install.ps1" %*
exit /b %ERRORLEVEL%
