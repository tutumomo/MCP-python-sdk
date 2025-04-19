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

### 1. 以 stdio 方式啟動 MCP 伺服器

```
python src/mcp_server.py
```

### 2. 以 HTTP 服務方式啟動（建議用 uvicorn 啟動）

請先確認 `src/mcp_server.py` 已包含下列程式碼：
```python
app = mcp.sse_app()  # 讓 uvicorn 可以直接啟動 HTTP 伺服器
```

然後執行以下指令：
```
uvicorn src.mcp_server:app --reload --port 8000
```
- `--reload` 代表程式碼變更時自動重啟（開發時建議加上）。
- `--port 8000` 可依需求調整。

啟動後，伺服器會以 HTTP 服務方式運作，可透過 API 進行座標轉換。

---

## API 請求範例（HTTP 服務模式）

### 經緯度轉 UTM

POST 請求內容：
```json
{
  "tool": "latlon_to_utm",
  "arguments": {
    "latitude": 25.0478,
    "longitude": 121.5319
  }
}
```

### UTM 轉經緯度

POST 請求內容：
```json
{
  "tool": "utm_to_latlon",
  "arguments": {
    "easting": 304801.6,
    "northing": 2776152.4,
    "zone": 51,
    "south": false
  }
}
```

---

## 注意事項
- 建議所有文字檔案（如 requirements.txt、README.md）皆以 UTF-8 編碼儲存，避免編碼錯誤。
- 若遇到套件安裝或啟動問題，請確認已啟用虛擬環境並安裝所有依賴。
- 若要搬移專案，請整個資料夾一併複製。

## 貢獻

如果您希望對此專案做出貢獻，請隨時提出問題或提交拉取請求。我們歡迎任何改進和建議。

## 授權

此專案遵循 MIT 授權條款。請參閱 LICENSE 文件以獲取更多信息。