@echo off
setlocal enabledelayedexpansion

:menu
echo ========================================
echo [選單] Git 操作選擇
echo ========================================
echo [0] 全新裝機初始化（建議在新電腦上第一次操作用）
echo [1] 初始化 submodules（含檢查是否已初始化）
echo [2] 從上游 repo 更新（含 submodules）
echo [3] 推送到 GitHub（含 submodules）
echo [X] 離開
echo ========================================
set /p choice=請輸入選項編號：

if /I "!choice!"=="0" goto fullinit
if /I "!choice!"=="1" goto init
if /I "!choice!"=="2" goto pull
if /I "!choice!"=="3" goto push
if /I "!choice!"=="X" goto end
goto menu

:fullinit
set /p "repoURL=請輸入 GitHub repo URL（例如 https://github.com/你/adk-python.git）: "
git clone --recurse-submodules !repoURL!
cd adk-python
git submodule update --init --recursive
echo [INFO] 已 clone 並初始化 submodules

git remote | findstr "upstream" > nul
IF ERRORLEVEL 1 (
    set /p upstreamURL=請輸入主專案的 upstream URL:
    git remote add upstream !upstreamURL!
)

echo [INFO] 初始化完成，歡迎使用
pause
goto end

:init
set "needInit=1"

if exist .gitmodules (
    echo [INFO] 偵測到 .gitmodules 存在。
    for /f %%i in ('findstr /i "\[submodule" .gitmodules') do (
        set "needInit=0"
    )
)

if "!needInit!"=="0" (
    set /p redoInit=[INFO] 檢測到已有 submodules 記錄，是否重新初始化？(Y/N):
    if /I "!redoInit!" NEQ "Y" (
        echo [INFO] 已取消初始化 submodules。
        goto menu
    )
)

if exist submodules_config.txt (
    echo [INFO] 開始依 submodules_config.txt 初始化 submodules...
    for /f "tokens=1,2,3 delims= " %%a in (submodules_config.txt) do (
        if not exist "%%a\\" (
            git submodule add %%b %%a
        )
    )
    git submodule init
    git submodule update --remote --merge
    echo [INFO] Submodules 初始化完成
) else (
    echo [INFO] 未偵測到 submodules_config.txt，略過 submodule 初始化
)
goto menu

:pull
echo [INFO] 更新主專案...
git remote | findstr "upstream" > nul
IF ERRORLEVEL 1 (
    set /p upstreamURL=請輸入主專案的 upstream URL:
    git remote add upstream !upstreamURL!
)
git fetch upstream
git pull upstream main --allow-unrelated-histories

if exist submodules_config.txt (
    echo [INFO] 開始更新 submodules（從 upstream 拉取）
    for /f "tokens=1,2,3 delims= " %%a in (submodules_config.txt) do (
        set "subPath=%%a"
        set "originURL=%%b"
        set "upstreamURL=%%c"
        if exist "!subPath!\\" (
            pushd "!subPath!" > nul
            git remote set-url origin !originURL!
            git remote | findstr "upstream" > nul
            if ERRORLEVEL 1 (
                git remote add upstream !upstreamURL!
            ) else (
                git remote set-url upstream !upstreamURL!
            )
            git checkout main
            git fetch upstream
            git pull upstream main
            popd > nul
        )
    )
)
goto menu

:push
set "defaultMsg=更新"
set /p "commitMsg=請輸入 commit 訊息（直接按 Enter 則使用預設："更新"）: "
if "!commitMsg!"=="" (
    set commitMsg=!defaultMsg!
)

for /f "tokens=1-4 delims=/ " %%a in ('date /t') do (
    set today=%%a-%%b-%%c
)
for /f "tokens=1-2 delims=: " %%x in ('time /t') do (
    set now=%%x_%%y
)
set timestamp=!today!_!now!

echo Commit Log - !timestamp! > commit_log.txt
echo -------------------------- >> commit_log.txt

if exist submodules_config.txt (
    echo [INFO] 開始推送 submodules...
    for /f "tokens=1,2,3 delims= " %%a in (submodules_config.txt) do (
        set "subPath=%%a"
        set "originURL=%%b"
        set "upstreamURL=%%c"
        if exist "!subPath!\\" (
            pushd "!subPath!" > nul
            git add .
            git commit -m "!commitMsg! - !timestamp!" 2>nul
            git push origin main
            echo [submodule] %%a 提交成功：!commitMsg! - !timestamp! >> ..\\commit_log.txt
            popd > nul
        )
    )
)

echo [INFO] 提交主專案
git add .
git commit -m "!commitMsg! - !timestamp!" 2>nul
git push origin main
echo [main] 主專案提交成功：!commitMsg! - !timestamp! >> commit_log.txt

goto menu

:end
echo.
echo 作業結束，歡迎下次再用！
pause
