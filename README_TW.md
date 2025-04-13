# MCP Python SDK

<div align="center">

<strong>模型上下文協定 (MCP) 的 Python 實作</strong>

[![PyPI][pypi-badge]][pypi-url]
[![MIT licensed][mit-badge]][mit-url]
[![Python Version][python-badge]][python-url]
[![Documentation][docs-badge]][docs-url]
[![Specification][spec-badge]][spec-url]
[![GitHub Discussions][discussions-badge]][discussions-url]

</div>

<!-- omit in toc -->
## 目錄

- [MCP Python SDK](#mcp-python-sdk)
  - [概觀](#概觀)
  - [安裝](#安裝)
    - [將 MCP 加入您的 Python 專案](#將-mcp-加入您的-python-專案)
    - [執行獨立的 MCP 開發工具](#執行獨立的-mcp-開發工具)
  - [快速入門](#快速入門)
  - [什麼是 MCP？](#什麼是-mcp)
  - [核心概念](#核心概念)
    - [伺服器](#伺服器)
    - [資源](#資源)
    - [工具](#工具)
    - [提示](#提示)
    - [圖片](#圖片)
    - [上下文](#上下文)
  - [執行您的伺服器](#執行您的伺服器)
    - [開發模式](#開發模式)
    - [Claude 桌面整合](#claude-桌面整合)
    - [直接執行](#直接執行)
    - [掛載到現有的 ASGI 伺服器](#掛載到現有的-asgi-伺服器)
  - [範例](#範例)
    - [Echo 伺服器](#echo-伺服器)
    - [SQLite 瀏覽器](#sqlite-瀏覽器)
  - [進階用法](#進階用法)
    - [低階伺服器](#低階伺服器)
    - [撰寫 MCP 客戶端](#撰寫-mcp-客戶端)
    - [MCP 原語](#mcp-原語)
    - [伺服器能力](#伺服器能力)
  - [文件](#文件)
  - [貢獻](#貢獻)
  - [授權](#授權)

[pypi-badge]: https://img.shields.io/pypi/v/mcp.svg
[pypi-url]: https://pypi.org/project/mcp/
[mit-badge]: https://img.shields.io/pypi/l/mcp.svg
[mit-url]: https://github.com/modelcontextprotocol/python-sdk/blob/main/LICENSE
[python-badge]: https://img.shields.io/pypi/pyversions/mcp.svg
[python-url]: https://www.python.org/downloads/
[docs-badge]: https://img.shields.io/badge/docs-modelcontextprotocol.io-blue.svg
[docs-url]: https://modelcontextprotocol.io
[spec-badge]: https://img.shields.io/badge/spec-spec.modelcontextprotocol.io-blue.svg
[spec-url]: https://spec.modelcontextprotocol.io
[discussions-badge]: https://img.shields.io/github/discussions/modelcontextprotocol/python-sdk
[discussions-url]: https://github.com/modelcontextprotocol/python-sdk/discussions

## 概觀

模型上下文協定 (Model Context Protocol, MCP) 允許應用程式以標準化的方式為大型語言模型 (LLM) 提供上下文，將提供上下文的關注點與實際的 LLM 互動分開。這個 Python SDK 實作了完整的 MCP 規範，讓您可以輕鬆地：

- 建構可連接到任何 MCP 伺服器的 MCP 客戶端
- 建立公開資源、提示和工具的 MCP 伺服器
- 使用標準傳輸協定，如 stdio 和 SSE
- 處理所有 MCP 協定訊息和生命週期事件

## 安裝

### 將 MCP 加入您的 Python 專案

我們建議使用 [uv](https://docs.astral.sh/uv/) 來管理您的 Python 專案。

如果您尚未建立 uv 管理的專案，請建立一個：

   ```bash
   uv init mcp-server-demo
   cd mcp-server-demo
   ```

   然後將 MCP 加入您的專案依賴項：

   ```bash
   uv add "mcp[cli]"
   ```

或者，對於使用 pip 管理依賴項的專案：
```bash
pip install "mcp[cli]"
```

### 執行獨立的 MCP 開發工具

使用 uv 執行 mcp 指令：

```bash
uv run mcp
```

## 快速入門

讓我們建立一個簡單的 MCP 伺服器，公開一個計算機工具和一些資料：

```python
# server.py
from mcp.server.fastmcp import FastMCP

# 建立一個 MCP 伺服器
mcp = FastMCP("Demo")


# 加入一個加法工具
@mcp.tool()
def add(a: int, b: int) -> int:
    """將兩個數字相加"""
    return a + b


# 加入一個動態問候資源
@mcp.resource("greeting://{name}")
def get_greeting(name: str) -> str:
    """取得個人化的問候語"""
    return f"Hello, {name}!"
```

您可以將此伺服器安裝在 [Claude Desktop](https://claude.ai/download) 中，並透過執行以下指令立即與其互動：
```bash
mcp install server.py
```

或者，您可以使用 MCP Inspector 進行測試：
```bash
mcp dev server.py
```

## 什麼是 MCP？

[模型上下文協定 (MCP)](https://modelcontextprotocol.io) 讓您可以建構伺服器，以安全、標準化的方式向 LLM 應用程式公開資料和功能。可以把它想像成一個 Web API，但專門為 LLM 互動而設計。MCP 伺服器可以：

- 透過 **資源 (Resources)** 公開資料（可以把它們想像成類似 GET 端點；用於將資訊載入 LLM 的上下文）
- 透過 **工具 (Tools)** 提供功能（類似 POST 端點；用於執行程式碼或產生副作用）
- 透過 **提示 (Prompts)** 定義互動模式（可重複使用的 LLM 互動模板）
- 還有更多！

## 核心概念

### 伺服器

FastMCP 伺服器是您與 MCP 協定的核心介面。它處理連線管理、協定合規性和訊息路由：

```python
# 加入對啟動/關閉的生命週期支援，並使用強型別
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from dataclasses import dataclass

from fake_database import Database  # 請替換為您實際的資料庫類型

from mcp.server.fastmcp import Context, FastMCP

# 建立一個具名伺服器
mcp = FastMCP("My App")

# 指定部署和開發的依賴項
mcp = FastMCP("My App", dependencies=["pandas", "numpy"])


@dataclass
class AppContext:
    db: Database


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    """使用型別安全的上下文管理應用程式生命週期"""
    # 在啟動時初始化
    db = await Database.connect()
    try:
        yield AppContext(db=db)
    finally:
        # 在關閉時清理
        await db.disconnect()


# 將生命週期傳遞給伺服器
mcp = FastMCP("My App", lifespan=app_lifespan)


# 在工具中存取型別安全的生命週期上下文
@mcp.tool()
def query_db(ctx: Context) -> str:
    """使用已初始化資源的工具"""
    db = ctx.request_context.lifespan_context.db
    return db.query()
```

### 資源

資源是您向 LLM 公開資料的方式。它們類似於 REST API 中的 GET 端點 - 提供資料，但不應執行大量計算或產生副作用：

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("My App")


@mcp.resource("config://app")
def get_config() -> str:
    """靜態設定資料"""
    return "應用程式設定在此"


@mcp.resource("users://{user_id}/profile")
def get_user_profile(user_id: str) -> str:
    """動態使用者資料"""
    return f"使用者 {user_id} 的個人資料"
```

### 工具

工具讓 LLM 可以透過您的伺服器採取行動。與資源不同，工具預期會執行計算並產生副作用：

```python
import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("My App")


@mcp.tool()
def calculate_bmi(weight_kg: float, height_m: float) -> float:
    """根據體重（公斤）和身高（公尺）計算 BMI"""
    return weight_kg / (height_m**2)


@mcp.tool()
async def fetch_weather(city: str) -> str:
    """取得指定城市的目前天氣"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"https://api.weather.com/{city}")
        return response.text
```

### 提示

提示是可重複使用的模板，可幫助 LLM 有效地與您的伺服器互動：

```python
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.prompts import base

mcp = FastMCP("My App")


@mcp.prompt()
def review_code(code: str) -> str:
    return f"請檢閱這段程式碼：\n\n{code}"


@mcp.prompt()
def debug_error(error: str) -> list[base.Message]:
    return [
        base.UserMessage("我遇到了這個錯誤："),
        base.UserMessage(error),
        base.AssistantMessage("我來幫您除錯。您已經嘗試過哪些方法了？"),
    ]
```

### 圖片

FastMCP 提供了一個 `Image` 類別，可自動處理圖片資料：

```python
from mcp.server.fastmcp import FastMCP, Image
from PIL import Image as PILImage

mcp = FastMCP("My App")


@mcp.tool()
def create_thumbnail(image_path: str) -> Image:
    """從圖片建立縮圖"""
    img = PILImage.open(image_path)
    img.thumbnail((100, 100))
    return Image(data=img.tobytes(), format="png")
```

### 上下文

Context 物件讓您的工具和資源可以存取 MCP 功能：

```python
from mcp.server.fastmcp import FastMCP, Context

mcp = FastMCP("My App")


@mcp.tool()
async def long_task(files: list[str], ctx: Context) -> str:
    """處理多個檔案並追蹤進度"""
    for i, file in enumerate(files):
        ctx.info(f"正在處理 {file}")
        await ctx.report_progress(i, len(files))
        data, mime_type = await ctx.read_resource(f"file://{file}")
    return "處理完成"
```

## 執行您的伺服器

### 開發模式

測試和除錯伺服器最快的方法是使用 MCP Inspector：

```bash
mcp dev server.py

# 加入依賴項
mcp dev server.py --with pandas --with numpy

# 掛載本地程式碼
mcp dev server.py --with-editable .
```

### Claude 桌面整合

伺服器準備就緒後，將其安裝到 Claude Desktop 中：

```bash
mcp install server.py

# 自訂名稱
mcp install server.py --name "我的分析伺服器"

# 環境變數
mcp install server.py -v API_KEY=abc123 -v DB_URL=postgres://...
mcp install server.py -f .env
```

### 直接執行

對於進階情境，例如自訂部署：

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("My App")

if __name__ == "__main__":
    mcp.run()
```

執行方式：
```bash
python server.py
# 或
mcp run server.py
```

### 掛載到現有的 ASGI 伺服器

您可以使用 `sse_app` 方法將 SSE 伺服器掛載到現有的 ASGI 伺服器。這讓您可以將 SSE 伺服器與其他 ASGI 應用程式整合。

```python
from starlette.applications import Starlette
from starlette.routing import Mount, Host
from mcp.server.fastmcp import FastMCP


mcp = FastMCP("My App")

# 將 SSE 伺服器掛載到現有的 ASGI 伺服器
app = Starlette(
    routes=[
        Mount('/', app=mcp.sse_app()),
    ]
)

# 或動態掛載為主機
app.router.routes.append(Host('mcp.acme.corp', app=mcp.sse_app()))
```

有關在 Starlette 中掛載應用程式的更多資訊，請參閱 [Starlette 文件](https://www.starlette.io/routing/#submounting-routes)。

## 範例

### Echo 伺服器

一個簡單的伺服器，展示資源、工具和提示：

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Echo")


@mcp.resource("echo://{message}")
def echo_resource(message: str) -> str:
    """將訊息作為資源回傳"""
    return f"資源回傳： {message}"


@mcp.tool()
def echo_tool(message: str) -> str:
    """將訊息作為工具回傳"""
    return f"工具回傳： {message}"


@mcp.prompt()
def echo_prompt(message: str) -> str:
    """建立一個回傳提示"""
    return f"請處理此訊息： {message}"
```

### SQLite 瀏覽器

一個更複雜的範例，展示資料庫整合：

```python
import sqlite3

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("SQLite Explorer")


@mcp.resource("schema://main")
def get_schema() -> str:
    """將資料庫結構作為資源提供"""
    conn = sqlite3.connect("database.db")
    schema = conn.execute("SELECT sql FROM sqlite_master WHERE type='table'").fetchall()
    return "\n".join(sql[0] for sql in schema if sql[0])


@mcp.tool()
def query_data(sql: str) -> str:
    """安全地執行 SQL 查詢"""
    conn = sqlite3.connect("database.db")
    try:
        result = conn.execute(sql).fetchall()
        return "\n".join(str(row) for row in result)
    except Exception as e:
        return f"錯誤： {str(e)}"
```

## 進階用法

### 低階伺服器

若要獲得更多控制權，您可以直接使用低階伺服器實作。這讓您可以完全存取協定，並允許您自訂伺服器的各個方面，包括透過 lifespan API 進行生命週期管理：

```python
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fake_database import Database  # 請替換為您實際的資料庫類型

from mcp.server import Server


@asynccontextmanager
async def server_lifespan(server: Server) -> AsyncIterator[dict]:
    """管理伺服器啟動和關閉生命週期。"""
    # 在啟動時初始化資源
    db = await Database.connect()
    try:
        yield {"db": db}
    finally:
        # 在關閉時清理
        await db.disconnect()


# 將生命週期傳遞給伺服器
server = Server("example-server", lifespan=server_lifespan)


# 在處理常式中存取生命週期上下文
@server.call_tool()
async def query_db(name: str, arguments: dict) -> list:
    ctx = server.request_context
    db = ctx.lifespan_context["db"]
    return await db.query(arguments["query"])
```

lifespan API 提供：
- 一種在伺服器啟動時初始化資源並在停止時清理它們的方法
- 透過處理常式中的請求上下文存取已初始化的資源
- 在生命週期和請求處理常式之間進行型別安全的上下文傳遞

```python
import mcp.server.stdio
import mcp.types as types
from mcp.server.lowlevel import NotificationOptions, Server
from mcp.server.models import InitializationOptions

# 建立伺服器實例
server = Server("example-server")


@server.list_prompts()
async def handle_list_prompts() -> list[types.Prompt]:
    return [
        types.Prompt(
            name="example-prompt",
            description="一個範例提示模板",
            arguments=[
                types.PromptArgument(
                    name="arg1", description="範例參數", required=True
                )
            ],
        )
    ]


@server.get_prompt()
async def handle_get_prompt(
    name: str, arguments: dict[str, str] | None
) -> types.GetPromptResult:
    if name != "example-prompt":
        raise ValueError(f"未知的提示： {name}")

    return types.GetPromptResult(
        description="範例提示",
        messages=[
            types.PromptMessage(
                role="user",
                content=types.TextContent(type="text", text="範例提示文字"),
            )
        ],
    )


async def run():
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="example",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    import asyncio

    asyncio.run(run())
```

### 撰寫 MCP 客戶端

SDK 提供了一個高階客戶端介面，用於連接到 MCP 伺服器：

```python
from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client

# 建立用於 stdio 連線的伺服器參數
server_params = StdioServerParameters(
    command="python",  # 可執行檔
    args=["example_server.py"],  # 可選的命令列參數
    env=None,  # 可選的環境變數
)


# 可選：建立一個取樣回呼函式
async def handle_sampling_message(
    message: types.CreateMessageRequestParams,
) -> types.CreateMessageResult:
    return types.CreateMessageResult(
        role="assistant",
        content=types.TextContent(
            type="text",
            text="Hello, world! from model",
        ),
        model="gpt-3.5-turbo",
        stopReason="endTurn",
    )


async def run():
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(
            read, write, sampling_callback=handle_sampling_message
        ) as session:
            # 初始化連線
            await session.initialize()

            # 列出可用的提示
            prompts = await session.list_prompts()

            # 取得一個提示
            prompt = await session.get_prompt(
                "example-prompt", arguments={"arg1": "value"}
            )

            # 列出可用的資源
            resources = await session.list_resources()

            # 列出可用的工具
            tools = await session.list_tools()

            # 讀取一個資源
            content, mime_type = await session.read_resource("file://some/path")

            # 呼叫一個工具
            result = await session.call_tool("tool-name", arguments={"arg1": "value"})


if __name__ == "__main__":
    import asyncio

    asyncio.run(run())
```

### MCP 原語

MCP 協定定義了伺服器可以實作的三個核心原語：

| 原語    | 控制權               | 描述                                         | 範例用途                  |
|-----------|-----------------------|-----------------------------------------------------|------------------------------|
| 提示 (Prompts)   | 使用者控制       | 由使用者選擇呼叫的互動式模板        | 斜線指令、選單選項 |
| 資源 (Resources) | 應用程式控制| 由客戶端應用程式管理的上下文資料   | 檔案內容、API 回應 |
| 工具 (Tools)     | 模型控制      | 向 LLM 公開以採取行動的函式        | API 呼叫、資料更新      |

### 伺服器能力

MCP 伺服器在初始化期間宣告能力：

| 能力  | 功能旗標                 | 描述                        |
|-------------|------------------------------|------------------------------------|
| `prompts`   | `listChanged`                | 提示模板管理         |
| `resources` | `subscribe`<br/>`listChanged`| 資源公開和更新      |
| `tools`     | `listChanged`                | 工具探索和執行       |
| `logging`   | -                            | 伺服器記錄設定       |
| `completion`| -                            | 參數自動完成建議    |

## 文件

- [模型上下文協定文件](https://modelcontextprotocol.io)
- [模型上下文協定規範](https://spec.modelcontextprotocol.io)
- [官方支援的伺服器](https://github.com/modelcontextprotocol/servers)

## 貢獻

我們熱衷於支援各種經驗水平的貢獻者，並希望看到您參與到專案中。請參閱 [貢獻指南](CONTRIBUTING.md) 開始。

## 授權

本專案採用 MIT 授權 - 詳情請參閱 LICENSE 檔案。