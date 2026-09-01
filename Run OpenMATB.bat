@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
set "LAUNCHER=%SCRIPT_DIR%launcher.py"
set "EXIT_CODE=9009"

if exist "%SCRIPT_DIR%.venv\Scripts\python.exe" (
    "%SCRIPT_DIR%.venv\Scripts\python.exe" "%LAUNCHER%"
    set "EXIT_CODE=%ERRORLEVEL%"
    goto done
)

if defined CONDA_PREFIX if exist "%CONDA_PREFIX%\python.exe" (
    "%CONDA_PREFIX%\python.exe" "%LAUNCHER%"
    set "EXIT_CODE=%ERRORLEVEL%"
    goto done
)

if exist "%USERPROFILE%\anaconda3\python.exe" (
    "%USERPROFILE%\anaconda3\python.exe" "%LAUNCHER%"
    set "EXIT_CODE=%ERRORLEVEL%"
    goto done
)

if exist "%USERPROFILE%\miniconda3\python.exe" (
    "%USERPROFILE%\miniconda3\python.exe" "%LAUNCHER%"
    set "EXIT_CODE=%ERRORLEVEL%"
    goto done
)

if exist "%USERPROFILE%\Anaconda3\python.exe" (
    "%USERPROFILE%\Anaconda3\python.exe" "%LAUNCHER%"
    set "EXIT_CODE=%ERRORLEVEL%"
    goto done
)

if exist "%USERPROFILE%\Miniconda3\python.exe" (
    "%USERPROFILE%\Miniconda3\python.exe" "%LAUNCHER%"
    set "EXIT_CODE=%ERRORLEVEL%"
    goto done
)

where python >nul 2>nul
if %ERRORLEVEL%==0 (
    python "%LAUNCHER%"
    set "EXIT_CODE=%ERRORLEVEL%"
    goto done
)

where python3 >nul 2>nul
if %ERRORLEVEL%==0 (
    python3 "%LAUNCHER%"
    set "EXIT_CODE=%ERRORLEVEL%"
    goto done
)

where py >nul 2>nul
if %ERRORLEVEL%==0 (
    py -3 "%LAUNCHER%"
    set "EXIT_CODE=%ERRORLEVEL%"
    goto done
)

echo.
echo Could not find a Python interpreter.
echo Tried:
echo   1. %SCRIPT_DIR%.venv\Scripts\python.exe
echo   2. %%CONDA_PREFIX%%\python.exe
echo   3. %%USERPROFILE%%\anaconda3\python.exe
echo   4. %%USERPROFILE%%\miniconda3\python.exe
echo   5. %%USERPROFILE%%\Anaconda3\python.exe
echo   6. %%USERPROFILE%%\Miniconda3\python.exe
echo   7. python
echo   8. python3
echo   9. py -3
echo.
echo Please install Python or create the .venv for OpenMATB.

goto end

:done
echo.
echo Launcher finished with exit code %EXIT_CODE%.

:end
pause
endlocal & exit /b %EXIT_CODE%
