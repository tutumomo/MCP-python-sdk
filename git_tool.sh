# 重新建立 macOS/Linux 可用的 git_tool.sh 檔案
shell_script = """#!/bin/bash

echo "========================================"
echo "[選單] Git 操作選擇"
echo "========================================"
echo "[0] 初始化主專案 remote 與 submodules（本地已 clone）"
echo "[1] 初始化 submodules（含檢查是否已初始化）"
echo "[2] 從上游 repo 更新（含 submodules）"
echo "[3] 推送到 GitHub（含 submodules）"
echo "[X] 離開"
echo "========================================"

read -p "請輸入選項編號: " choice

function submodule_init_line() {
    subPath="$1"
    originURL="$2"
    upstreamURL="$3"

    existing_url=$(git config -f .gitmodules --get submodule."$subPath".url)
    if [ -z "$existing_url" ]; then
        echo "[INFO] 加入 submodule：$subPath"
        git submodule add "$originURL" "$subPath"
    else
        echo "[INFO] submodule $subPath 已存在，略過加入。"
    fi
}

case "$choice" in
  0)
    echo "[INFO] 設定主 repo 的 upstream 來源..."
    git remote get-url upstream >/dev/null 2>&1
    if [ $? -ne 0 ]; then
        read -p "請輸入主專案的 upstream URL: " upstreamURL
        git remote add upstream "$upstreamURL"
    else
        echo "[INFO] upstream 已存在，略過設定。"
    fi

    if [ -f "submodules_config.txt" ]; then
        echo "[INFO] 開始初始化 submodules..."
        while read -r line; do
            set -- $line
            submodule_init_line "$1" "$2" "$3"
        done < submodules_config.txt
        git submodule init
        git submodule update --remote --merge
        echo "[INFO] Submodules 初始化完成"
    else
        echo "[INFO] 沒有 submodules_config.txt，略過 submodule 設定。"
    fi
    ;;

  1)
    if [ -f ".gitmodules" ]; then
        read -p "[INFO] 檢測到已有 submodules 記錄，是否重新初始化？(Y/N): " redoInit
        if [[ ! "$redoInit" =~ ^[Yy]$ ]]; then
            echo "[INFO] 已取消初始化 submodules。"
            exit 0
        fi
    fi

    if [ -f "submodules_config.txt" ]; then
        echo "[INFO] 開始依 submodules_config.txt 初始化 submodules..."
        while read -r line; do
            set -- $line
            submodule_init_line "$1" "$2" "$3"
        done < submodules_config.txt
        git submodule init
        git submodule update --remote --merge
        echo "[INFO] Submodules 初始化完成"
    else
        echo "[INFO] 未偵測到 submodules_config.txt，略過 submodule 初始化"
    fi
    ;;

  2)
    echo "[INFO] 更新主專案..."
    git remote get-url upstream >/dev/null 2>&1
    if [ $? -ne 0 ]; then
        read -p "請輸入主專案的 upstream URL: " upstreamURL
        git remote add upstream "$upstreamURL"
    fi
    git fetch upstream
    git pull upstream main --allow-unrelated-histories

    if [ -f "submodules_config.txt" ]; then
        echo "[INFO] 開始更新 submodules..."
        while read -r line; do
            set -- $line
            subPath="$1"
            originURL="$2"
            upstreamURL="$3"
            if [ -d "$subPath" ]; then
                cd "$subPath"
                git remote set-url origin "$originURL"
                git remote get-url upstream >/dev/null 2>&1
                if [ $? -ne 0 ]; then
                    git remote add upstream "$upstreamURL"
                else
                    git remote set-url upstream "$upstreamURL"
                fi
                git checkout main
                git fetch upstream
                git pull upstream main
                cd ..
            fi
        done < submodules_config.txt
    fi
    ;;

  3)
    read -p "請輸入 commit 訊息（直接按 Enter 則使用預設：更新）: " commitMsg
    if [ -z "$commitMsg" ]; then
        commitMsg="更新"
    fi
    timestamp=$(date "+%Y-%m-%d_%H-%M")
    echo "Commit Log - $timestamp" > commit_log.txt
    echo "--------------------------" >> commit_log.txt

    if [ -f "submodules_config.txt" ]; then
        echo "[INFO] 開始推送 submodules..."
        while read -r line; do
            set -- $line
            subPath="$1"
            if [ -d "$subPath" ]; then
                cd "$subPath"
                git add .
                git commit -m "$commitMsg - $timestamp" 2>/dev/null
                git push origin main
                echo "[submodule] $subPath 提交成功：$commitMsg - $timestamp" >> ../commit_log.txt
                cd ..
            fi
        done < submodules_config.txt
    fi

    echo "[INFO] 提交主專案"
    git add .
    git commit -m "$commitMsg - $timestamp" 2>/dev/null
    git push origin main
    echo "[main] 主專案提交成功：$commitMsg - $timestamp" >> commit_log.txt
    ;;

  X|x)
    echo "👋 離開工具"
    exit 0
    ;;
  *)
    echo "❌ 無效選項"
    ;;
esac
"""

with open("/mnt/data/git_tool.sh", "w", encoding="utf-8") as f:
    f.write(shell_script)

"/mnt/data/git_tool.sh"
