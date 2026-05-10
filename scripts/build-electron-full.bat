@echo off
REM Manatrix Studio - Complete Build Script with Backend Integration
REM This script prepares backend files and builds the Electron app

setlocal EnableDelayedExpansion

echo ========================================
echo Manatrix Studio - Full Build
echo ========================================
echo.

REM Get script directory
set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%.."
set "ELECTRON_DIR=%PROJECT_ROOT%\electron"

REM Change to project root
cd /d "%PROJECT_ROOT%"

echo [STEP 1] Preparing backend files...

REM Create electron/web directory if it doesn't exist
if not exist "%ELECTRON_DIR%\web" mkdir "%ELECTRON_DIR%\web"

REM Copy web files to electron/web (for asar unpacking)
echo   - Copying web module...
xcopy /E /I /Y "%PROJECT_ROOT%\web\*" "%ELECTRON_DIR%\web\" >nul 2>&1

REM Create electron/backend directory structure
echo   - Creating backend structure...
if not exist "%ELECTRON_DIR%\backend" mkdir "%ELECTRON_DIR%\backend"

REM Copy main package files
echo   - Copying package files...
copy /Y "%PROJECT_ROOT%\__init__.py" "%ELECTRON_DIR%\backend\" >nul 2>&1
copy /Y "%PROJECT_ROOT%\setup.py" "%ELECTRON_DIR%\backend\" >nul 2>&1
copy /Y "%PROJECT_ROOT%\pyproject.toml" "%ELECTRON_DIR%\backend\" >nul 2>&1
copy /Y "%PROJECT_ROOT%\requirements.txt" "%ELECTRON_DIR%\backend\" >nul 2>&1
copy /Y "%PROJECT_ROOT%\config.yaml" "%ELECTRON_DIR%\backend\" >nul 2>&1

REM Copy Python packages
for %%P in (manatrix models optimization utils rules pcfg evaluation data training config crawler pentest rl_agent knowledge_graph attack_graph scripts) do (
    echo   - Copying %%P module...
    if exist "%PROJECT_ROOT%\%%P" (
        if not exist "%ELECTRON_DIR%\backend\%%P" mkdir "%ELECTRON_DIR%\backend\%%P"
        xcopy /E /Y "%PROJECT_ROOT%\%%P\*.py" "%ELECTRON_DIR%\backend\%%P\" >nul 2>&1
    )
)

REM Copy checkpoints if they exist
if exist "%PROJECT_ROOT%\checkpoints" (
    echo   - Copying checkpoints...
    if not exist "%ELECTRON_DIR%\backend\checkpoints" mkdir "%ELECTRON_DIR%\backend\checkpoints"
    xcopy /E /Y "%PROJECT_ROOT%\checkpoints\*" "%ELECTRON_DIR%\backend\checkpoints\" >nul 2>&1
)

echo [STEP 1] Backend files prepared.
echo.

echo [STEP 2] Installing Node.js dependencies...
cd /d "%ELECTRON_DIR%"
call npm install
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] npm install failed
    pause
    exit /b 1
)

echo.
echo [STEP 3] Building Electron installer...
call npx electron-builder --win
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Build failed
    pause
    exit /b 1
)

echo.
echo ========================================
echo Build complete!
echo ========================================
echo.
echo Output files:
dir "%ELECTRON_DIR%\dist\*.exe" /b 2>nul

echo.
echo The installer includes:
echo   - Electron frontend
echo   - Python backend (web, manatrix, models, etc.)
echo   - All configuration files
echo.
echo IMPORTANT: Users need Python installed to run the app.
echo Python path will be auto-detected on startup.
echo.

pause
endlocal
