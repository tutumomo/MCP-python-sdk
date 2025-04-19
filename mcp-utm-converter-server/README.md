# MCP UTM Converter Server

這個專案是一個 MCP 伺服器，提供經緯度與 UTM 座標之間的轉換功能。伺服器能夠接收來自客戶端的請求，並根據請求的類型進行相應的座標轉換。

## 目錄結構

```
mcp-utm-converter-server
├── src
│   ├── mcp_server.py        # MCP 伺服器的主要入口點
│   ├── utm_converter.py      # 包含經緯度與 UTM 座標轉換的具體實現
│   └── types
│       └── __init__.py      # 定義與 MCP 相關的數據類型和結構
├── requirements.txt          # 專案所需的 Python 套件和依賴項
└── README.md                 # 專案說明和使用指南
```

## 安裝

在開始之前，請確保您已安裝 Python 3.x。然後，您可以使用以下命令安裝所需的依賴項：

```
pip install -r requirements.txt
```

## 使用

要啟動 MCP 伺服器，請運行以下命令：

```
python src/mcp_server.py
```

伺服器啟動後，您可以通過發送請求來使用經緯度與 UTM 座標轉換功能。請參考 `src/mcp_server.py` 中的具體實現以了解可用的請求格式和參數。

## 貢獻

如果您希望對此專案做出貢獻，請隨時提出問題或提交拉取請求。我們歡迎任何改進和建議。

## 授權

此專案遵循 MIT 授權條款。請參閱 LICENSE 文件以獲取更多信息。