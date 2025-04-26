# Model Context Protocol (MCP) 程式設計極速入門

[TOC]

## 簡介

模型上下文協定（MCP）是一個創新的開源協定，它重新定義了大型語言模型（LLM）與外部世界的互動方式。MCP 提供了一種標準化方法，使任意大型語言模型能夠輕鬆連接各種資料來源和工具，實現資訊的無縫存取和處理。MCP 就像是 AI 應用程式的 USB-C 介面，為 AI 模型提供了一種標準化的方式來連接不同的資料來源和工具。

![image-20250223214308430](.assets/image-20250223214308430.png)

MCP 有以下幾個核心功能：

- Resources 資源
- Prompts 提示詞
- Tools 工具
- Sampling 取樣
- Roots 根目錄
- Transports 傳輸層

因為大部分功能其實都是服務於 Claude 用戶端的，本文更希望編寫的 MCP 伺服器服務與通用大型語言模型，所以本文將會主要以「工具」為重點，其他功能會放到最後進行簡單講解。

其中 MCP 的傳輸層支援了 2 種協定的實作：stdio（標準輸入/輸出）和 SSE（伺服器傳送事件），因為 stdio 更為常用，所以本文會以 stdio 為例進行講解。

本文將會使用 3.11 的 Python 版本，並使用 uv 來管理 Python 專案。同時程式碼將會在文末放到 Github 上，廢話不多說，我們這就開始吧～

## 開發 MCP 伺服器

在這一小節中，我們將會實作一個用於網路搜尋的伺服器。首先，我們先來透過 uv 初始化我們的專案。

> uv 官方文件：https://docs.astral.sh/uv/

```shell
# 初始化專案
uv init mcp_getting_started
cd mcp_getting_started

# 建立虛擬環境並進入虛擬環境
uv venv
.venv\Scripts\activate.bat

# 安裝依賴
uv add "mcp[cli]" httpx openai

```

然後我們來建立一個叫 `web_search.py` 的檔案，來實作我們的服務。MCP 為我們提供了 2 個物件：`mcp.server.FastMCP` 和 `mcp.server.Server`，`mcp.server.FastMCP` 是更高層的封裝，我們這裡就來使用它。

```python
import httpx
from mcp.server import FastMCP

# # 初始化 FastMCP 伺服器
app = FastMCP('web-search')
```

實作執行的方法非常簡單，MCP 為我們提供了一個 `@mcp.tool()` 我們只需要將實作函式用這個裝飾器裝飾即可。函式名稱將作為工具名稱，參數將作為工具參數，並透過註解來描述工具與參數，以及傳回值。

這裡我們直接使用智譜的介面，它這個介面不僅能幫我們搜尋到相關的結果連結，並幫我們產生了對應連結中文章總結後的內容的，~~並且現階段是免費的~~(目前已經開始收費，0.03元/次)，非常適合我們。

>官方文件：https://bigmodel.cn/dev/api/search-tool/web-search-pro
>
>API Key 產生地址：https://bigmodel.cn/usercenter/proj-mgmt/apikeys

```python
@app.tool()
async def web_search(query: str) -> str:
    """
    搜尋網際網路內容

    Args:
        query: 要搜尋的內容

    Returns:
        搜尋結果的總結
    """

    async with httpx.AsyncClient() as client:
        response = await client.post(
            'https://open.bigmodel.cn/api/paas/v4/tools',
            headers={'Authorization': '換成你自己的API KEY'},
            json={
                'tool': 'web-search-pro',
                'messages': [
                    {'role': 'user', 'content': query}
                ],
                'stream': False
            }
        )

        res_data = []
        for choice in response.json()['choices']:
            for message in choice['message']['tool_calls']:
                search_results = message.get('search_result')
                if not search_results:
                    continue
                for result in search_results:
                    res_data.append(result['content'])

        return '\n\n\n'.join(res_data)
```

最後，我們來新增執行伺服器的程式碼。

```python
if __name__ == "__main__":
    app.run(transport='stdio')
```

## 調試 MCP 伺服器

此時，我們就完成了 MCP 伺服器端的編寫。下面，我們來使用官方提供的 `Inspector` 視覺化工具來調試我們的伺服器。

