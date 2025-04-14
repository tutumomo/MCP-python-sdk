@echo off
setlocal enabledelayedexpansion

echo ========================================
echo [清除 Git submodule 記錄工具]
echo ========================================

REM 檢查設定檔是否存在
if not exist submodules_config.txt (
    echo [ERROR] 找不到 submodules_config.txt，請先建立！
    pause
    exit /b
)

REM 開始清除每個 submodule
for /f "tokens=1 delims= " %%a in (submodules_config.txt) do (
    set "subPath=%%a"
    echo ----------------------------------------
    echo [INFO] 移除 submodule：!subPath!

    git submodule deinit -f !subPath!
    git rm -f !subPath!
    if exist ".git\modules\!subPath!" (
        rmdir /s /q ".git\modules\!subPath!"
    )
)

REM 刪除 .gitmodules 檔案
if exist .gitmodules (
    del .gitmodules
    echo [INFO] .gitmodules 檔案已刪除
)

echo [INFO] 清除完畢，請手動執行 git add/commit/push
echo ========================================
pause
