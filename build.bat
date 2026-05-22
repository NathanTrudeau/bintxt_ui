@echo off
REM bintxt_ui Windows build script
REM Requires: pip install pyinstaller
REM Output:   dist\bintxt_ui.exe

echo [bintxt_ui] Building executable...

REM Ensure submodule is up to date
git submodule update --init --recursive

REM Clean previous build
if exist build rmdir /s /q build
if exist dist  rmdir /s /q dist

REM Build
pyinstaller bintxt_ui.spec

if %ERRORLEVEL% EQU 0 (
    echo.
    echo [bintxt_ui] Build complete: dist\bintxt_ui.exe
) else (
    echo.
    echo [bintxt_ui] Build FAILED — check output above.
)
pause