我們可以透過兩種方法來執行 `Inspector`：

> 請先確保已經安裝了 node 環境。

透過 npx：

```shell
npx -y @modelcontextprotocol/inspector <command> <arg1> <arg2>
```

我們的這個程式碼執行命令為：

```shell
npx -y @modelcontextprotocol/inspector uv run web_search.py
```



透過 mcp dev 來執行：

```shell
mcp dev PYTHONFILE
```

我們的這個程式碼執行命令為：

```shell
mcp dev web_search.py
```

當出現如下提示則代表執行成功。如果提示連線出錯，可能是連接埠被佔用，可以看這個 issue 的解決方法：https://github.com/liaokongVFX/MCP-Chinese-Getting-Started-Guide/issues/6

![image-20250223223638135](.assets/image-20250223223638135.png)

然後，我們開啟這個地址，點擊左側的 `Connect` 按鈕，即可連線我們剛寫的服務。然後我們切換到 `Tools` 欄中，點擊 `List Tools` 按鈕即可看到我們剛寫的工具，我們就可以開始進行調試啦。

![image-20250223224052795](.assets/image-20250223224052795.png)

## 開發 MCP 用戶端

首先，我們先來看看如何在用戶端如何呼叫我們剛才開發的 MCP 伺服器中的工具。

```python
import asyncio

from mcp.client.stdio import stdio_client
from mcp import ClientSession, StdioServerParameters

# 為 stdio 連線建立伺服器參數
server_params = StdioServerParameters(
    # 伺服器執行的命令，這裡我們使用 uv 來執行 web_search.py
    command='uv',
    # 執行的參數
    args=['run', 'web_search.py'],
    # 環境變數，預設為 None，表示使用目前環境變數
    # env=None
)


async def main():
    # 建立 stdio 用戶端
    async with stdio_client(server_params) as (stdio, write):
        # 建立 ClientSession 物件
        async with ClientSession(stdio, write) as session:
            # 初始化 ClientSession
            await session.initialize()

            # 列出可用的工具
            response = await session.list_tools()
            print(response)

            # 呼叫工具
            response = await session.call_tool('web_search', {'query': '今天杭州天氣'})
            print(response)


if __name__ == '__main__':
    asyncio.run(main())

```

因為我們的 python 指令稿需要在虛擬環境中才能執行，所以這裡我們透過 `uv` 來啟動我們的指令稿。

下面我們來透過一個小例子來看看如何讓 `DeepSeek` 來呼叫我們 MCP 伺服器中的方法。

這裡我們會用 `dotenv` 來管理我們相關的環境變數。.env 檔案內容如下：

```shell
OPENAI_API_KEY=sk-89baxxxxxxxxxxxxxxxxxx
OPENAI_BASE_URL=https://api.deepseek.com
OPENAI_MODEL=deepseek-chat
```

首先我們來編寫我們的 `MCPClient` 類別。

```python
import json
import asyncio
import os
from typing import Optional
from contextlib import AsyncExitStack

from openai import OpenAI
from dotenv import load_dotenv

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


load_dotenv()


class MCPClient:
    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.client = OpenAI()
```

然後我們新增 `connect_to_server` 方法來初始化我們的 MCP 伺服器的 session。

```python
    async def connect_to_server(self):
        server_params = StdioServerParameters(
            command='uv',
            args=['run', 'web_search.py'],
            env=None
        )

        stdio_transport = await self.exit_stack.enter_async_context(
            stdio_client(server_params))
        stdio, write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(
            ClientSession(stdio, write))

        await self.session.initialize()
```

然後我們再實作一個用於呼叫 MCP 伺服器的方法來處理和 DeepSeek 之間的互動。

