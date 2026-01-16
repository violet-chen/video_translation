@echo off
chcp 65001 >nul
echo ========================================
echo   FFmpeg 安装助手
echo ========================================
echo.

:: 检查是否已安装
ffmpeg -version >nul 2>&1
if not errorlevel 1 (
    echo [√] FFmpeg 已安装！
    ffmpeg -version | findstr "ffmpeg version"
    echo.
    pause
    exit /b 0
)

echo FFmpeg 未安装，请按以下步骤手动安装：
echo.
echo 1. 访问 https://github.com/BtbN/FFmpeg-Builds/releases
echo.
echo 2. 下载 ffmpeg-master-latest-win64-gpl.zip
echo.
echo 3. 解压到 C:\ffmpeg
echo.
echo 4. 将 C:\ffmpeg\bin 添加到系统环境变量 PATH
echo    - 右键"此电脑" → 属性 → 高级系统设置
echo    - 环境变量 → 系统变量 → Path → 编辑 → 新建
echo    - 添加: C:\ffmpeg\bin
echo.
echo 5. 重启命令行或电脑
echo.
echo ========================================
echo.

:: 尝试使用winget安装
echo 正在尝试使用 winget 自动安装...
winget install Gyan.FFmpeg -e --silent
if not errorlevel 1 (
    echo.
    echo [√] FFmpeg 安装成功！请重启命令行。
)

pause
