@echo off
REM 部署脚本：把 web/static 推送到 gh-pages 分支
REM 依赖：git subtree（在 Git for Windows 自带）

cd /d %~dp0

echo === 部署 GitHub Pages ===
echo 把 web/static 推送到 gh-pages 分支...

for /f "delims=" %%i in ('git subtree split --prefix web/static main') do set SPLIT=%%i
git push origin "%SPLIT%:gh-pages" --force

echo === 完成！访问 https://uynewnas.github.io/hexlolfun/ ===
pause
