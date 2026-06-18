@echo off
REM GitHub Pages 部署脚本
REM 每次 web/static 内容更新后运行此脚本

setlocal

set REPO_DIR=%~dp0
set SRC_DIR=%REPO_DIR%web\static
set DEPLOY_DIR=%REPO_DIR%..\hexlolfun-gh-pages

echo === 部署 GitHub Pages ===
echo 源目录: %SRC_DIR%
echo 部署目录: %DEPLOY_DIR%

REM 清理旧的部署目录
if exist "%DEPLOY_DIR%" rmdir /s /q "%DEPLOY_DIR%"

REM 复制 web/static 到部署目录
xcopy /E /I /Y "%SRC_DIR%" "%DEPLOY_DIR%"

REM 推送到 gh-pages
cd /d "%DEPLOY_DIR%"
git init -b gh-pages >nul 2>&1
git add .
git -c user.email=bot@local -c user.name=bot commit -m "Deploy" >nul 2>&1
git remote add origin https://github.com/UyNewNas/hexlolfun.git >nul 2>&1
git push -f origin gh-pages

echo === 完成！访问 https://uynewnas.github.io/hexlolfun/ ===
pause