```python
    async def process_query(self, query: str) -> str:
        # 這裡需要透過 system prompt 來約束一下大型語言模型，
        # 否則會出現不呼叫工具，自己亂回答的情況
        system_prompt = (
            "You are a helpful assistant."
            "You have the function of online search. "
            "Please MUST call web_search tool to search the Internet content before answering."
            "Please do not lose the user's question information when searching,"
            "and try to maintain the completeness of the question content as much as possible."
            "When there is a date related question in the user's question,"
            "please use the search function directly to search and PROHIBIT inserting specific time."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query}
        ]

        # 取得所有 mcp 伺服器 工具列表資訊
        response = await self.session.list_tools()
        # 產生 function call 的描述資訊
        available_tools = [{
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.inputSchema
            }
        } for tool in response.tools]

        # 請求 deepseek，function call 的描述資訊透過 tools 參數傳入
        response = self.client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL"),
            messages=messages,
            tools=available_tools
        )

        # 處理傳回的內容
        content = response.choices[0]
        if content.finish_reason == "tool_calls":
            # 如果是需要使用工具，就解析工具
            tool_call = content.message.tool_calls[0]
            tool_name = tool_call.function.name
            tool_args = json.loads(tool_call.function.arguments)

            # 執行工具
            result = await self.session.call_tool(tool_name, tool_args)
            print(f"\n\n[Calling tool {tool_name} with args {tool_args}]\n\n")

            # 將 deepseek 傳回的呼叫哪個工具資料和工具執行完成後的資料都存入 messages 中
            messages.append(content.message.model_dump())
            messages.append({
                "role": "tool",
                "content": result.content[0].text,
                "tool_call_id": tool_call.id,
            })

            # 將上面的結果再傳回給 deepseek 用於產生最終的結果
            response = self.client.chat.completions.create(
                model=os.getenv("OPENAI_MODEL"),
                messages=messages,
            )
            return response.choices[0].message.content

        return content.message.content
```

接著，我們來實作循環提問和最後退出後關閉 session 的操作。

```python
    async def chat_loop(self):
        while True:
            try:
                query = input("\nQuery: ").strip()

                if query.lower() == 'quit':
                    break

                response = await self.process_query(query)
                print("\n" + response)

            except Exception as e:
                import traceback
                traceback.print_exc()

    async def cleanup(self):
        """Clean up resources"""
        await self.exit_stack.aclose()
```

最後，我們來完成執行這個用戶端相關的程式碼

```python
async def main():
    client = MCPClient()
    try:
        await client.connect_to_server()
        await client.chat_loop()
    finally:
        await client.cleanup()


if __name__ == "__main__":
    import sys

    asyncio.run(main())

```

這是一個最精簡的程式碼，裡面沒有實作記錄上下文訊息等功能，只是為了用最簡單的程式碼來了解如何透過大型語言模型來調動 MCP 伺服器。這裡只示範了如何連線單一伺服器，如果你期望連線多個 MCP 伺服器，無非就是循環一下 `connect_to_server` 中的程式碼，可以將它們封裝成一個類別，然後將所有的 MCP 伺服器中的工具循環遍歷產生一個大的 `available_tools`，然後再透過大型語言模型的傳回結果進行呼叫即可，這裡就不再贅述了。
> 可以參考官方範例：https://github.com/modelcontextprotocol/python-sdk/blob/main/examples/clients/simple-chatbot/mcp_simple_chatbot/main.py

## Sampling 講解

MCP 還為我們提供了一個 `Sampling` 的功能，這個如果從字面上來理解會讓人摸不著頭緒，但實際上這個功能就給了我們一個在執行工具前後的介面，我們可以在工具執行前後執行一些操作。例如，當呼叫本地檔案刪除的工具時，肯定是期望我們確認後再進行刪除。那麼，此時就可以使用這個功能。

下面我們就來實作這個人工監督的小功能。

首先，我們來建立個模擬擁有刪除檔案的 MCP 伺服器：

```python
# 伺服器端
from mcp.server import FastMCP
from mcp.types import SamplingMessage, TextContent

app = FastMCP('file_server')


@app.tool()
async def delete_file(file_path: str):
    # 建立 SamplingMessage 用於觸發 sampling callback 函式
    result = await app.get_context().session.create_message(
        messages=[
            SamplingMessage(
                role='user', content=TextContent(
                    type='text', text=f'是否要刪除檔案: {file_path} (Y)')
            )
        ],
        max_tokens=100
    )

    # 取得 sampling callback 函式的傳回值，並根據傳回值進行處理
    if result.content.text == 'Y':
        return f'檔案 {file_path} 已被刪除！！'


if __name__ == '__main__':
    app.run(transport='stdio')

```

