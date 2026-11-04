@echo off
rem Starts NIXYZ without a console window. The app asks for admin rights itself.
rem Run from System32 so a planted pythonw next to this file is never picked up.
rem -I: isolated mode, Python ignores modules placed next to the script and PYTHON* variables.
rem .build-venv has pywebview, so the app opens in its own window; system Python opens it in a browser.
set "NIXYZ=%~dp0NIXYZ.pyw"
set "PYW=pythonw"
if exist "%~dp0.build-venv\Scripts\pythonw.exe" set "PYW=%~dp0.build-venv\Scripts\pythonw.exe"
cd /d "%SystemRoot%\System32"
start "" "%PYW%" -I "%NIXYZ%"
