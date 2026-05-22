@echo off
REM M1racle 一键部署: 批量导入 + 同步 WebDAV + 上传 GitHub
cd /d G:\M1racle-123pan-share

echo ========================================
echo   M1racle 资源库 - 一键导入 & 同步
echo ========================================
echo.

REM 1. 确保服务在跑
tasklist /FI "IMAGENAME eq python.exe" 2>NUL | find /I "python.exe" >NUL
if errorlevel 1 (
    echo [启动] 启动 web 服务...
    start "M1racle-Web" "C:\Users\21234\AppData\Local\Programs\Python\Python312\python.exe" web.py
    timeout /t 5 /nobreak >nul
    echo [启动] 等待服务就绪...
    timeout /t 3 /nobreak >nul
) else (
    echo [跳过] web 服务已在运行
)

REM 2. 批量导入
echo.
echo [导入] 开始批量导入 links.txt ...
"C:\Users\21234\AppData\Local\Programs\Python\Python312\python.exe" batch_import.py
if errorlevel 1 (
    echo [警告] 导入过程可能有错误，继续同步...
)

REM 3. 同步到 WebDAV
echo.
echo [同步] 复制数据库到 WebDAV ...
copy /Y "assets\PAN123DATABASE.db" "G:\123Pan-Unlimited-WebDAV-Windows\123Pan-Unlimited-WebDAV-Windows\PAN123DATABASE.db"
echo [同步] WebDAV 数据库已更新

REM 4. 上传 GitHub
echo.
echo [上传] 发布到 GitHub Release ...
gh release upload database "assets\PAN123DATABASE.db" --clobber --repo ldohgfsdu/M1racle-123pan-share

echo.
echo ========================================
echo   ✅ 全部完成！
echo ========================================
pause