這裡最重要的就是需要透過 `create_message` 方法來建立一個 `SamplingMessage` 類型的 message，它會將這個 message 傳送給 sampling callback 對應的函式中。

接著，我們來建立用戶端的程式碼：

```python
# 用戶端
import asyncio

from mcp.client.stdio import stdio_client
from mcp import ClientSession, StdioServerParameters
from mcp.shared.context import RequestContext
from mcp.types import (
    TextContent,
    CreateMessageRequestParams,
    CreateMessageResult,
)

server_params = StdioServerParameters(
    command='uv',
    args=['run', 'file_server.py'],
)


async def sampling_callback(
        context: RequestContext[ClientSession, None],
        params: CreateMessageRequestParams,
):
    # 取得工具傳送的訊息並顯示給使用者
    input_message = input(params.messages[0].content.text)
    # 將使用者輸入傳送回工具
    return CreateMessageResult(
        role='user',
        content=TextContent(
            type='text',
            text=input_message.strip().upper() or 'Y'
        ),
        model='user-input',
        stopReason='endTurn'
    )


async def main():
    async with stdio_client(server_params) as (stdio, write):
        async with ClientSession(
                stdio, write,
                # 設定 sampling_callback 對應的方法
                sampling_callback=sampling_callback
        ) as session:
            await session.initialize()
            res = await session.call_tool(
                'delete_file',
                {'file_path': 'C:/xxx.txt'}
            )
            # 取得工具最後執行完的傳回結果
            print(res)


if __name__ == '__main__':
    asyncio.run(main())

```

特別要注意的是，目前在工具裡面列印的內容實際上使用 `stdio_client` 是無法顯示到命令列視窗的。所以，我們調試的話，可以使用 `mcp.shared.memory.create_connected_server_and_client_session`。

具體程式碼如下：

```python
# 用戶端
from mcp.shared.memory import (
    create_connected_server_and_client_session as create_session
)
# 這裡需要引入伺服器端的 app 物件
from file_server import app

async def sampling_callback(context, params):
    ...

async def main():
    async with create_session(
        app._mcp_server,
        sampling_callback=sampling_callback
    ) as client_session:
        await client_session.call_tool(
            'delete_file',
            {'file_path': 'C:/xxx.txt'}
        )

if __name__ == '__main__':
    asyncio.run(main())
```



## Claude Desktop 載入 MCP Server

因為後面的兩個功能實際上都是為了提供給 Claude 桌面端用的，所以這裡先說下如何載入我們自訂的 MCP Server 到 Claude 桌面端。

首先，我們先開啟設定。

![image-20250227221154638](.assets/image-20250227221154638.png)

我們點擊 `Developer` 選單，然後點擊 `Edit Config` 按鈕開啟 Claude 桌面端的設定檔 `claude_desktop_config.json`

![image-20250227221302174](.assets/image-20250227221302174.png)

然後開始新增我們的伺服器，伺服器需要在 `mcpServers` 層級下，參數有 `command`、`args`、`env`。實際上，參數和 `StdioServerParameters` 物件初始化時的參數是一樣的。

```json
{
  "mcpServers": {
    "web-search-server": {
      "command": "uv",
      "args": [
        "--directory",
        "D:/projects/mcp_getting_started",
        "run",
        "web_search.py"
      ]
    }
  }
}
```

最後，我們儲存檔案後重新啟動 Claude 桌面端就可以在這裡看到我們的外掛程式了。

![image-20250227221911231](.assets/image-20250227221911231.png)

![image-20250227221921036](.assets/image-20250227221921036.png)

當然，我們也可以直接在我們外掛程式的目錄下執行以下命令來直接安裝：

```shell
mcp install web_search.py
```



## 其他功能

### Prompt

MCP 還為我們提供了一個產生 Prompt 範本的功能。它使用起來也很簡單，只需要使用 `prompt` 裝飾器裝飾一下即可，程式碼如下：

