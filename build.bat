@echo off
chcp 65001 >nul
echo ========================================
echo   Video Translator - Build Script
echo ========================================
echo.

cd /d %~dp0

echo [1/3] Installing dependencies...
pip install PyQt6 faster-whisper deep-translator pyinstaller -i https://pypi.tuna.tsinghua.edu.cn/simple -q

echo [2/3] Cleaning previous build...
if exist "build" rmdir /s /q build
if exist "dist" rmdir /s /q dist
if exist "*.spec" del /q *.spec

echo [3/3] Building exe...
pyinstaller --noconfirm --onedir --windowed ^
    --name "VideoTranslator" ^
    --hidden-import "faster_whisper" ^
    --hidden-import "deep_translator" ^
    --hidden-import "ctranslate2" ^
    --hidden-import "huggingface_hub" ^
    --hidden-import "tokenizers" ^
    --collect-all "faster_whisper" ^
    --collect-all "ctranslate2" ^
    --copy-metadata "huggingface_hub" ^
    --copy-metadata "tokenizers" ^
    video_translator.py

echo.
echo ========================================
echo   Build Complete!
echo   Output: dist\VideoTranslator
echo ========================================
echo.
echo Note: FFmpeg is required to run the program
echo Download: https://ffmpeg.org/download.html
echo.
pause
