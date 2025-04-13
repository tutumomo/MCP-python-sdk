# 建立一個基本的 TUI (Terminal UI) 版本，支援 iTerm2/macOS 終端互動
# 使用 shell script 寫法，讓使用者以鍵盤選單方式操作
# 用 select / case 配合簡易介面，未使用外部 TUI 工具

tui_shell_script = """#!/bin/bash

while true; do
  echo "========================================"
  echo " 🛠️  Git 工具選單"
  echo "========================================"
  echo "1) 初始化主專案 remote 與 submodules（本地已 clone）"
  echo "2) 初始化 submodules（含檢查是否已初始化）"
  echo "3) 從上游 repo 更新（含 submodules）"
  echo "4) 推送到 GitHub（含 submodules）"
  echo "X) 離開"
  echo "========================================"
  read -p "請選擇操作項目: " choice

  case "$choice" in
    1)
      echo "[INFO] 設定主 repo 的 upstream 來源..."
      if ! git remote get-url upstream >/dev/null 2>&1; then
          read -p "請輸入主專案的 upstream URL: " upstreamURL
          git remote add upstream "$upstreamURL"
      else
          echo "[INFO] upstream 已存在，略過設定。"
      fi

      if [ -f "submodules_config.txt" ]; then
          echo "[INFO] 開始初始化 submodules..."
          while read -r line; do
              set -- $line
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
          done < submodules_config.txt
          git submodule init
          git submodule update --remote --merge
          echo "[INFO] Submodules 初始化完成"
      else
          echo "[INFO] 沒有 submodules_config.txt，略過 submodule 設定。"
      fi
      ;;
    2)
      if [ -f ".gitmodules" ]; then
          read -p "[INFO] 檢測到已有 submodules 記錄，是否重新初始化？(Y/N): " redoInit
          if [[ ! "$redoInit" =~ ^[Yy]$ ]]; then
              echo "[INFO] 已取消初始化 submodules。"
              continue
          fi
      fi

      if [ -f "submodules_config.txt" ]; then
          echo "[INFO] 開始依 submodules_config.txt 初始化 submodules..."
          while read -r line; do
              set -- $line
              subPath="$1"
              originURL="$2"
              upstreamURL="$3"
              git config -f .gitmodules --get submodule."$subPath".url >/dev/null 2>&1
              if [ $? -ne 0 ]; then
                  git submodule add "$originURL" "$subPath"
              fi
          done < submodules_config.txt
          git submodule init
          git submodule update --remote --merge
          echo "[INFO] Submodules 初始化完成"
      else
          echo "[INFO] 未偵測到 submodules_config.txt，略過 submodule 初始化"
      fi
      ;;
    3)
      echo "[INFO] 更新主專案..."
      if ! git remote get-url upstream >/dev/null 2>&1; then
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
                  if ! git remote get-url upstream >/dev/null 2>&1; then
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
    4)
      read -p "請輸入 commit 訊息（直接按 Enter 則使用預設：更新）: " commitMsg
      [ -z "$commitMsg" ] && commitMsg="更新"
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
      echo "❌ 無效選項，請重新選擇"
      ;;
  esac
done
"""

# 儲存為可執行 shell script
tui_path = "/mnt/data/git_tool_tui.sh"
with open(tui_path, "w", encoding="utf-8") as f:
    f.write(tui_shell_script)

tui_path