```python
from mcp.server import FastMCP

app = FastMCP('prompt_and_resources')

@app.prompt('翻譯專家')
async def translate_expert(
        target_language: str = 'Chinese',
) -> str:
    return f'你是一個翻譯專家，擅長將任何語言翻譯成{target_language}。請翻譯以下內容：'


if __name__ == '__main__':
    app.run(transport='stdio')

```

然後我們用上一節講到的設定 Claude 桌面端 MCP 伺服器的方法新增下我們的新 MCP 伺服器。然後我們就可以點擊右下角的圖示開始使用啦。

它會讓我們設定一下我們傳入的參數，然後它會在我們的聊天視窗上產生一個附件。

![mcp001](.assets/mcp001-1740666812436-2.gif)



### Resource

我們還可以在 Claude 用戶端上選擇我們為使用者提供的預設資源，同時也支援自訂的協定。具體程式碼如下：

```python
from mcp.server import FastMCP

app = FastMCP('prompt_and_resources')

@app.resource('echo://static')
async def echo_resource():
    # 傳回的是，當使用者使用這個資源時，資源的內容
    return 'Echo!'

@app.resource('greeting://{name}')
async def get_greeting(name):
    return f'Hello, {name}!'


if __name__ == '__main__':
    app.run(transport='stdio')

```

然後，我們到 Claude 桌面端上看看。

![mcp002](.assets/mcp002.gif)

這裡要特別注意的是，目前 Claude 桌面端是沒法讀到資源裝飾器設定 `greeting://{name}` 這種萬用字元的路徑，未來將會被支援。但是，在我們的用戶端程式碼中是可以當作資源範本來使用的，具體程式碼如下：

```python
import asyncio
from pydantic import AnyUrl

from mcp.client.stdio import stdio_client
from mcp import ClientSession, StdioServerParameters

server_params = StdioServerParameters(
    command='uv',
    args=['run', 'prompt_and_resources.py'],
)


async def main():
    async with stdio_client(server_params) as (stdio, write):
        async with ClientSession(stdio, write) as session:
            await session.initialize()

            # 取得無萬用字元的資源列表
            res = await session.list_resources()
            print(res)

            # 取得有萬用字元的資源列表(資源範本)
            res = await session.list_resource_templates()
            print(res)

            # 讀取資源，會匹配萬用字元
            res = await session.read_resource(AnyUrl('greeting://liming'))
            print(res)

            # 取得 Prompt 範本列表
            res = await session.list_prompts()
            print(res)

            # 使用 Prompt 範本
            res = await session.get_prompt(
                '翻譯專家', arguments={'target_language': '英語'})
            print(res)


if __name__ == '__main__':
    asyncio.run(main())

```



### 生命週期

MCP 生命週期分為 3 個階段：

- 初始化
- 互動通訊中
- 服務被關閉

因此，我們可以在這三個階段的開始和結束來做一些事情，例如建立資料庫連線和關閉資料庫連線、記錄日誌、記錄工具使用資訊等。

下面我們將以網頁搜尋工具，把工具呼叫時的查詢和查詢到的結果儲存到一個全域上下文中作為快取為例，來看看生命週期如何使用。完整程式碼如下：

```python
import httpx
from dataclasses import dataclass
from contextlib import asynccontextmanager

from mcp.server import FastMCP
from mcp.server.fastmcp import Context


@dataclass
# 初始化一個生命週期上下文物件
class AppContext:
    # 裡面有一個欄位用於儲存請求歷史
    histories: dict


@asynccontextmanager
async def app_lifespan(server):
    # 在 MCP 初始化時執行
    histories = {}
    try:
        # 每次通訊會把這個上下文透過參數傳入工具
        yield AppContext(histories=histories)
    finally:
        # 當 MCP 服務關閉時執行
        print(histories)


app = FastMCP(
    'web-search',
    # 設定生命週期監聽函式
    lifespan=app_lifespan
)


@app.tool()
# 第一個參數會被傳入上下文物件
async def web_search(ctx: Context, query: str) -> str:
    """
    搜尋網際網路內容

    Args:
        query: 要搜尋的內容

    Returns:
        搜尋結果的總結
    """
    # 如果之前問過同樣的問題，就直接傳回快取
    histories = ctx.request_context.lifespan_context.histories
    if query in histories:
    	return histories[query]

    async with httpx.AsyncClient() as client:
        response = await client.post(
            'https://open.bigmodel.cn/api/paas/v4/tools',
            headers={'Authorization': 'YOUR API KEY'},
            json={
                'tool': 'web-search-pro',
                'messages': [
                    {'role': 'user', 'content': query}
                ],
                'stream': False
            }
        )

        res_data = []
        for choice in response.json()['choices']:
            for message in choice['message']['tool_calls']:
                search_results = message.get('search_result')
                if not search_results:
                    continue
                for result in search_results:
                    res_data.append(result['content'])

        return_data = '\n\n\n'.join(res_data)

        # 將查詢值和傳回值存入到 histories 中
        ctx.request_context.lifespan_context.histories[query] = return_data
        return return_data


if __name__ == "__main__":
    app.run()

```



