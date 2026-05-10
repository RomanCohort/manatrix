@echo off
REM Manatrix Studio - Electron Build Script for Windows

echo ========================================
echo Manatrix Studio - Electron Builder
echo ========================================
echo.

REM Change to electron directory
cd /d "%~dp0electron"

REM Check for Node.js
where node >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Node.js not found. Please install Node.js from https://nodejs.org
    pause
    exit /b 1
)

echo [1/2] Installing dependencies...
call npm install
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] npm install failed
    pause
    exit /b 1
)

echo.
echo [2/2] Building installer...
call npx electron-builder --win
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Build failed
    pause
    exit /b 1
)

echo.
echo ========================================
echo Build complete!
echo Output: electron\dist\
echo ========================================
echo.

REM Show the output files
dir electron\dist\ /b 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo No installer files found.
)

pause