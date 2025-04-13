#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
MCP客户端 - 天气查询客户端

这个脚本实现了一个简单的MCP客户端，使用JSON-RPC协议与MCP服务器通信，查询天气信息。
"""

import os
import sys
import json
import logging
import argparse
import subprocess
import time
import threading
import uuid
from typing import Dict, List, Any, Optional

logger = logging.getLogger("mcp-weather-client")

class MCPClient:
    def __init__(self, server_command: List[str], verbose: bool = False, timeout: int = 30):
        self.server_command = server_command
        self.verbose = verbose
        self.timeout = timeout
        self.process = None
        self.session_id = None
        self.stderr_thread = None
        self.stderr_output = []
        self.request_id = 0

    def _log(self, message: str, level: str = "info"):
        if self.verbose:
            getattr(logger, level)(message)

    def _read_stderr(self):
        while self.process and not self.process.poll():
            line = self.process.stderr.readline()
            if line:
                self.stderr_output.append(line.strip())
                self._log(f"伺服器錯誤輸出: {line.strip()}", "debug")

    def start_server(self):
        self._log(f"啟動MCP伺服器: {' '.join(self.server_command)}")
        try:
            self.stop_server()
            self.process = subprocess.Popen(
                self.server_command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )
            self.stderr_output = []
            self.stderr_thread = threading.Thread(target=self._read_stderr)
            self.stderr_thread.daemon = True
            self.stderr_thread.start()
            time.sleep(2)
            if self.process.poll() is not None:
                stderr = "\n".join(self.stderr_output)
                raise Exception(f"伺服器啟動失敗: {stderr}")
            self._log("伺服器啟動成功")
        except Exception as e:
            logger.error(f"啟動伺服器時出錯: {str(e)}")
            raise

    def stop_server(self):
        if self.process:
            self._log("停止MCP伺服器")
            try:
                self.process.terminate()
                time.sleep(0.5)
                if self.process.poll() is None:
                    self.process.kill()
                    time.sleep(0.5)
            except Exception as e:
                logger.error(f"停止伺服器時出錯: {str(e)}")
            finally:
                self.process = None
                self.stderr_thread = None

    def _get_next_request_id(self) -> int:
        self.request_id += 1
        return self.request_id

    def send_jsonrpc_request(self, method: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        if not self.process:
            self.start_server()
        if params is None:
            params = {}
        request_id = self._get_next_request_id()
        request = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": request_id
        }
        request_json = json.dumps(request)
        self._log(f"發送JSON-RPC請求: {request_json}")

        response = None
        timer = threading.Timer(self.timeout, lambda: self.process.kill())

        try:
            timer.start()
            self.process.stdin.write(request_json + "\n")
            self.process.stdin.flush()

            response_json = self.process.stdout.readline().strip()

            if not response_json:
                stderr = "\n".join(self.stderr_output)
                self._log("⚠️ 伺服器沒有回應任何內容", "error")
                self._log(f"🔍 伺服器 stderr: {stderr}", "debug")
                raise Exception("伺服器沒有回應，或回應為空")

            try:
                response = json.loads(response_json)
            except json.JSONDecodeError:
                self._log(f"❌ 無法解析伺服器回應：{response_json}", "error")
                raise Exception("無法解析JSON")

            if "error" in response:
                raise Exception(f"JSON-RPC錯誤: {response['error']}")

        except Exception as e:
            logger.error(f"發送JSON-RPC時錯誤: {str(e)}")
            self.stop_server()
            response = {"error": {"message": f"發送時錯誤: {str(e)}", "code": -32000}}
        finally:
            timer.cancel()

        return response

    def create_session(self) -> str:
        """
        创建MCP会话
        
        Returns:
            会话ID
        """
        self._log("创建MCP会话")
        response = self.send_jsonrpc_request("createSession")
        
        if "result" in response and "sessionId" in response["result"]:
            self.session_id = response["result"]["sessionId"]
            self._log(f"会话已创建: {self.session_id}")
            return self.session_id
        else:
            error_msg = response.get("error", {}).get("message", "未知错误")
            logger.error(f"创建会话失败: {error_msg}")
            raise Exception(f"创建会话失败: {error_msg}")
    
    def add_message(self, content: str) -> str:
        """
        向会话添加消息
        
        Args:
            content: 消息内容
        
        Returns:
            消息ID
        """
        if not self.session_id:
            self.create_session()
        
        self._log(f"添加消息: {content}")
        params = {
            "sessionId": self.session_id,
            "message": {
                "role": "user",
                "content": content,
            }
        }
        
        response = self.send_jsonrpc_request("addMessage", params)
        
        if "result" in response and "messageId" in response["result"]:
            message_id = response["result"]["messageId"]
            self._log(f"消息已添加: {message_id}")
            return message_id
        else:
            error_msg = response.get("error", {}).get("message", "未知错误")
            logger.error(f"添加消息失败: {error_msg}")
            raise Exception(f"添加消息失败: {error_msg}")
    
    def call_tool(self, tool_name: str, tool_args: Dict[str, Any]) -> Dict[str, Any]:
        """
        调用工具
        
        Args:
            tool_name: 工具名称
            tool_args: 工具参数
        
        Returns:
            工具执行结果
        """
        if not self.session_id:
            self.create_session()
        
        self._log(f"调用工具: {tool_name}, 参数: {tool_args}")
        params = {
            "sessionId": self.session_id,
            "name": tool_name,
            "arguments": tool_args
        }
        
        response = self.send_jsonrpc_request("callTool", params)
        
        if "result" in response:
            result = response["result"]
            self._log(f"工具调用结果: {result}")
            return result
        else:
            error_msg = response.get("error", {}).get("message", "未知错误")
            logger.error(f"调用工具失败: {error_msg}")
            raise Exception(f"调用工具失败: {error_msg}")
    
    def get_completion(self, message_id: str) -> str:
        """
        获取消息的完成结果
        
        Args:
            message_id: 消息ID
        
        Returns:
            完成结果
        """
        if not self.session_id:
            self.create_session()
        
        self._log(f"获取完成结果: {message_id}")
        params = {
            "sessionId": self.session_id,
            "messageId": message_id
        }
        
        response = self.send_jsonrpc_request("getCompletion", params)
        
        if "result" in response and "completion" in response["result"]:
            completion = response["result"]["completion"]
            self._log(f"完成结果: {completion}")
            
            # 检查是否有工具调用
            if "toolCall" in completion and completion["toolCall"]:
                tool_call = completion["toolCall"]
                tool_name = tool_call["name"]
                tool_args = tool_call["arguments"]
                
                self._log(f"检测到工具调用: {tool_name}")
                tool_result = self.call_tool(tool_name, tool_args)
                
                # 继续获取完成结果
                return self.get_completion(message_id)
            
            # 返回最终结果
            if "content" in completion:
                return completion["content"]
            else:
                return "无内容"
        else:
            error_msg = response.get("error", {}).get("message", "未知错误")
            logger.error(f"获取完成结果失败: {error_msg}")
            raise Exception(f"获取完成结果失败: {error_msg}")
    
    def query_weather(self, query: str) -> str:
        """
        查询天气
        
        Args:
            query: 查询内容
        
        Returns:
            查询结果
        """
        try:
            message_id = self.add_message(query)
            result = self.get_completion(message_id)
            return result
        except Exception as e:
            logger.error(f"查询天气时出错: {str(e)}")
            return f"查询天气时出错: {str(e)}"
        finally:
            self.stop_server()
    
    def direct_query_weather(self, city: str) -> str:
        """
        直接查询城市天气
        
        Args:
            city: 城市名称
        
        Returns:
            天气信息
        """
        try:
            # 创建会话
            self.create_session()
            
            # 直接调用get_weather_by_city工具
            result = self.call_tool("get_weather_by_city", {"city": city})
            return json.dumps(result, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"直接查询天气时出错: {str(e)}")
            return f"直接查询天气时出错: {str(e)}"
        finally:
            self.stop_server()

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="MCP天气查询客户端")
    parser.add_argument("--query", "-q", type=str, help="天气查询内容")
    parser.add_argument("--verbose", "-v", action="store_true", help="显示详细日志")
    parser.add_argument("--timeout", "-t", type=int, default=30, help="请求超时时间（秒）")
    parser.add_argument("--direct", "-d", action="store_true", help="直接调用工具而不是使用MCP协议")
    parser.add_argument("--city", "-c", type=str, help="直接指定城市名称")
    args = parser.parse_args()
    
    # 如果指定了城市，则使用城市作为查询内容
    if args.city:
        args.query = args.city
        args.direct = True
    
    if not args.query:
        parser.print_help()
        sys.exit(1)
    
    # MCP服务器命令
    server_command = [sys.executable, "mcp_server.py"]
    
    # 创建MCP客户端
    client = MCPClient(server_command, verbose=args.verbose, timeout=args.timeout)
    
    # 如果使用直接模式，则直接调用工具
    if args.direct:
        result = client.direct_query_weather(args.query)
        print(result)
    else:
        # 查询天气
        result = client.query_weather(args.query)
        print(result)

if __name__ == "__main__":
    main() 