## 在 LangChain 中使用 MCP 伺服器

最近 LangChain 發布了一個新的開源專案 `langchain-mcp-adapters`，可以很方便的將 MCP 伺服器整合到 LangChain 中。下面我們來看看如何使用它:

```python
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.prebuilt import create_react_agent

from langchain_openai import ChatOpenAI
model = ChatOpenAI(model="gpt-4o")

server_params = StdioServerParameters(
    command='uv',
    args=['run', 'web_search.py'],
)

async with stdio_client(server_params) as (read, write):
    async with ClientSession(read, write) as session:
        await session.initialize()

        # 取得工具列表
        tools = await load_mcp_tools(session)

        # 建立並使用 ReAct agent
        agent = create_react_agent(model, tools)
        agent_response = await agent.ainvoke({'messages': '杭州今天天氣怎麼樣？'})
```

更詳細的使用方法請參考：https://github.com/langchain-ai/langchain-mcp-adapters



## DeepSeek + cline + 自訂 MCP = 圖文大師

最後，我們來使用 VsCode 的 cline 外掛程式，來透過 DeepSeek 和我們自訂的一個圖片產生的 mcp 伺服器來建構一個圖文大師的應用。廢話不多說，我們直接開始。

首先先來建構我們的圖片產生的 mcp server，這裡我們直接用 huggingface 上的 `FLUX.1-schnell` 模型，地址是：https://huggingface.co/spaces/black-forest-labs/FLUX.1-schnell 。這裡我們不使用 `gradio_client` 函式庫，而是會使用 `httpx` 手搓一個，因為使用 `gradio_client` 函式庫可能會出現編碼錯誤的 bug。具體程式碼如下：

```python
# image_server.py

import json
import httpx
from mcp.server import FastMCP


app = FastMCP('image_server')


@app.tool()
async def image_generation(image_prompt: str):
    """
    產生圖片
    :param image_prompt: 圖片描述，需要是英文
    :return: 圖片儲存到的本地路徑
    """
    async with httpx.AsyncClient() as client:
        data = {'data': [image_prompt, 0, True, 512, 512, 3]}

        # 建立產生圖片任務
        response1 = await client.post(
            'https://black-forest-labs-flux-1-schnell.hf.space/call/infer',
            json=data,
            headers={"Content-Type": "application/json"}
        )

        # 解析回應取得事件 ID
        response_data = response1.json()
        event_id = response_data.get('event_id')

        if not event_id:
            return '無法取得事件 ID'

        # 透過流式的方式拿到傳回資料
        url = f'https://black-forest-labs-flux-1-schnell.hf.space/call/infer/{event_id}'
        full_response = ''
        async with client.stream('GET', url) as response2:
            async for chunk in response2.aiter_text():
                full_response += chunk

        return json.loads(full_response.split('data: ')[-1])[0]['url']

if __name__ == '__main__':
    app.run(transport='stdio')

```

然後我們可以在虛擬環境下使用下面的命令開啟 MCP Inspector 進行調試下我們的工具。

```shell
mcp dev image_server.py
```

![image-20250301231332749](.assets/image-20250301231332749.png)

接著我們在 VsCode 中安裝 cline 外掛程式，當安裝完外掛程式後，我們設定一下我們的 deepseek 的 api key。接著，我們點擊右上角的 `MCP Server` 按鈕開啟 mcp server 列表。

