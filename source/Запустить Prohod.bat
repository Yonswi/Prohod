@echo off
rem Starts Prohod without a console window. The app asks for admin rights itself.
rem Run from System32 so a planted pythonw next to this file is never picked up.
rem -I: isolated mode, Python ignores modules placed next to the script and PYTHON* variables.
set "PROHOD=%~dp0Prohod.pyw"
cd /d "%SystemRoot%\System32"
start "" pythonw -I "%PROHOD%"
