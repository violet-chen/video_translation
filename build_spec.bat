@echo off
chcp 65001 >nul
echo ========================================
echo   Video Translator - Build with Spec
echo ========================================
echo.

cd /d %~dp0

echo [1/3] Cleaning previous build...
if exist "build" rmdir /s /q build
if exist "dist" rmdir /s /q dist

echo [2/3] Building exe with spec file...
pyinstaller --noconfirm VideoTranslator.spec

echo.
if exist "dist\VideoTranslator\VideoTranslator.exe" (
    echo ========================================
    echo   Build Success!
    echo   Output: dist\VideoTranslator\VideoTranslator.exe
    echo ========================================
) else (
    echo Build failed, please check error messages above.
)
echo.
echo Note: FFmpeg is required
pause