![image-20250301232248034](.assets/image-20250301232248034.png)

然後切換到 `Installed` Tab 點擊 `Configure MCP Servers` 按鈕來編輯自訂的 mcp 伺服器。

![image-20250301232417966](.assets/image-20250301232417966.png)

設定如下：

```json
{
  "mcpServers": {
    "image_server": {
      "command": "uv",
      "args": [
        "--directory",
        "D:/projects/mcp_getting_started",
        "run",
        "image_server.py"
      ],
      "env": {},
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

我們儲存後，這裡的這個小點是綠色的就表示我們的伺服器已連線，然後我們就可以開始使用啦。

![image-20250301232809433](.assets/image-20250301232809433.png)

然後，我們就開啟輸入框，來輸入我們的要寫的文章的內容：

![image-20250301233421292](.assets/image-20250301233421292.png)

我們可以看到，它正確的呼叫了我們的工具

![image-20250301233726301](.assets/image-20250301233726301.png)

最後，就是可以看到產生的文章啦。

![image-20250301234532249](.assets/image-20250301234532249.png)



## 借助 serverless 將 MCP 服務部署到雲端

上面我們講的都是如何使用本地的 MCP 服務，但是有時我們希望直接把 MCP 服務部署到雲端來直接呼叫，就省去了本地下載啟動的煩惱了。此時，我們就需要來使用 MCP 的 SSE 的協定來實作了。

此時，我們先來寫 SSE 協定的 MCP 服務。實作起來很簡單，只需要將我們最後的 `run` 命令中的 `transport` 參數設定為 `sse` 即可。下面還是以上面的網路搜尋為例子，來實作一下 ，具體程式碼如下：

```python
# sse_web_search.py
import httpx

from mcp.server import FastMCP


app = FastMCP('web-search', port=9000)


