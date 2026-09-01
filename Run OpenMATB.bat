@echo off

setlocal

set SCRIPT_DIR=%~dp0

if exist "%SCRIPT_DIR%.venv\Scripts\python.exe" (

    "%SCRIPT_DIR%.venv\Scripts\python.exe" "%SCRIPT_DIR%launcher.py"

) else (

    python "%SCRIPT_DIR%launcher.py"

)

set EXIT_CODE=%ERRORLEVEL%

echo.

echo Launcher finished with exit code %EXIT_CODE%.

pause

endlocal & exit /b %EXIT_CODE%

