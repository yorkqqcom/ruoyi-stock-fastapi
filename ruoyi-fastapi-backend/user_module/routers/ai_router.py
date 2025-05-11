from dns.dnssecalgs.rsa import PublicRSASHA1
from fastapi import APIRouter, Body, HTTPException
from mcp.client.sse import sse_client
from pydantic import BaseModel
import httpx
import akshare as ak
import pandas as pd
from datetime import datetime

from user_module.services.stock_hist_service import StockHistService
from utils.response_util import ResponseUtil

import json
import os

from contextlib import AsyncExitStack
from typing import Optional

from mcp import ClientSession, StdioServerParameters, stdio_client
from openai import OpenAI, models
from dotenv import load_dotenv
load_dotenv(dotenv_path="ai.env")

class ChatResponse(BaseModel):
    response: str
    mcp_status: int = 200  # MCP协议状态码


ai_router = APIRouter(prefix="/api/ai", tags=["AI对话"])
class AIConfig:
    API_KEY = os.getenv("AI_API_KEY")
    MODEL_NAME = os.getenv("MODEL", "gpt-3.5-turbo")  # 默认值
    BASE_URL = os.getenv("BASE_URL")


# 初始化OpenAI客户端
oai_client = OpenAI(
    # base_url="http://localhost:11434/v1",  # Add /v1 to the base URL
    # api_key="ollama"  # API key can be any non-empty string if no auth is set up
    base_url=AIConfig.BASE_URL,  # Add /v1 to the base URL
    api_key=AIConfig.API_KEY,  # API key can be any non-empty string if no auth is set up
)


class HybridAgent:
    def __init__(self):
        self.mcp_servers = [
            {"name": "stock_service", "url": "http://localhost:8000/sse"},
        ]

    async def execute_query(self, question: str):
        openai_tools = []
        service_sessions = {}  # 存储各服务的会话信息

        # 1. 连接所有服务并收集工具
        for server in self.mcp_servers:
            try:
                async with sse_client(server["url"]) as (read, write):
                    async with ClientSession(read, write) as mcp_session:
                        await mcp_session.initialize()

                        # 获取工具列表
                        tools = await mcp_session.list_tools()

                        for tool in tools.tools:
                            schema = tool.inputSchema
                            if not isinstance(schema, dict):
                                continue
                            if "type" not in schema or schema.get("type") != "object":
                                continue
                            if "properties" not in schema or not isinstance(schema["properties"], dict):
                                continue

                            openai_tools.append({
                                "type": "function",
                                "function": {
                                    "name": tool.name,
                                    "description": tool.description,
                                    "parameters": schema
                                }
                            })
                            # print(openai_tools)
                        # 保存会话信息以便后续调用
                        service_sessions[server["name"]] = {
                            "url": server["url"],
                            "tools": [tool.name for tool in tools.tools]
                        }

            except Exception as e:
                print(f"连接服务 {server['name']} 失败: {str(e)}")
                continue

        if not openai_tools:
            return "没有可用的服务工具"

        # 2. 调用大模型获取工具决策
        response = oai_client.chat.completions.create(
            # model="qwen3:8b",
            model=AIConfig.MODEL_NAME,
            messages=[{"role": "user", "content": question}],
            tools = openai_tools,
            tool_choice="auto"
        )
        print('------finish_reason------',  response.choices[0])
        # 3. 处理工具调用
        if response.choices[0].message.tool_calls:
            tool_calls = response.choices[0].message.tool_calls
            tool_results = []

            # 遍历所有工具调用
            for tool_call in tool_calls:
                # 查找对应服务并执行调用
                result = await self.execute_tool_call(tool_call, service_sessions)
                tool_results.append((tool_call, result))

            # 构建最终对话上下文
            messages = self.build_messages(question, tool_calls, tool_results)

            # 生成最终响应
            final_response = oai_client.chat.completions.create(
                # model="qwen3:8b",
                model=AIConfig.MODEL_NAME,
                messages=messages
            )
            return final_response.choices[0].message.content

    async def execute_tool_call(self, tool_call, service_sessions):
        # 工具调用执行逻辑
        for server_name, info in service_sessions.items():
            if tool_call.function.name in info["tools"]:
                try:
                    # 检查是否需要股票代码转换
                    args = json.loads(tool_call.function.arguments)
                    if 'symbol' in args and not args['symbol'].isdigit():
                        # 尝试将股票名称转换为代码
                        df = await StockHistService.get_stock_list()
                        # 精确匹配
                        exact_match = df[df['name'] == args['symbol']]
                        if not exact_match.empty:
                            args['symbol'] = exact_match.iloc[0]['symbol']
                        else:
                            # 模糊匹配
                            fuzzy_match = df[df['name'].str.contains(args['symbol'], na=False)]
                            if not fuzzy_match.empty:
                                args['symbol'] = fuzzy_match.iloc[0]['symbol']
                            else:
                                return {"content": f"未找到股票名称 '{args['symbol']}' 对应的股票代码"}

                    async with sse_client(info["url"]) as (read, write):
                        async with ClientSession(read, write) as mcp_session:
                            await mcp_session.initialize()
                            result = await mcp_session.call_tool(
                                tool_call.function.name,
                                args
                            )
                            return {"content": str(result)}

                except Exception as e:
                    return {"content": f"工具执行错误: {str(e)}"}
        return {"content": "服务未找到"}

    def build_messages(self, question, tool_calls, results):
        messages = [
            {"role": "user", "content": question},
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        },
                        "type": "function"
                    } for tc in tool_calls
                ]
            }
        ]

        for (tool_call, result) in results:
            messages.append({
                "role": "tool",
                "content": result.get("content", str(result)),
                "tool_call_id": tool_call.id
            })
        print(messages)
        return messages

class ChatRequest(BaseModel):
    query: str
    model: str = "deepseek-r1"
    stream: bool = False
    temperature: float = 0.7


@ai_router.post("/chat")
async def chat(
        request: ChatRequest = Body(...)
):
    try:
        response = await call_llm(
            query=request.query,
            model=request.model,
            stream=request.stream,
            temperature=request.temperature
        )
        return ResponseUtil.success(data=ChatResponse(
            response=response,
            mcp_status=200
        ))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "response": f"处理失败: {str(e)}",
                "mcp_status": 500
            }
        )


async def call_llm(
    query: str,
    model: str = "deepseek-r1",
    stream: bool = False,
    temperature: float = 0.7
):
    try:
        print('调用Ollama大模型接口')
        agent = HybridAgent()
        result = await agent.execute_query(query)
        print('查询结果', result)
        return result
    except httpx.HTTPStatusError as http_err:
        # HTTP错误，例如：400, 404, 500等
        print(f'HTTP错误 occurred: {http_err}')  # Python 3.6
        raise HTTPException(
            status_code=http_err.response.status_code,
            detail=str(http_err)
        )
    except Exception as e:
        # 其他错误
        print(f'其他错误 occurred: {e}')  # Python 3.6
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