@app.tool()
async def web_search(query: str) -> str:
    """
    搜尋網際網路內容

    Args:
        query: 要搜尋的內容

    Returns:
        搜尋結果的總結
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            'https://open.bigmodel.cn/api/paas/v4/tools',
            headers={'Authorization': 'YOUR API KEY'},
            json={
                'tool': 'web-search-pro',
                'messages': [
                    {'role': 'user', 'content': query}
                ],
                'stream': False
            }
        )

        res_data = []
        for choice in response.json()['choices']:
            for message in choice['message']['tool_calls']:
                search_results = message.get('search_result')
                if not search_results:
                    continue
                for result in search_results:
                    res_data.append(result['content'])

        return '\n\n\n'.join(res_data)


if __name__ == "__main__":
    app.run(transport='sse')

```

在 `FastMCP` 中，有幾個可以設定 SSE 協定相關的參數：

- host: 服務地址，預設為 `0.0.0.0`
- port: 服務連接埠，預設為 8000。上述程式碼中，我設定為 `9000`
- sse_path：sse 的路由，預設為 `/sse`

此時，我們就可以直接寫一個用戶端的程式碼來進行測試了。具體程式碼如下：

```python
import asyncio
from mcp.client.sse import sse_client
from mcp import ClientSession


async def main():
    async with sse_client('http://localhost:9000/sse') as streams:
        async with ClientSession(*streams) as session:
            await session.initialize()

            res = await session.call_tool('web_search', {'query': '杭州今天天氣'})
            print(res)


if __name__ == '__main__':
    asyncio.run(main())

```

我們可以看到，它正常工作了，並搜尋到了內容：

![image-20250406152518223](.assets/image-20250406152518223.png)

當然，我們也可以使用 `mcp dev sse_web_search.py` 的方式來測試。這裡要注意的是，`Transport Type` 需要改成 `SSE`，然後下面填寫我們的本地服務地址。

![image-20250406153106098](.assets/image-20250406153106098.png)

當一切都測試沒有問題後，我們就來將它透過 severless 的方式來部署到雲端。這裡我們選擇的是阿里雲的函數計算服務。首先我們先進入到阿里雲的 `函數計算 FC 3.0` 的 `函數` 選單，並點擊 `建立函數` 來建立我們的服務。地址是：https://fcnext.console.aliyun.com/cn-hangzhou/functions

![image-20250406153655185](.assets/image-20250406153655185.png)

我們這裡選擇 `Web函數` ，執行環境我們選擇 `Python 10`。程式碼上傳方式這裡可以根據大家需求來，因為我這裡就一個 python 檔案，所以我這裡就直接選擇`使用範例程式碼`了，這樣我後面直接把我的程式碼覆蓋進去了就行了。啟動命令和監聽連接埠我這裡都保留為預設(**連接埠需要和程式碼中一致**)。

環境變數大家可以將程式碼中用到的 apikey 可以設定為一個環境變數，這裡我就不設定了。最後設定完成截圖如下：

![image-20250406154115438](.assets/image-20250406154115438.png)

在高階設定中，為了方便調試，我啟動了日誌功能。

![image-20250406154228341](.assets/image-20250406154228341.png)

設定完成後，點建立即可。它就跳轉到程式碼編輯部分，然後我們把之前的程式碼複製進去即可。

![image-20250406154441634](.assets/image-20250406154441634.png)

完成後，我們來安裝下依賴。我們點擊右上角的`編輯層`。這裡預設會有個預設的 flask 的層，因為開始的範本用的是 flask，這裡我們就不需要了。我們刪除它，再新增一個 mcp 的層。選擇`新增官方公共層`，然後搜尋 `mcp` 就能看到了一個 python 版的 MCP 層，裡面包含了 MCP 所有用到的依賴。

![image-20250406154753623](.assets/image-20250406154753623.png)

如果你還有其他第三方的，可以先搜尋下看看公共層中是否有，沒有就可以自行建構一個自訂的層。點擊這裡就可以，只需要提供一個 `requirements` 列表就可以了，這裡就不贅述了。

![image-20250406154935751](.assets/image-20250406154935751.png)

當我們都設定完成後，點擊右下角的部署即可。

然後我們又回到了我們程式碼編輯的頁面，此時，我們再點擊左上角的部署程式碼。稍等一兩秒就會提示程式碼部署成功。此時，我們的 MCP 服務就被部署到了雲端。

![image-20250406155135563](.assets/image-20250406155135563.png)



> 20250409 更新：不知道是不是官方看到了這篇文章，現在執行時可以直接選擇 `MCP 執行時` 了，就不用再在層那裡手動新增 `MCP 層` 了。
>
> ![image-20250409213302652](.assets/image-20250409213302652.png)



然後，我們切換到`設定`的`觸發器`中，就可以看到我們用來存取的 URL 地址了。當然，你也可以綁定自己的網域名稱。

![image-20250406155353662](.assets/image-20250406155353662.png)

然後，我們就可以用我們上面的用戶端程式碼進行測試了。

```python
import asyncio
from mcp.client.sse import sse_client
from mcp import ClientSession


async def main():
    async with sse_client('https://mcp-test-whhergsbso.cn-hangzhou.fcapp.run/sse') as streams:
        async with ClientSession(*streams) as session:
            await session.initialize()

            res = await session.call_tool('web_search', {'query': '杭州今天天氣'})
            print(res)


if __name__ == '__main__':
    asyncio.run(main())
```

如果我們發現在用戶端有報錯也不用慌，我們可以​​直接在日誌中找到對應出錯的請求點擊`請求日誌`查看報錯來修復。

![image-20250406155803071](.assets/image-20250406155803071.png)

到這裡，我們的 MCP 服務就被部署到了雲端，我們就可以在任何地方直接來使用它了。

例如，在 `Cherry-Studio` 中，我們可以這樣來設定：

![image-20250406160152782](.assets/image-20250406160152782.png)

在 `Cline` 中：

![image-20250406160709759](.assets/image-20250406160709759.png)

在 `Cursor` 中：

![image-20250406161055717](.assets/image-20250406161055717.png)

```json
{
  "mcpServers": {
    "web-search": {
      "url": "https://mcp-test-whhergsbso.cn-hangzhou.fcapp.run/sse"
    }
  }
}
```



至此，整個 MCP 入門教學就到這裡啦，後續有其他的再進行更新。相關程式碼會放到 github 倉庫中：https://github.com/liaokongVFX/MCP-Chinese-Getting-Started-Guide
